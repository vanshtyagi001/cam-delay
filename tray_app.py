"""
System Tray Application for CamDelay.
Manages the Windows notification area tray icon, context menus,
quick delay switching, camera selection, and opens settings/preview windows.
"""

import sys
import tkinter as tk
from tkinter import messagebox
from typing import Optional
import pystray
from PIL import Image, ImageDraw
from config import Config
from camera_worker import CameraWorker, CameraState
from camera_enumerator import get_physical_cameras
from ui_settings import SettingsWindow
from ui_preview import PreviewWindow
from ui_custom_delay import show_custom_delay_dialog
from hotkey_manager import HotkeyManager

class TrayApp:
    def __init__(self, tk_root: tk.Tk, worker: CameraWorker, config: Config):
        self.root = tk_root
        self.worker = worker
        self.config = config

        self.current_state = CameraState.STOPPED
        self.status_text = "Initializing..."

        # UI Window singletons
        self._settings_window: Optional[SettingsWindow] = None
        self._preview_window: Optional[PreviewWindow] = None

        # Hotkey Manager
        self.hotkey_mgr = HotkeyManager()
        self.hotkey_mgr.on_freeze = self._on_hotkey_freeze
        self.hotkey_mgr.on_resume = self._on_hotkey_resume
        self.hotkey_mgr.on_resume_live = self._on_hotkey_resume_live
        self.hotkey_mgr.on_toggle_delay = self._on_hotkey_toggle_delay
        self.hotkey_mgr.on_delay_increase = self._on_hotkey_delay_inc
        self.hotkey_mgr.on_delay_decrease = self._on_hotkey_delay_dec

        # Build icon and pystray instance
        self.icon = pystray.Icon(
            "CamDelay",
            icon=self._create_icon_image(self.current_state),
            title=f"CamDelay - {self.worker.virtual_camera_name}",
            menu=self._build_menu()
        )

        # Register state listener from worker
        self.worker.add_state_callback(self._on_worker_state_change)

    def _create_icon_image(self, state: CameraState) -> Image.Image:
        """Generates a crisp 64x64 RGBA icon reflecting current camera status."""
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Base camera body (Dark slate rounded rectangle)
        draw.rounded_rectangle([(8, 16), (56, 48)], radius=8, fill=(30, 41, 59), outline=(148, 163, 184), width=2)
        # Top viewfinder / flash bump
        draw.rectangle([(24, 11), (40, 16)], fill=(51, 65, 85))
        # Camera lens outer ring
        draw.ellipse([(22, 22), (42, 42)], fill=(15, 23, 42), outline=(203, 213, 225), width=2)
        # Inner lens aperture
        draw.ellipse([(27, 27), (37, 37)], fill=(56, 189, 248))

        # Status badge indicator on bottom right
        if state == CameraState.ACTIVE:
            # Glowing green circle
            draw.ellipse([(44, 40), (58, 54)], fill=(34, 197, 94), outline=(255, 255, 255), width=2)
        elif state == CameraState.FROZEN:
            # Ice blue badge with snowflake indicator
            draw.ellipse([(44, 40), (58, 54)], fill=(56, 189, 248), outline=(255, 255, 255), width=2)
            draw.line([(51, 43), (51, 51)], fill=(255, 255, 255), width=2)
            draw.line([(47, 47), (55, 47)], fill=(255, 255, 255), width=2)
        elif state in [CameraState.DISCONNECTED, CameraState.ERROR]:
            # Amber / red warning badge
            draw.ellipse([(44, 40), (58, 54)], fill=(239, 68, 68), outline=(255, 255, 255), width=2)
            draw.line([(51, 44), (51, 48)], fill=(255, 255, 255), width=2)
            draw.point([(51, 51)], fill=(255, 255, 255))
        else:
            # Disabled / Paused: muted gray
            draw.ellipse([(44, 40), (58, 54)], fill=(148, 163, 184), outline=(255, 255, 255), width=2)

        return img

    def _on_worker_state_change(self, state: CameraState, message: str):
        self.current_state = state
        self.status_text = message
        # Update icon appearance
        self.icon.icon = self._create_icon_image(state)
        self.icon.title = f"CamDelay: {self.worker.virtual_camera_name} - {message}"
        self.icon.menu = self._build_menu()

    def _build_menu(self) -> pystray.Menu:
        """Constructs the dynamic system tray context menu."""
        items = []

        # 1. Header (Title and Status)
        vname = self.worker.virtual_camera_name
        status_disp = f"Status: {self.status_text}"
        items.append(pystray.MenuItem(f"{vname}", lambda: None, enabled=False))
        items.append(pystray.MenuItem(status_disp, lambda: None, enabled=False))
        items.append(pystray.Menu.SEPARATOR)

        # 2. Input Camera Submenu
        cam_subitems = []
        cams = get_physical_cameras(self.worker.virtual_camera_name)
        if cams:
            for c in cams:
                idx = c["index"]
                name = c["name"]
                is_selected = (name == self.worker.camera_name or (idx == self.worker.camera_index and not any(x["name"] == self.worker.camera_name for x in cams)))
                cam_subitems.append(pystray.MenuItem(
                    f"{name}",
                    self._create_camera_selector(idx, name),
                    checked=lambda item, sel=is_selected: sel
                ))
        else:
            cam_subitems.append(pystray.MenuItem("No cameras detected", lambda: None, enabled=False))

        cam_subitems.append(pystray.Menu.SEPARATOR)
        cam_subitems.append(pystray.MenuItem("🔄 Refresh Cameras", self._on_refresh_cameras))
        items.append(pystray.MenuItem("Input Camera", pystray.Menu(*cam_subitems)))

        # 3. Delay Submenu
        delay_subitems = []
        presets = [0, 50, 100, 200, 300, 500, 1000]
        cur_delay = self.worker.target_delay_ms

        for p in presets:
            lbl = f"{p} ms" if p > 0 else "0 ms (Passthrough / Low Latency)"
            is_checked = (cur_delay == p)
            delay_subitems.append(pystray.MenuItem(
                lbl,
                self._create_delay_setter(p),
                checked=lambda item, sel=is_checked: sel
            ))

        delay_subitems.append(pystray.Menu.SEPARATOR)
        delay_subitems.append(pystray.MenuItem("Custom Delay...", self._open_custom_delay))
        items.append(pystray.MenuItem("Delay", pystray.Menu(*delay_subitems)))
        items.append(pystray.MenuItem("Custom Delay...", self._open_custom_delay))

        # Start / Stop Delay Toggle
        if self.worker.target_delay_ms > 0:
            items.append(pystray.MenuItem(f"⏹ Stop Delay (0 ms Live) [Ctrl+Alt+D]", self._on_hotkey_toggle_delay))
        else:
            stored = self.worker._stored_delay_ms if self.worker._stored_delay_ms > 0 else 200
            items.append(pystray.MenuItem(f"▶ Start Delay ({stored} ms) [Ctrl+Alt+D]", self._on_hotkey_toggle_delay))

        items.append(pystray.Menu.SEPARATOR)

        # 4. Freeze / Resume Controls
        if self.worker.is_frozen:
            items.append(pystray.MenuItem(f"▶ Resume Video ({self.worker.target_delay_ms} ms delay) [Ctrl+Alt+V]", self._on_hotkey_resume))
            items.append(pystray.MenuItem("⚡ Resume Live (0 ms) [Ctrl+Alt+0]", self._on_hotkey_resume_live))
        else:
            items.append(pystray.MenuItem("❄ Freeze Frame [Ctrl+Alt+C]", self._on_hotkey_freeze))

        items.append(pystray.Menu.SEPARATOR)

        # 5. Enable / Disable Toggle
        if self.worker.is_enabled:
            items.append(pystray.MenuItem("Disable Camera", self._on_toggle_enable))
        else:
            items.append(pystray.MenuItem("Enable Camera", self._on_toggle_enable))

        # 6. Live Preview
        items.append(pystray.MenuItem("Live vs Delayed Preview...", self._open_preview))

        # 7. Settings
        items.append(pystray.MenuItem("Settings...", self._open_settings))

        items.append(pystray.Menu.SEPARATOR)

        # 8. Exit
        items.append(pystray.MenuItem("Exit", self._on_exit))

        return pystray.Menu(*items)

    def _on_hotkey_freeze(self):
        """Triggered via Ctrl+Alt+C or menu to freeze frame."""
        print("[TrayApp] Freeze toggled (Ctrl+Alt+C).")
        self.worker.toggle_freeze()
        self.icon.menu = self._build_menu()

    def _on_hotkey_resume(self):
        """Triggered via Ctrl+Alt+V or menu to resume with set delay from current video."""
        print(f"[TrayApp] Resuming live feed with {self.worker.target_delay_ms} ms delay (Ctrl+Alt+V).")
        self.worker.unfreeze()
        self.icon.menu = self._build_menu()

    def _on_hotkey_resume_live(self):
        """Triggered via Ctrl+Alt+0 to unfreeze and switch to immediate 0ms live feed."""
        print("[TrayApp] Resuming live feed with 0 ms passthrough.")
        self.worker.unfreeze(delay_ms=0)
        self.icon.menu = self._build_menu()

    def _on_hotkey_toggle_delay(self):
        """Triggered via Ctrl+Alt+D to toggle starting/stopping delay."""
        is_delayed = self.worker.toggle_delay()
        if is_delayed:
            print(f"[TrayApp] Delay started: {self.worker.target_delay_ms} ms (Ctrl+Alt+D).")
        else:
            print("[TrayApp] Delay stopped: 0 ms live passthrough (Ctrl+Alt+D).")
        self.icon.menu = self._build_menu()

    def _on_hotkey_delay_inc(self):
        new_d = self.worker.target_delay_ms + 50
        print(f"[TrayApp] Delay increased to {new_d} ms.")
        self.worker.set_delay(new_d)
        self.icon.menu = self._build_menu()

    def _on_hotkey_delay_dec(self):
        new_d = max(0, self.worker.target_delay_ms - 50)
        print(f"[TrayApp] Delay decreased to {new_d} ms.")
        self.worker.set_delay(new_d)
        self.icon.menu = self._build_menu()

    def _create_camera_selector(self, index: int, name: str):
        def _select():
            self.worker.set_input_camera(index, name)
            self.icon.menu = self._build_menu()
        return _select

    def _create_delay_setter(self, delay_ms: int):
        def _set():
            self.worker.set_delay(delay_ms)
            self.icon.menu = self._build_menu()
        return _set

    def _on_refresh_cameras(self):
        self.icon.menu = self._build_menu()

    def _on_toggle_enable(self):
        new_state = not self.worker.is_enabled
        self.worker.set_enabled(new_state)
        self.icon.menu = self._build_menu()

    def _open_custom_delay(self):
        def _ui():
            show_custom_delay_dialog(
                self.worker.target_delay_ms,
                on_save_callback=lambda val: (self.worker.set_delay(val), setattr(self.icon, 'menu', self._build_menu()))
            )
        self.root.after(0, _ui)

    def _open_preview(self):
        def _ui():
            if self._preview_window and self._preview_window.root.winfo_exists():
                self._preview_window.root.lift()
            else:
                self._preview_window = PreviewWindow(self.root, self.worker)
        self.root.after(0, _ui)

    def _open_settings(self):
        def _ui():
            if self._settings_window and self._settings_window.root.winfo_exists():
                self._settings_window.root.lift()
            else:
                def _on_settings_applied():
                    # Apply any updated parameters to worker
                    if self.config.virtual_camera_name != self.worker.virtual_camera_name:
                        self.worker.update_virtual_camera_name(self.config.virtual_camera_name)
                    if self.config.delay_ms != self.worker.target_delay_ms:
                        self.worker.set_delay(self.config.delay_ms)
                    if self.config.input_camera != self.worker.camera_name:
                        self.worker.set_input_camera(self.config.input_camera_index, self.config.input_camera)
                    self.icon.menu = self._build_menu()
                self._settings_window = SettingsWindow(self.root, self.config, on_apply_callback=_on_settings_applied)
        self.root.after(0, _ui)

    def _on_exit(self):
        print("[TrayApp] Exiting application...")
        self.hotkey_mgr.stop()
        self.worker.stop()
        self.icon.stop()
        self.root.after(0, self.root.quit)

    def run(self):
        """Runs the tray icon in detached mode and starts the Tk event loop."""
        self.hotkey_mgr.start()
        self.icon.run_detached()
        if self.worker.is_enabled:
            self.worker.start()
        self.root.mainloop()
