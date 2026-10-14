"""
Camera enumeration utility for Windows.
Enumerates all available DirectShow video capture devices and filters out
the virtual camera itself to avoid feedback loops.
"""

from typing import List, Dict, Optional
import ctypes
from ctypes import wintypes
import comtypes
import comtypes.client
from comtypes import GUID, IUnknown, COMMETHOD, HRESULT
import comtypes.automation
import cv2

CLSID_SystemDeviceEnum = GUID('{62BE5D10-60EB-11D0-BD3B-00A0C911CE86}')
CLSID_VideoInputDeviceCategory = GUID('{860BB310-5D01-11D0-BD3B-00A0C911CE86}')

class IPropertyBag(IUnknown):
    _iid_ = GUID('{55272A00-42CB-11CE-8135-00AA004BB851}')
    _methods_ = [
        COMMETHOD([], HRESULT, 'Read',
                  (['in'], wintypes.LPCWSTR, 'pszPropName'),
                  (['in', 'out'], ctypes.POINTER(comtypes.automation.VARIANT), 'pVar'),
                  (['in'], ctypes.c_void_p, 'pErrorLog')),
        COMMETHOD([], HRESULT, 'Write',
                  (['in'], wintypes.LPCWSTR, 'pszPropName'),
                  (['in'], ctypes.POINTER(comtypes.automation.VARIANT), 'pVar'))
    ]

class IMoniker(IUnknown):
    _iid_ = GUID('{0000000F-0000-0000-C000-000000000046}')

class IEnumMoniker(IUnknown):
    _iid_ = GUID('{00000102-0000-0000-C000-000000000046}')

IMoniker._methods_ = [
    COMMETHOD([], HRESULT, 'GetClassID', (['out'], ctypes.POINTER(GUID), 'pClassID')),
    COMMETHOD([], HRESULT, 'IsDirty'),
    COMMETHOD([], HRESULT, 'Load', (['in'], ctypes.c_void_p, 'pStm')),
    COMMETHOD([], HRESULT, 'Save', (['in'], ctypes.c_void_p, 'pStm'), (['in'], wintypes.BOOL, 'fClearDirty')),
    COMMETHOD([], HRESULT, 'GetSizeMax', (['out'], ctypes.POINTER(ctypes.c_uint64), 'pcbSize')),
    COMMETHOD([], HRESULT, 'BindToObject',
              (['in'], ctypes.c_void_p, 'pbc'),
              (['in'], ctypes.POINTER(IMoniker), 'pmkToLeft'),
              (['in'], ctypes.POINTER(GUID), 'riidResult'),
              (['out'], ctypes.POINTER(ctypes.c_void_p), 'ppvResult')),
    COMMETHOD([], HRESULT, 'BindToStorage',
              (['in'], ctypes.c_void_p, 'pbc'),
              (['in'], ctypes.POINTER(IMoniker), 'pmkToLeft'),
              (['in'], ctypes.POINTER(GUID), 'riid'),
              (['out'], ctypes.POINTER(ctypes.POINTER(IUnknown)), 'ppvObj'))
]

IEnumMoniker._methods_ = [
    COMMETHOD([], HRESULT, 'Next',
              (['in'], wintypes.ULONG, 'celt'),
              (['out'], ctypes.POINTER(ctypes.POINTER(IMoniker)), 'rgelt'),
              (['out'], ctypes.POINTER(wintypes.ULONG), 'pceltFetched')),
    COMMETHOD([], HRESULT, 'Skip', (['in'], wintypes.ULONG, 'celt')),
    COMMETHOD([], HRESULT, 'Reset'),
    COMMETHOD([], HRESULT, 'Clone', (['out'], ctypes.POINTER(ctypes.POINTER(IEnumMoniker)), 'ppenum'))
]

class ICreateDevEnum(IUnknown):
    _iid_ = GUID('{29840822-5B84-11D0-BD3B-00A0C911CE86}')
    _methods_ = [
        COMMETHOD([], HRESULT, 'CreateClassEnumerator',
                  (['in'], ctypes.POINTER(GUID), 'pType'),
                  (['out'], ctypes.POINTER(ctypes.POINTER(IEnumMoniker)), 'ppEnumMoniker'),
                  (['in'], wintypes.DWORD, 'dwFlags'))
    ]

def get_all_directshow_devices() -> List[Dict[str, any]]:
    """Enumerates all DirectShow video input devices in order of their DirectShow index."""
    devices = []
    need_uninit = False
    try:
        import comtypes
        try:
            comtypes.CoInitialize()
            need_uninit = True
        except Exception:
            pass
        dev_enum = comtypes.client.CreateObject(CLSID_SystemDeviceEnum, interface=ICreateDevEnum)
        enum_moniker = dev_enum.CreateClassEnumerator(ctypes.byref(CLSID_VideoInputDeviceCategory), 0)
        if not enum_moniker:
            return devices

        index = 0
        while True:
            moniker, fetched = enum_moniker.Next(1)
            if not fetched or not moniker:
                break
            try:
                prop_bag_unk = moniker.BindToStorage(None, None, ctypes.byref(IPropertyBag._iid_))
                prop_bag = prop_bag_unk.QueryInterface(IPropertyBag)
                var = comtypes.automation.VARIANT()
                friendly_name = prop_bag.Read('FriendlyName', var, None)
                devices.append({
                    "index": index,
                    "name": str(friendly_name) if friendly_name else f"Camera {index}",
                })
            except Exception as e:
                devices.append({
                    "index": index,
                    "name": f"Camera {index}",
                })
            index += 1
    except Exception as e:
        print(f"[CameraEnumerator] COM error enumerating devices: {e}")
    finally:
        if need_uninit:
            try:
                comtypes.CoUninitialize()
            except Exception:
                pass
    return devices

def get_physical_cameras(virtual_camera_name: str = "Asus Camera") -> List[Dict[str, any]]:
    """
    Returns a list of physical cameras available for input.
    Excludes the virtual camera itself to prevent feedback.
    """
    all_devs = get_all_directshow_devices()
    vcam_lower = virtual_camera_name.strip().lower()
    
    physical_cams = []
    for dev in all_devs:
        name = dev["name"].strip()
        name_lower = name.lower()
        # Filter out current virtual camera and known virtual camera drivers
        if name_lower == vcam_lower:
            continue
        if "unity video capture" in name_lower or "unitycapture" in name_lower:
            continue
        physical_cams.append(dev)

    # Fallback if DirectShow enumeration returned empty
    if not physical_cams:
        for idx in range(3):
            cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
            if cap.isOpened():
                ret, _ = cap.read()
                cap.release()
                if ret:
                    physical_cams.append({
                        "index": idx,
                        "name": f"Camera {idx}"
                    })

    return physical_cams

if __name__ == "__main__":
    cams = get_physical_cameras()
    print("Physical cameras found:")
    for c in cams:
        print(f"  [{c['index']}] {c['name']}")
