"""
Global Hotkey Manager for Windows.
Uses native Win32 RegisterHotKey to listen for system-wide shortcuts
without any external dependencies or low-level keyboard hooks.
"""

import ctypes
from ctypes import wintypes
import threading
from typing import Callable, Dict

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

WM_HOTKEY = 0x0312
WM_QUIT = 0x0012

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000

# Virtual Key Codes
VK_C = 0x43  # 'C' for Freeze/Capture
VK_V = 0x56  # 'V' for Video/Resume
VK_D = 0x44  # 'D' for Start/Stop Delay toggle
VK_0 = 0x30  # '0' for Live 0ms Passthrough
VK_UP = 0x26
VK_DOWN = 0x28

class HotkeyManager:
    def __init__(self):
        self._thread: threading.Thread = None
        self._thread_id: int = 0
        self._stop_event = threading.Event()
        self._callbacks: Dict[int, Callable[[], None]] = {}
        self._registered_ids = []

        # Registered Actions
        self.on_freeze: Callable[[], None] = None
        self.on_resume: Callable[[], None] = None
        self.on_resume_live: Callable[[], None] = None
        self.on_toggle_delay: Callable[[], None] = None
        self.on_delay_increase: Callable[[], None] = None
        self.on_delay_decrease: Callable[[], None] = None

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="HotkeyThread")
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread_id:
            user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.5)

    def _run_loop(self):
        self._thread_id = kernel32.GetCurrentThreadId()

        # Hotkey IDs
        HK_FREEZE = 101          # Ctrl + Alt + C
        HK_RESUME = 102          # Ctrl + Alt + V
        HK_TOGGLE_DELAY = 106    # Ctrl + Alt + D
        HK_RESUME_LIVE = 103     # Ctrl + Alt + 0
        HK_DELAY_INC = 104       # Ctrl + Alt + UP
        HK_DELAY_DEC = 105       # Ctrl + Alt + DOWN

        mods = MOD_CONTROL | MOD_ALT | MOD_NOREPEAT

        hotkey_defs = [
            (HK_FREEZE, mods, VK_C),
            (HK_RESUME, mods, VK_V),
            (HK_TOGGLE_DELAY, mods, VK_D),
            (HK_RESUME_LIVE, mods, VK_0),
            (HK_DELAY_INC, mods, VK_UP),
            (HK_DELAY_DEC, mods, VK_DOWN),
        ]

        registered = []
        for hk_id, fs_mods, vk in hotkey_defs:
            if user32.RegisterHotKey(None, hk_id, fs_mods, vk):
                registered.append(hk_id)
            else:
                print(f"[HotkeyManager] Could not register hotkey ID {hk_id}")

        self._registered_ids = registered

        msg = wintypes.MSG()
        while not self._stop_event.is_set():
            ret = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if ret <= 0 or msg.message == WM_QUIT:
                break

            if msg.message == WM_HOTKEY:
                hk_id = msg.wParam
                if hk_id == HK_FREEZE and self.on_freeze:
                    self.on_freeze()
                elif hk_id == HK_RESUME and self.on_resume:
                    self.on_resume()
                elif hk_id == HK_TOGGLE_DELAY and self.on_toggle_delay:
                    self.on_toggle_delay()
                elif hk_id == HK_RESUME_LIVE and self.on_resume_live:
                    self.on_resume_live()
                elif hk_id == HK_DELAY_INC and self.on_delay_increase:
                    self.on_delay_increase()
                elif hk_id == HK_DELAY_DEC and self.on_delay_decrease:
                    self.on_delay_decrease()

        for hk_id in self._registered_ids:
            try:
                user32.UnregisterHotKey(None, hk_id)
            except Exception:
                pass
        self._registered_ids.clear()
        print("[HotkeyManager] Hotkeys unregistered.")
