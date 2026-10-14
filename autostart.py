"""
Windows Autostart manager for CamDelay.
Registers or unregisters the app in HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run.
"""

import sys
import os
import winreg
from pathlib import Path

REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "CamDelay"

def get_launch_command() -> str:
    """Returns the silent execution command for starting CamDelay with Windows."""
    base_dir = Path(__file__).parent.resolve()
    vbs_path = base_dir / "run_silently.vbs"
    if vbs_path.exists():
        return f'wscript.exe "{vbs_path}"'
    
    # Fallback to pythonw.exe
    python_dir = Path(sys.executable).parent
    pythonw = python_dir / "pythonw.exe"
    if not pythonw.exists():
        pythonw = Path(sys.executable)
    main_py = base_dir / "main.py"
    return f'"{pythonw}" "{main_py}"'

def is_autostart_enabled() -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_READ) as k:
            val, _ = winreg.QueryValueEx(k, APP_NAME)
            return bool(val)
    except FileNotFoundError:
        return False
    except Exception as e:
        print(f"[Autostart] Check error: {e}")
        return False

def set_autostart(enable: bool) -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_SET_VALUE) as k:
            if enable:
                cmd = get_launch_command()
                winreg.SetValueEx(k, APP_NAME, 0, winreg.REG_SZ, cmd)
                print(f"[Autostart] Enabled with command: {cmd}")
            else:
                try:
                    winreg.DeleteValue(k, APP_NAME)
                    print("[Autostart] Disabled successfully.")
                except FileNotFoundError:
                    pass
        return True
    except Exception as e:
        print(f"[Autostart] Failed to update autostart setting: {e}")
        return False

if __name__ == "__main__":
    current = is_autostart_enabled()
    print(f"Current autostart status: {current}")
