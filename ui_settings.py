"""
Settings Dialog for CamDelay.
Provides a modern interface for configuring input camera, virtual camera name,
startup behavior, default delay, and video preferences.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from config import Config
from camera_enumerator import get_physical_cameras
from autostart import set_autostart, is_autostart_enabled

class SettingsWindow:
    def __init__(self, parent_tk, config: Config, on_apply_callback=None):
        self.config = config
        self.on_apply = on_apply_callback

        self.root = tk.Toplevel(parent_tk)
        self.root.title("CamDelay - Settings")
        self.root.geometry("490x690")
        self.root.resizable(False, False)
        self.root.attributes("-topmost", True)
        self.root.configure(bg="#18181b")

        # Center on screen
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() - 490) // 2
        y = (self.root.winfo_screenheight() - 690) // 2
        self.root.geometry(f"+{x}+{y}")

        self._init_ui()

    def _init_ui(self):
        # Header banner
        header = tk.Frame(self.root, bg="#27272a", height=65)
        header.pack(fill="x")
        header.pack_propagate(False)

        title_lbl = tk.Label(
            header,
            text="CamDelay Settings",
            font=("Segoe UI", 13, "bold"),
            fg="#f4f4f5",
            bg="#27272a"
        )
        title_lbl.pack(anchor="w", padx=20, pady=(12, 2))

        sub_lbl = tk.Label(
            header,
            text="Configure physical camera input, virtual device name, and stream delay",
            font=("Segoe UI", 8),
            fg="#a1a1aa",
            bg="#27272a"
        )
        sub_lbl.pack(anchor="w", padx=20)

        # Content container
        container = tk.Frame(self.root, bg="#18181b")
        container.pack(fill="both", expand=True, padx=24, pady=16)

        # 1. Input Camera Section
        lbl_cam = tk.Label(container, text="INPUT PHYSICAL CAMERA", font=("Segoe UI", 8, "bold"), fg="#38bdf8", bg="#18181b")
        lbl_cam.pack(anchor="w", pady=(0, 4))

        cam_frame = tk.Frame(container, bg="#18181b")
        cam_frame.pack(fill="x", pady=(0, 14))

        self.cam_var = tk.StringVar()
        self.cam_combo = ttk.Combobox(cam_frame, textvariable=self.cam_var, state="readonly", font=("Segoe UI", 9))
        self.cam_combo.pack(side="left", fill="x", expand=True, ipady=3)

        btn_refresh = tk.Button(
            cam_frame,
            text="🔄 Refresh",
            font=("Segoe UI", 8),
            bg="#27272a",
            fg="#f4f4f5",
            relief="flat",
            cursor="hand2",
            command=self._refresh_cameras
        )
        btn_refresh.pack(side="left", padx=(8, 0), ipady=2)

        self._refresh_cameras()

        # 2. Virtual Camera Name Section
        lbl_vname = tk.Label(container, text="VIRTUAL CAMERA NAME", font=("Segoe UI", 8, "bold"), fg="#38bdf8", bg="#18181b")
        lbl_vname.pack(anchor="w", pady=(0, 4))

        lbl_vname_desc = tk.Label(container, text="The name exposed to Zoom, Discord, browsers, and Windows applications:", font=("Segoe UI", 8), fg="#71717a", bg="#18181b")
        lbl_vname_desc.pack(anchor="w", pady=(0, 4))

        self.vname_var = tk.StringVar(value=self.config.virtual_camera_name)
        vname_entry = tk.Entry(
            container,
            textvariable=self.vname_var,
            font=("Segoe UI", 10),
            bg="#27272a",
            fg="#f4f4f5",
            insertbackground="#f4f4f5",
            relief="flat"
        )
        vname_entry.pack(fill="x", ipady=4, pady=(0, 14))

        # 3. Default Delay Section
        lbl_delay = tk.Label(container, text="DEFAULT DELAY (MILLISECONDS)", font=("Segoe UI", 8, "bold"), fg="#38bdf8", bg="#18181b")
        lbl_delay.pack(anchor="w", pady=(0, 4))

        delay_frame = tk.Frame(container, bg="#18181b")
        delay_frame.pack(fill="x", pady=(0, 14))

        self.delay_var = tk.IntVar(value=self.config.delay_ms)
        self.delay_slider = ttk.Scale(
            delay_frame,
            from_=0,
            to=2000,
            variable=self.delay_var,
            orient="horizontal",
            command=lambda v: self.delay_spin.delete(0, tk.END) or self.delay_spin.insert(0, str(int(float(v))))
        )
        self.delay_slider.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.delay_spin = tk.Spinbox(
            delay_frame,
            from_=0,
            to=10000,
            textvariable=self.delay_var,
            width=6,
            font=("Segoe UI", 10),
            bg="#27272a",
            fg="#f4f4f5",
            insertbackground="#f4f4f5",
            relief="flat",
            justify="center"
        )
        self.delay_spin.pack(side="left", ipady=2)

        lbl_ms_suffix = tk.Label(delay_frame, text="ms", font=("Segoe UI", 9, "bold"), fg="#71717a", bg="#18181b")
        lbl_ms_suffix.pack(side="left", padx=(4, 0))

        # 4. Resolution Preference Section
        lbl_res = tk.Label(container, text="MAXIMUM RESOLUTION", font=("Segoe UI", 8, "bold"), fg="#38bdf8", bg="#18181b")
        lbl_res.pack(anchor="w", pady=(0, 4))

        self.res_var = tk.StringVar()
        cur_w = self.config.resolution_width
        cur_h = self.config.resolution_height
        if cur_w == 1920:
            self.res_var.set("1920x1080 (1080p FHD)")
        elif cur_w == 1280:
            self.res_var.set("1280x720 (720p HD)")
        else:
            self.res_var.set("640x480 (480p SD)")

        res_combo = ttk.Combobox(
            container,
            textvariable=self.res_var,
            values=["1920x1080 (1080p FHD)", "1280x720 (720p HD)", "640x480 (480p SD)"],
            state="readonly",
            font=("Segoe UI", 9)
        )
        res_combo.pack(fill="x", ipady=3, pady=(0, 14))

        # 5. Startup & Behavior Checkboxes
        lbl_opts = tk.Label(container, text="STARTUP BEHAVIOR & DRIVER", font=("Segoe UI", 8, "bold"), fg="#38bdf8", bg="#18181b")
        lbl_opts.pack(anchor="w", pady=(0, 6))

        self.autostart_var = tk.BooleanVar(value=is_autostart_enabled())
        chk_autostart = tk.Checkbutton(
            container,
            text="Start with Windows (silently minimizes to system tray)",
            variable=self.autostart_var,
            font=("Segoe UI", 9),
            fg="#f4f4f5",
            bg="#18181b",
            selectcolor="#27272a",
            activebackground="#18181b",
            activeforeground="#f4f4f5"
        )
        chk_autostart.pack(anchor="w", pady=2)

        self.autocamera_var = tk.BooleanVar(value=self.config.auto_start_camera)
        chk_autocamera = tk.Checkbutton(
            container,
            text="Start camera automatically when application starts",
            variable=self.autocamera_var,
            font=("Segoe UI", 9),
            fg="#f4f4f5",
            bg="#18181b",
            selectcolor="#27272a",
            activebackground="#18181b",
            activeforeground="#f4f4f5"
        )
        chk_autocamera.pack(anchor="w", pady=2)

        btn_elevated = tk.Button(
            container,
            text="🛡 Register Driver System-wide (Admin UAC)",
            font=("Segoe UI", 8),
            bg="#27272a",
            fg="#93c5fd",
            activebackground="#3f3f46",
            activeforeground="#ffffff",
            relief="flat",
            cursor="hand2",
            command=self._on_register_driver_elevated
        )
        btn_elevated.pack(anchor="w", pady=(6, 0))

        # 6. Global Shortcuts Reference Section
        lbl_hk = tk.Label(container, text="GLOBAL KEYBOARD SHORTCUTS", font=("Segoe UI", 8, "bold"), fg="#38bdf8", bg="#18181b")
        lbl_hk.pack(anchor="w", pady=(14, 4))

        hk_card = tk.Frame(container, bg="#27272a", bd=1, relief="solid")
        hk_card.pack(fill="x", pady=(0, 4))

        shortcuts = [
            ("Ctrl + Alt + C", "Freeze / Toggle Current Frame"),
            ("Ctrl + Alt + V", "Resume from Live Video (with set delay)"),
            ("Ctrl + Alt + D", "Start / Stop Delay (Toggle set delay / 0 ms)"),
            ("Ctrl + Alt + 0", "Resume Live Immediately (0 ms passthrough)"),
            ("Ctrl + Alt + ↑ / ↓", "Increase / Decrease Delay (+/- 50 ms)")
        ]

        for key, desc in shortcuts:
            row = tk.Frame(hk_card, bg="#27272a")
            row.pack(fill="x", padx=10, pady=3)
            lbl_k = tk.Label(row, text=key, font=("Consolas", 8, "bold"), fg="#38bdf8", bg="#18181b", padx=6, pady=1)
            lbl_k.pack(side="left")
            lbl_d = tk.Label(row, text=desc, font=("Segoe UI", 8), fg="#e4e4e7", bg="#27272a")
            lbl_d.pack(side="left", padx=(8, 0))

        # Bottom Action Bar
        bottom = tk.Frame(self.root, bg="#27272a", height=55)
        bottom.pack(fill="x", side="bottom")
        bottom.pack_propagate(False)

        btn_cancel = tk.Button(
            bottom,
            text="Cancel",
            font=("Segoe UI", 9),
            bg="#3f3f46",
            fg="#f4f4f5",
            relief="flat",
            width=10,
            cursor="hand2",
            command=self.root.destroy
        )
        btn_cancel.pack(side="right", padx=(6, 20), pady=12)

        btn_save = tk.Button(
            bottom,
            text="Save & Apply",
            font=("Segoe UI", 9, "bold"),
            bg="#0284c7",
            fg="#ffffff",
            activebackground="#0369a1",
            activeforeground="#ffffff",
            relief="flat",
            width=12,
            cursor="hand2",
            command=self._save_and_apply
        )
        btn_save.pack(side="right", padx=6, pady=12)

    def _on_register_driver_elevated(self):
        from vcam_manager import register_system_wide_elevated
        vname = self.vname_var.get().strip() or "Asus Camera"
        success = register_system_wide_elevated(vname)
        if success:
            messagebox.showinfo("Driver Registration", f"Requested system-wide registration for '{vname}'. Check the UAC prompt if shown.")
        else:
            messagebox.showwarning("Driver Registration", "Failed to launch elevated registration.")

    def _refresh_cameras(self):
        cams = get_physical_cameras(self.config.virtual_camera_name)
        names = [f"[{c['index']}] {c['name']}" for c in cams]
        self.cam_combo["values"] = names
        if names:
            # Match current config
            matched = False
            for n in names:
                if self.config.input_camera in n:
                    self.cam_var.set(n)
                    matched = True
                    break
            if not matched:
                self.cam_var.set(names[0])
        else:
            self.cam_var.set("No physical cameras detected")

    def _save_and_apply(self):
        # 1. Input camera
        selected_cam_str = self.cam_var.get()
        if selected_cam_str and selected_cam_str != "No physical cameras detected":
            try:
                # Format: [0] Camera Name
                idx_str = selected_cam_str.split("]")[0].replace("[", "").strip()
                cam_name = selected_cam_str.split("]", 1)[1].strip()
                self.config.input_camera_index = int(idx_str)
                self.config.input_camera = cam_name
            except Exception:
                pass

        # 2. Virtual camera name
        new_vname = self.vname_var.get().strip()
        if not new_vname:
            new_vname = "Asus Camera"
        self.config.virtual_camera_name = new_vname

        # 3. Delay
        try:
            val_delay = int(self.delay_var.get())
            self.config.delay_ms = max(0, val_delay)
        except Exception:
            pass

        # 4. Resolution
        res_str = self.res_var.get()
        if "1920" in res_str:
            self.config.set("resolution_width", 1920, auto_save=False)
            self.config.set("resolution_height", 1080, auto_save=False)
        elif "1280" in res_str:
            self.config.set("resolution_width", 1280, auto_save=False)
            self.config.set("resolution_height", 720, auto_save=False)
        else:
            self.config.set("resolution_width", 640, auto_save=False)
            self.config.set("resolution_height", 480, auto_save=False)

        # 5. Startup options
        autostart_enabled = self.autostart_var.get()
        set_autostart(autostart_enabled)
        self.config.start_with_windows = autostart_enabled
        self.config.auto_start_camera = self.autocamera_var.get()

        self.config.save()

        if self.on_apply:
            self.on_apply()

        self.root.destroy()
