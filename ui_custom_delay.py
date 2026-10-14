"""
Custom delay input dialog for CamDelay.
Appears when the user selects 'Custom Delay...' from the system tray.
"""

import tkinter as tk
from tkinter import ttk

def show_custom_delay_dialog(current_delay_ms: int, on_save_callback):
    """Opens a centered, modal custom delay input dialog."""
    root = tk.Toplevel()
    root.title("Set Custom Delay")
    root.geometry("340x210")
    root.resizable(False, False)
    root.attributes("-topmost", True)
    root.configure(bg="#1e1e24")

    # Center window
    root.update_idletasks()
    x = (root.winfo_screenwidth() - 340) // 2
    y = (root.winfo_screenheight() - 210) // 2
    root.geometry(f"+{x}+{y}")

    style = ttk.Style(root)
    style.theme_use("clam")

    # Title label
    lbl_title = tk.Label(
        root,
        text="Custom Video Delay",
        font=("Segoe UI", 12, "bold"),
        fg="#edf2f4",
        bg="#1e1e24"
    )
    lbl_title.pack(pady=(16, 4))

    lbl_desc = tk.Label(
        root,
        text="Enter video delay in milliseconds (0 - 10000 ms):",
        font=("Segoe UI", 9),
        fg="#8d99ae",
        bg="#1e1e24"
    )
    lbl_desc.pack(pady=(0, 12))

    # Entry frame
    entry_frame = tk.Frame(root, bg="#1e1e24")
    entry_frame.pack(pady=4)

    val_var = tk.StringVar(value=str(current_delay_ms))
    entry = tk.Entry(
        entry_frame,
        textvariable=val_var,
        font=("Segoe UI", 12),
        width=10,
        justify="center",
        bg="#2b2d42",
        fg="#edf2f4",
        insertbackground="#edf2f4",
        relief="flat"
    )
    entry.pack(side="left", padx=(0, 6), ipady=4)
    entry.focus_set()
    entry.select_range(0, tk.END)

    lbl_ms = tk.Label(
        entry_frame,
        text="ms",
        font=("Segoe UI", 12, "bold"),
        fg="#8d99ae",
        bg="#1e1e24"
    )
    lbl_ms.pack(side="left")

    err_lbl = tk.Label(
        root,
        text="",
        font=("Segoe UI", 8),
        fg="#ef233c",
        bg="#1e1e24"
    )
    err_lbl.pack(pady=2)

    def apply_val(event=None):
        try:
            val = int(val_var.get().strip())
            if val < 0 or val > 60000:
                err_lbl.config(text="Delay must be between 0 and 60,000 ms")
                return
            on_save_callback(val)
            root.destroy()
        except ValueError:
            err_lbl.config(text="Please enter a valid number")

    root.bind("<Return>", apply_val)
    root.bind("<Escape>", lambda e: root.destroy())

    # Buttons
    btn_frame = tk.Frame(root, bg="#1e1e24")
    btn_frame.pack(pady=(12, 16))

    btn_cancel = tk.Button(
        btn_frame,
        text="Cancel",
        font=("Segoe UI", 9),
        bg="#3d405b",
        fg="#edf2f4",
        activebackground="#4a4e69",
        activeforeground="#ffffff",
        relief="flat",
        width=10,
        cursor="hand2",
        command=root.destroy
    )
    btn_cancel.pack(side="left", padx=6)

    btn_ok = tk.Button(
        btn_frame,
        text="Apply",
        font=("Segoe UI", 9, "bold"),
        bg="#3a86ff",
        fg="#ffffff",
        activebackground="#2563eb",
        activeforeground="#ffffff",
        relief="flat",
        width=10,
        cursor="hand2",
        command=apply_val
    )
    btn_ok.pack(side="left", padx=6)

    return root
