"""
Live Preview window for CamDelay.
Renders side-by-side comparison of Live Physical Camera vs Delayed Virtual Camera.
Includes real-time delay slider and live FPS/latency stats.
"""

import time
import tkinter as tk
from tkinter import ttk
import cv2
from PIL import Image, ImageTk
import numpy as np

class PreviewWindow:
    def __init__(self, parent_tk, camera_worker):
        self.worker = camera_worker
        self.root = tk.Toplevel(parent_tk)
        self.root.title(f"CamDelay - Live vs Delayed Preview ({self.worker.virtual_camera_name})")
        self.root.geometry("860x540")
        self.root.minsize(700, 450)
        self.root.configure(bg="#0f172a")

        # Center on screen
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() - 860) // 2
        y = (self.root.winfo_screenheight() - 540) // 2
        self.root.geometry(f"+{x}+{y}")

        self._active = True
        self._last_live_img = None
        self._last_delayed_img = None

        self._init_ui()
        self.worker.add_preview_callback(self._on_frame)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _init_ui(self):
        # Header bar
        header = tk.Frame(self.root, bg="#1e293b", height=50)
        header.pack(fill="x")
        header.pack_propagate(False)

        lbl_title = tk.Label(
            header,
            text="Video Delay Monitor",
            font=("Segoe UI", 12, "bold"),
            fg="#f8fafc",
            bg="#1e293b"
        )
        lbl_title.pack(side="left", padx=16)

        self.stats_lbl = tk.Label(
            header,
            text="FPS: -- | Output Delay: -- ms",
            font=("Segoe UI", 9, "bold"),
            fg="#38bdf8",
            bg="#1e293b"
        )
        self.stats_lbl.pack(side="right", padx=16)

        # Video frames container (Side-by-side)
        video_container = tk.Frame(self.root, bg="#0f172a")
        video_container.pack(fill="both", expand=True, padx=14, pady=10)

        # Left: Live Physical Feed
        left_box = tk.Frame(video_container, bg="#1e293b", bd=1, relief="solid")
        left_box.pack(side="left", fill="both", expand=True, padx=(0, 6))

        lbl_live_header = tk.Label(
            left_box,
            text=f"Live Physical Camera ({self.worker.camera_name})",
            font=("Segoe UI", 9, "bold"),
            fg="#a5f3fc",
            bg="#1e293b"
        )
        lbl_live_header.pack(anchor="w", padx=10, pady=6)

        self.canvas_live = tk.Label(left_box, bg="#000000", text="Waiting for frames...", fg="#64748b")
        self.canvas_live.pack(fill="both", expand=True, padx=6, pady=(0, 6))

        # Right: Delayed Virtual Feed
        right_box = tk.Frame(video_container, bg="#1e293b", bd=1, relief="solid")
        right_box.pack(side="right", fill="both", expand=True, padx=(6, 0))

        self.lbl_delayed_header = tk.Label(
            right_box,
            text=f"Delayed Virtual Camera ({self.worker.virtual_camera_name}) - {self.worker.target_delay_ms} ms",
            font=("Segoe UI", 9, "bold"),
            fg="#fde047",
            bg="#1e293b"
        )
        self.lbl_delayed_header.pack(anchor="w", padx=10, pady=6)

        self.canvas_delayed = tk.Label(right_box, bg="#000000", text="Waiting for frames...", fg="#64748b")
        self.canvas_delayed.pack(fill="both", expand=True, padx=6, pady=(0, 6))

        # Controls bar at bottom
        controls = tk.Frame(self.root, bg="#1e293b", height=60)
        controls.pack(fill="x", side="bottom")
        controls.pack_propagate(False)

        lbl_slider = tk.Label(controls, text="Adjust Delay:", font=("Segoe UI", 9, "bold"), fg="#f8fafc", bg="#1e293b")
        lbl_slider.pack(side="left", padx=(16, 8))

        self.slider_var = tk.IntVar(value=self.worker.target_delay_ms)
        self.slider = ttk.Scale(
            controls,
            from_=0,
            to=2000,
            variable=self.slider_var,
            orient="horizontal",
            command=self._on_slider_moved
        )
        self.slider.pack(side="left", fill="x", expand=True, padx=8)

        self.lbl_val = tk.Label(
            controls,
            text=f"{self.worker.target_delay_ms} ms",
            font=("Segoe UI", 10, "bold"),
            fg="#fde047",
            bg="#1e293b",
            width=8
        )
        self.lbl_val.pack(side="left", padx=8)

        # Freeze / Resume button
        self.btn_freeze = tk.Button(
            controls,
            text="▶ Resume (Ctrl+Alt+V)" if self.worker.is_frozen else "❄ Freeze (Ctrl+Alt+C)",
            font=("Segoe UI", 8, "bold"),
            bg="#22c55e" if self.worker.is_frozen else "#0284c7",
            fg="#ffffff",
            activebackground="#0369a1",
            activeforeground="#ffffff",
            relief="flat",
            cursor="hand2",
            command=self._toggle_freeze
        )
        self.btn_freeze.pack(side="left", padx=6)

        # Quick preset buttons
        presets_frame = tk.Frame(controls, bg="#1e293b")
        presets_frame.pack(side="right", padx=16)

        for p in [0, 100, 200, 500, 1000]:
            btn = tk.Button(
                presets_frame,
                text=f"{p}ms" if p > 0 else "0ms",
                font=("Segoe UI", 8),
                bg="#334155",
                fg="#f8fafc",
                relief="flat",
                cursor="hand2",
                command=lambda val=p: self._set_delay_val(val)
            )
            btn.pack(side="left", padx=2)

    def _on_slider_moved(self, val):
        ms = int(float(val))
        self.lbl_val.config(text=f"{ms} ms")
        self.lbl_delayed_header.config(
            text=f"Delayed Virtual Camera ({self.worker.virtual_camera_name}) - {ms} ms"
        )
        self.worker.set_delay(ms)

    def _set_delay_val(self, ms: int):
        self.slider_var.set(ms)
        self.lbl_val.config(text=f"{ms} ms")
        self.lbl_delayed_header.config(
            text=f"Delayed Virtual Camera ({self.worker.virtual_camera_name}) - {ms} ms"
        )
        self.worker.set_delay(ms)

    def _toggle_freeze(self):
        self.worker.toggle_freeze()
        if self.worker.is_frozen:
            self.btn_freeze.config(text="▶ Resume (Ctrl+Alt+V)", bg="#22c55e")
            self.lbl_delayed_header.config(
                text=f"❄ FROZEN FRAME - Virtual Camera ({self.worker.virtual_camera_name})",
                fg="#38bdf8"
            )
        else:
            self.btn_freeze.config(text="❄ Freeze (Ctrl+Alt+C)", bg="#0284c7")
            self.lbl_delayed_header.config(
                text=f"Delayed Virtual Camera ({self.worker.virtual_camera_name}) - {self.worker.target_delay_ms} ms",
                fg="#fde047"
            )

    def _on_frame(self, live_bgr: np.ndarray, delayed_bgr: np.ndarray, delay_ms: float, fps: float):
        if not self._active or not self.root.winfo_exists():
            return

        try:
            # Downscale for preview display performance (e.g. max width 400px per pane)
            target_w = 380
            h, w = live_bgr.shape[:2]
            scale = target_w / max(w, 1)
            target_h = int(h * scale)

            live_small = cv2.resize(live_bgr, (target_w, target_h), interpolation=cv2.INTER_NEAREST)
            delayed_small = cv2.resize(delayed_bgr, (target_w, target_h), interpolation=cv2.INTER_NEAREST)

            live_rgb = cv2.cvtColor(live_small, cv2.COLOR_BGR2RGB)
            delayed_rgb = cv2.cvtColor(delayed_small, cv2.COLOR_BGR2RGB)

            img_live = ImageTk.PhotoImage(image=Image.fromarray(live_rgb))
            img_delayed = ImageTk.PhotoImage(image=Image.fromarray(delayed_rgb))

            def update_ui():
                if not self._active or not self.root.winfo_exists():
                    return
                self.canvas_live.configure(image=img_live, text="")
                self.canvas_live.image = img_live
                self.canvas_delayed.configure(image=img_delayed, text="")
                self.canvas_delayed.image = img_delayed
                self.stats_lbl.config(text=f"FPS: {fps:.1f} | Latency: {int(delay_ms)} ms")

            self.root.after(0, update_ui)
        except Exception:
            pass

    def _on_close(self):
        self._active = False
        self.worker.remove_preview_callback(self._on_frame)
        self.root.destroy()
