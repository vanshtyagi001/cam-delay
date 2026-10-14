"""
Virtual Camera Manager for Windows.
Handles registration, naming, and configuration of the DirectShow virtual camera filter.
Operates at user-level (HKCU) so administrator privileges are not strictly required,
while also supporting system-wide registration if desired.
"""

import os
import sys
import winreg
from pathlib import Path

CLSID_FILTER_64 = "{5C2CD55C-92AD-4999-8666-912BD3E70010}"
CLSID_FILTER_32 = "{5C2CD55C-92AD-4999-8666-912BD3E70020}"
CLSID_VIDEO_INPUT_CATEGORY = "{860BB310-5D01-11D0-BD3B-00A0C911CE86}"

def get_driver_dir() -> Path:
    """Returns directory containing the DirectShow filter DLLs."""
    base_dir = Path(__file__).parent.resolve()
    driver_dir = base_dir / "driver"
    return driver_dir

def get_filter_dll(is_64bit: bool = True) -> Path:
    driver_dir = get_driver_dir()
    if is_64bit:
        return driver_dir / "UnityCaptureFilter64.dll"
    else:
        return driver_dir / "UnityCaptureFilter32.dll"

def is_virtual_camera_registered(friendly_name: str = "Asus Camera") -> bool:
    """Checks if the virtual camera is currently registered in HKCU."""
    try:
        key_path = rf"Software\Classes\CLSID\{CLSID_FILTER_64}"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as k:
            val, _ = winreg.QueryValueEx(k, "")
            if val != friendly_name:
                return False
        
        inst_path = rf"Software\Classes\CLSID\{CLSID_VIDEO_INPUT_CATEGORY}\Instance\{CLSID_FILTER_64}"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, inst_path) as k:
            val, _ = winreg.QueryValueEx(k, "FriendlyName")
            return val == friendly_name
    except FileNotFoundError:
        return False
    except Exception as e:
        print(f"[VCamManager] Verification check error: {e}")
        return False

def register_virtual_camera(friendly_name: str = "Asus Camera") -> bool:
    """
    Registers the virtual camera filter in HKCU with the specified friendly name.
    Works for both 64-bit and 32-bit client applications.
    """
    dll64 = get_filter_dll(is_64bit=True)
    dll32 = get_filter_dll(is_64bit=False)

    if not dll64.exists():
        raise FileNotFoundError(f"Virtual camera driver 64-bit DLL not found: {dll64}")

    try:
        # 1. Register 64-bit COM filter
        key_path_64 = rf"Software\Classes\CLSID\{CLSID_FILTER_64}"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path_64) as k:
            winreg.SetValueEx(k, "", 0, winreg.REG_SZ, friendly_name)
            with winreg.CreateKey(k, "InprocServer32") as k_inproc:
                winreg.SetValueEx(k_inproc, "", 0, winreg.REG_SZ, str(dll64))
                winreg.SetValueEx(k_inproc, "ThreadingModel", 0, winreg.REG_SZ, "Both")

        # 2. Register 64-bit DirectShow Video Capture Device Category
        inst_path_64 = rf"Software\Classes\CLSID\{CLSID_VIDEO_INPUT_CATEGORY}\Instance\{CLSID_FILTER_64}"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, inst_path_64) as k_inst:
            winreg.SetValueEx(k_inst, "CLSID", 0, winreg.REG_SZ, CLSID_FILTER_64)
            winreg.SetValueEx(k_inst, "FriendlyName", 0, winreg.REG_SZ, friendly_name)
            winreg.SetValueEx(k_inst, "DevicePath", 0, winreg.REG_SZ, f"camdelay:{friendly_name.lower().replace(' ', '_')}")

        # 3. Register 32-bit (under WOW6432Node) if 32-bit DLL exists
        if dll32.exists():
            key_path_32 = rf"Software\Classes\WOW6432Node\CLSID\{CLSID_FILTER_32}"
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path_32) as k:
                winreg.SetValueEx(k, "", 0, winreg.REG_SZ, friendly_name)
                with winreg.CreateKey(k, "InprocServer32") as k_inproc:
                    winreg.SetValueEx(k_inproc, "", 0, winreg.REG_SZ, str(dll32))
                    winreg.SetValueEx(k_inproc, "ThreadingModel", 0, winreg.REG_SZ, "Both")

            inst_path_32 = rf"Software\Classes\WOW6432Node\CLSID\{CLSID_VIDEO_INPUT_CATEGORY}\Instance\{CLSID_FILTER_32}"
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, inst_path_32) as k_inst:
                winreg.SetValueEx(k_inst, "CLSID", 0, winreg.REG_SZ, CLSID_FILTER_32)
                winreg.SetValueEx(k_inst, "FriendlyName", 0, winreg.REG_SZ, friendly_name)
                winreg.SetValueEx(k_inst, "DevicePath", 0, winreg.REG_SZ, f"camdelay:{friendly_name.lower().replace(' ', '_')}")

        print(f"[VCamManager] Successfully registered virtual camera as '{friendly_name}'")
        return True
    except Exception as e:
        print(f"[VCamManager] Failed to register virtual camera: {e}")
        return False

def register_system_wide_elevated(friendly_name: str = "Asus Camera") -> bool:
    """Triggers elevated UAC registration to register filter in HKLM system-wide."""
    try:
        import ctypes
        script_path = str(Path(__file__).parent.resolve() / "install_driver.bat")
        ret = ctypes.windll.shell32.ShellExecuteW(
            None,
            "runas",
            "cmd.exe",
            f'/c "{script_path}" "{friendly_name}"',
            None,
            1
        )
        return ret > 32
    except Exception as e:
        print(f"[VCamManager] Elevated registration failed: {e}")
        return False

def unregister_virtual_camera():
    """Removes user-level virtual camera registration entries."""
    def delete_key_tree(root, path):
        try:
            with winreg.OpenKey(root, path, 0, winreg.KEY_ALL_ACCESS) as k:
                while True:
                    try:
                        subkey = winreg.EnumKey(k, 0)
                        delete_key_tree(root, f"{path}\\{subkey}")
                    except OSError:
                        break
            winreg.DeleteKey(root, path)
        except FileNotFoundError:
            pass
        except Exception as e:
            print(f"[VCamManager] Error removing {path}: {e}")

    delete_key_tree(winreg.HKEY_CURRENT_USER, rf"Software\Classes\CLSID\{CLSID_VIDEO_INPUT_CATEGORY}\Instance\{CLSID_FILTER_64}")
    delete_key_tree(winreg.HKEY_CURRENT_USER, rf"Software\Classes\CLSID\{CLSID_FILTER_64}")
    delete_key_tree(winreg.HKEY_CURRENT_USER, rf"Software\Classes\WOW6432Node\CLSID\{CLSID_VIDEO_INPUT_CATEGORY}\Instance\{CLSID_FILTER_32}")
    delete_key_tree(winreg.HKEY_CURRENT_USER, rf"Software\Classes\WOW6432Node\CLSID\{CLSID_FILTER_32}")
    print("[VCamManager] Virtual camera registration removed.")

def ensure_virtual_camera(friendly_name: str = "Asus Camera") -> bool:
    """Ensures that the virtual camera is registered with the specified friendly name."""
    if not is_virtual_camera_registered(friendly_name):
        return register_virtual_camera(friendly_name)
    return True

if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "Asus Camera"
    ensure_virtual_camera(name)
