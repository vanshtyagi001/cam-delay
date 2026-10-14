"""
CamDelay - Main Application Entry Point
A silent background Windows utility that creates a delayed virtual camera source.
"""

import sys
import os
import ctypes
from ctypes import wintypes
import tkinter as tk
from config import Config
from vcam_manager import ensure_virtual_camera
from camera_worker import CameraWorker
from tray_app import TrayApp

# Single-instance mutex name
MUTEX_NAME = "Global\\CamDelay_Application_SingleInstance_Mutex"

def setup_logging():
    """Redirects stdout and stderr to a log file if running headless under pythonw."""
    try:
        from config import get_config_dir
        log_file = get_config_dir() / "app.log"
        # If stdout is None (pythonw.exe), redirect to file
        if sys.stdout is None:
            sys.stdout = open(log_file, "a", encoding="utf-8", buffering=1)
        if sys.stderr is None:
            sys.stderr = open(log_file, "a", encoding="utf-8", buffering=1)
    except Exception:
        pass

def acquire_single_instance_mutex():
    """Ensures only one instance of CamDelay runs at a time."""
    kernel32 = ctypes.windll.kernel32
    mutex = kernel32.CreateMutexW(None, False, MUTEX_NAME)
    last_error = kernel32.GetLastError()
    ERROR_ALREADY_EXISTS = 183
    if last_error == ERROR_ALREADY_EXISTS:
        return None
    return mutex

def main():
    setup_logging()
    # 1. Single Instance Check
    mutex = acquire_single_instance_mutex()
    if not mutex:
        print("[CamDelay] Another instance of CamDelay is already running in the background.")
        sys.exit(0)

    # 2. Load Configuration
    config = Config()

    # 3. Ensure DirectShow Virtual Camera Driver Registration
    ensure_virtual_camera(config.virtual_camera_name)

    # 4. Create Hidden Tkinter Root Window
    root = tk.Tk()
    root.withdraw()  # Keeps root window hidden; no console or taskbar window

    # 5. Initialize Camera Worker Engine
    worker = CameraWorker(config)

    # 6. Initialize System Tray App
    app = TrayApp(root, worker, config)

    try:
        app.run()
    except KeyboardInterrupt:
        pass
    finally:
        worker.stop()
        if mutex:
            ctypes.windll.kernel32.CloseHandle(mutex)

if __name__ == "__main__":
    main()
