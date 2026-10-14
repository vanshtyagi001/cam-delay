"""
CameraWorker engine for CamDelay.
Handles capturing from physical camera, timestamp-based delay buffering,
and outputting delayed frames to the virtual camera device.
Supports dynamic delay adjustment and input camera switching while running.
"""

import time
import threading
from collections import deque
from enum import Enum
from typing import Optional, Callable, Tuple
import cv2
import numpy as np
import pyvirtualcam
from config import Config
from camera_enumerator import get_physical_cameras
from vcam_manager import ensure_virtual_camera

class CameraState(Enum):
    STOPPED = "Camera Stopped"
    STARTING = "Starting Camera..."
    ACTIVE = "Camera Active"
    FROZEN = "Frame Frozen"
    DISABLED = "Camera Disabled"
    DISCONNECTED = "Input Camera Disconnected"
    ERROR = "Camera Error"

class CameraWorker:
    def __init__(self, config: Config):
        self.config = config
        self.state = CameraState.STOPPED
        self.status_message = "Ready"

        # Parameters
        self.target_delay_ms = self.config.delay_ms
        self._stored_delay_ms = self.target_delay_ms if self.target_delay_ms > 0 else 200
        self.camera_index = self.config.input_camera_index
        self.camera_name = self.config.input_camera
        self.virtual_camera_name = self.config.virtual_camera_name
        self.is_enabled = self.config.auto_start_camera

        # Freeze control
        self.is_frozen = False
        self.frozen_frame: Optional[np.ndarray] = None
        self._last_sent_frame: Optional[np.ndarray] = None
        self._last_live_frame: Optional[np.ndarray] = None

        # Worker control
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        
        # State listeners
        self._state_callbacks = []
        self._preview_callbacks = []

        # Metrics
        self.measured_fps = 0.0
        self.frames_sent = 0
        self.current_width = 0
        self.current_height = 0

    def freeze(self):
        """Freezes the virtual camera output on the current frame."""
        with self._lock:
            self.is_frozen = True
            if self._last_sent_frame is not None:
                self.frozen_frame = self._last_sent_frame.copy()
            elif self._last_live_frame is not None:
                self.frozen_frame = self._last_live_frame.copy()
        print("[CameraWorker] Freeze activated.")
        self._set_state(CameraState.FROZEN, "❄ Frozen on Frame")

    def unfreeze(self, delay_ms: Optional[int] = None):
        """Resumes live stream from current physical video, applying target delay."""
        with self._lock:
            if delay_ms is not None:
                self.target_delay_ms = max(0, int(delay_ms))
                self.config.delay_ms = self.target_delay_ms
                if self.target_delay_ms > 0:
                    self._stored_delay_ms = self.target_delay_ms
            self.is_frozen = False
            self.frozen_frame = None
        print(f"[CameraWorker] Resumed live stream with delay {self.target_delay_ms} ms.")
        self._set_state(CameraState.ACTIVE, f"Active ({self.target_delay_ms} ms)")

    def toggle_freeze(self):
        """Toggles between frozen frame and active delayed streaming."""
        if self.is_frozen:
            self.unfreeze()
        else:
            self.freeze()

    def start_delay(self) -> int:
        """Starts/restores the configured video delay (if at 0 ms)."""
        target = self._stored_delay_ms if self._stored_delay_ms > 0 else 200
        if self.is_frozen:
            self.unfreeze(delay_ms=target)
        else:
            self.set_delay(target)
        print(f"[CameraWorker] Delay started: {target} ms")
        return target

    def stop_delay(self) -> int:
        """Stops the video delay and switches to 0 ms live passthrough."""
        if self.target_delay_ms > 0:
            self._stored_delay_ms = self.target_delay_ms
        if self.is_frozen:
            self.unfreeze(delay_ms=0)
        else:
            self.set_delay(0)
        print("[CameraWorker] Delay stopped: 0 ms passthrough")
        return 0

    def toggle_delay(self) -> bool:
        """Toggles between delayed video and 0 ms live passthrough."""
        if self.target_delay_ms > 0:
            self.stop_delay()
            return False
        else:
            self.start_delay()
            return True

    def add_state_callback(self, cb: Callable[[CameraState, str], None]):
        with self._lock:
            self._state_callbacks.append(cb)

    def add_preview_callback(self, cb: Callable[[np.ndarray, np.ndarray, float, float], None]):
        with self._lock:
            self._preview_callbacks.append(cb)

    def remove_preview_callback(self, cb: Callable):
        with self._lock:
            if cb in self._preview_callbacks:
                self._preview_callbacks.remove(cb)

    def _set_state(self, state: CameraState, message: str = ""):
        self.state = state
        self.status_message = message or state.value
        for cb in list(self._state_callbacks):
            try:
                cb(state, self.status_message)
            except Exception as e:
                print(f"[CameraWorker] State callback error: {e}")

    def set_delay(self, delay_ms: int):
        """Dynamically updates delay in milliseconds without restarting stream."""
        delay_ms = max(0, int(delay_ms))
        with self._lock:
            self.target_delay_ms = delay_ms
            self.config.delay_ms = delay_ms
            if delay_ms > 0:
                self._stored_delay_ms = delay_ms
        print(f"[CameraWorker] Target delay updated to {delay_ms} ms")
        if not self.is_frozen:
            self._set_state(self.state, f"Active ({delay_ms} ms)" if self.state == CameraState.ACTIVE else "")

    def set_input_camera(self, index: int, name: str):
        """Switches physical camera device dynamically."""
        with self._lock:
            self.camera_index = index
            self.camera_name = name
            self.config.input_camera_index = index
            self.config.input_camera = name
        print(f"[CameraWorker] Switched input camera to [{index}] {name}")
        # Signal restart of capture thread if active
        if self._thread and self._thread.is_alive():
            self.restart()

    def set_enabled(self, enabled: bool):
        self.is_enabled = enabled
        if enabled:
            if self.state in [CameraState.STOPPED, CameraState.DISABLED]:
                self.start()
        else:
            self._set_state(CameraState.DISABLED, "Camera Disabled")

    def update_virtual_camera_name(self, new_name: str):
        with self._lock:
            self.virtual_camera_name = new_name
            self.config.virtual_camera_name = new_name
            ensure_virtual_camera(new_name)
        if self._thread and self._thread.is_alive():
            self.restart()

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="CameraWorkerThread")
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self._set_state(CameraState.STOPPED, "Stopped")

    def restart(self):
        self.stop()
        self.start()

    def _open_physical_camera(self) -> Optional[cv2.VideoCapture]:
        """Attempts to open physical camera via DirectShow, then Media Foundation."""
        # Check available physical cameras to find index for configured camera name
        cams = get_physical_cameras(self.virtual_camera_name)
        chosen_idx = self.camera_index
        for c in cams:
            if c["name"] == self.camera_name:
                chosen_idx = c["index"]
                break

        print(f"[CameraWorker] Opening physical camera index {chosen_idx} ('{self.camera_name}')...")
        cap = cv2.VideoCapture(chosen_idx, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap = cv2.VideoCapture(chosen_idx, cv2.CAP_MSMF)
        if not cap.isOpened():
            return None

        # Request user resolution preference if available (e.g. 1280x720)
        req_w = self.config.resolution_width
        req_h = self.config.resolution_height
        if req_w and req_h:
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, req_w)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, req_h)

        return cap

    def _run_loop(self):
        """Main worker streaming loop."""
        need_com_uninit = False
        try:
            import comtypes
            comtypes.CoInitialize()
            need_com_uninit = True
        except Exception:
            pass

        ensure_virtual_camera(self.virtual_camera_name)
        self._set_state(CameraState.STARTING, "Starting Camera...")

        cap = None
        vcam = None
        buffer = deque()

        fps_timer = time.perf_counter()
        fps_frame_count = 0
        fps_val = 30.0

        try:
            while not self._stop_event.is_set():
                if not self.is_enabled:
                    self._set_state(CameraState.DISABLED, "Camera Disabled")
                    time.sleep(0.2)
                    continue

                # 1. Connect physical camera
                if cap is None or not cap.isOpened():
                    self._set_state(CameraState.DISCONNECTED, f"Waiting for {self.camera_name}...")
                    cap = self._open_physical_camera()
                    if cap is None or not cap.isOpened():
                        # Retry after 1.5 seconds
                        time.sleep(1.5)
                        continue

                    # Read test frame to ascertain dimensions
                    ret, test_frame = cap.read()
                    if not ret or test_frame is None:
                        cap.release()
                        cap = None
                        time.sleep(1.5)
                        continue

                    h, w, _ = test_frame.shape
                    self.current_width = w
                    self.current_height = h
                    cam_fps = cap.get(cv2.CAP_PROP_FPS)
                    fps_val = cam_fps if (cam_fps and 10 <= cam_fps <= 120) else 30.0
                    print(f"[CameraWorker] Input camera ready: {w}x{h} @ {fps_val:.1f} FPS")

                # 2. Ensure virtual camera initialized matching dimensions
                if vcam is None or vcam.width != self.current_width or vcam.height != self.current_height:
                    if vcam is not None:
                        vcam.close()
                    try:
                        vcam = pyvirtualcam.Camera(
                            width=self.current_width,
                            height=self.current_height,
                            fps=fps_val,
                            fmt=pyvirtualcam.PixelFormat.BGR,
                            device=self.virtual_camera_name
                        )
                        print(f"[CameraWorker] Virtual camera initialized: {vcam.device} ({self.current_width}x{self.current_height})")
                    except Exception as e:
                        print(f"[CameraWorker] Virtual camera creation failed: {e}")
                        self._set_state(CameraState.ERROR, f"Virtual camera error: {e}")
                        time.sleep(2.0)
                        continue

                if self.is_frozen:
                    self._set_state(CameraState.FROZEN, "❄ Frozen on Frame")
                else:
                    self._set_state(CameraState.ACTIVE, f"Active ({self.target_delay_ms} ms)")

                # 3. Capture physical frame
                ret, live_frame = cap.read()
                if not ret or live_frame is None:
                    print("[CameraWorker] Failed to read frame from physical camera. Disconnected.")
                    self._set_state(CameraState.DISCONNECTED, f"Waiting for {self.camera_name}...")
                    cap.release()
                    cap = None
                    buffer.clear()
                    time.sleep(1.0)
                    continue

                now = time.perf_counter()
                delay_sec = self.target_delay_ms / 1000.0
                self._last_live_frame = live_frame

                # 4. Handle Freeze or Delay Buffering
                if self.is_frozen:
                    # In frozen state: continuously stream static frozen frame at normal framerate
                    if self.frozen_frame is None:
                        self.frozen_frame = live_frame.copy()
                    frame_to_send = self.frozen_frame
                    buffer.clear()
                else:
                    if delay_sec <= 0.001:
                        # Low-latency passthrough mode (0 ms)
                        buffer.clear()
                        frame_to_send = live_frame
                    else:
                        buffer.append((now, live_frame))

                        # Drop obsolete frames if buffer exceeds target delay + 200ms
                        max_allowed_age = delay_sec + 0.200
                        while buffer and (now - buffer[0][0]) > max_allowed_age:
                            buffer.popleft()

                        # Find candidate frame that is >= delay_sec old
                        frame_to_send = None
                        while buffer and (now - buffer[0][0]) >= delay_sec:
                            t_cap, frame_to_send = buffer.popleft()

                # 5. Output to Virtual Camera
                if frame_to_send is not None:
                    try:
                        vcam.send(frame_to_send)
                        self.frames_sent += 1
                        if not self.is_frozen:
                            self._last_sent_frame = frame_to_send
                    except Exception as e:
                        print(f"[CameraWorker] Error sending frame to vcam: {e}")

                # 6. FPS Calculation
                fps_frame_count += 1
                if now - fps_timer >= 1.0:
                    self.measured_fps = fps_frame_count / (now - fps_timer)
                    fps_frame_count = 0
                    fps_timer = now

                # 7. Notify Preview listeners (if any)
                if self._preview_callbacks and frame_to_send is not None:
                    for cb in list(self._preview_callbacks):
                        try:
                            cb(live_frame, frame_to_send, self.target_delay_ms, self.measured_fps)
                        except Exception:
                            pass

        except Exception as e:
            print(f"[CameraWorker] Unexpected error in worker loop: {e}")
            self._set_state(CameraState.ERROR, f"Worker error: {e}")
        finally:
            if vcam:
                try:
                    vcam.close()
                except Exception:
                    pass
            if cap:
                try:
                    cap.release()
                except Exception:
                    pass
            buffer.clear()
            if need_com_uninit:
                try:
                    import comtypes
                    comtypes.CoUninitialize()
                except Exception:
                    pass
            print("[CameraWorker] Worker loop stopped.")

