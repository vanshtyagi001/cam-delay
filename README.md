# CamDelay

> A lightweight Windows utility that captures any physical webcam, applies a configurable video delay, and broadcasts the feed as a separate virtual camera device.

![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%2F%2011-blue)
![Python](https://img.shields.io/badge/Python-3.10%2B-green)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

---

## Overview

```text
Physical Camera  ──▶  Precision Delay Buffer  ──▶  Virtual Camera ("Asus Camera")
                            │
              [Ctrl+Alt+C] Freeze Frame
              [Ctrl+Alt+V] Resume with Delay
              [Ctrl+Alt+D] Toggle Delay On/Off
```

CamDelay runs silently in your Windows system tray with **zero visible console windows**. It allows you to introduce artificial delay, freeze frames on demand, and seamlessly feed the result into video conferencing software such as **Zoom, Discord, Google Meet, Microsoft Teams, and OBS Studio**.

---

## Features

* **Real-time Delay Control**: Adjust latency from `0 ms` (passthrough) up to `1000+ ms` on the fly without restarting streams or client apps.
* **Instant Freeze & Resume**:
  * **Freeze**: Lock the video on the current frame while keeping the virtual camera alive.
  * **Resume**: Jump directly to the live feed with your configured delay applied.
* **Low Latency Passthrough (`0 ms`)**: Toggle delay off at any time for direct, real-time video.
* **Zero Console Window**: Operates unobtrusively from the Windows notification area (System Tray).
* **Universal Compatibility**: DirectShow virtual camera driver recognizable by any Windows camera app.
* **Auto-Reconnect**: Gracefully handles USB webcam disconnections and automatically resumes streaming upon reconnect.
* **Side-by-Side Preview**: Includes a built-in monitor to inspect live vs. delayed frames in real-time.

---

## Global Shortcuts

CamDelay registers native system-wide shortcuts that function even when other applications (Zoom, games, browser) are active:

| Shortcut | Action | Description |
| :--- | :--- | :--- |
| **`Ctrl + Alt + C`** | **Freeze Frame** | Freezes the virtual camera feed on the current frame. |
| **`Ctrl + Alt + V`** | **Resume Feed** | Resumes streaming from live video with the configured delay. |
| **`Ctrl + Alt + D`** | **Toggle Delay** | Switches between your target delay and `0 ms` passthrough. |
| **`Ctrl + Alt + 0`** | **Instant Live** | Unfreezes and immediately drops latency to `0 ms`. |
| **`Ctrl + Alt + ↑`** | **Increase Delay** | Bumps delay up by `+50 ms`. |
| **`Ctrl + Alt + ↓`** | **Decrease Delay** | Lowers delay down by `-50 ms`. |

---

## Quick Start

### 1. Installation

Ensure you have Python 3.10+ installed, then install the required dependencies:

```bash
pip install -r requirements.txt
```

### 2. Launching

Run the silent launcher:
* Double-click **`start.bat`** (or execute `wscript.exe run_silently.vbs`).

A camera icon will appear in your **Windows System Tray** (click `^` on the taskbar if hidden).

### 3. Usage

1. Open **Zoom**, **Discord**, **Google Meet**, or **Teams**.
2. Select **`Asus Camera`** as your video device.
3. Use the system tray icon or keyboard shortcuts (`Ctrl+Alt+C` / `Ctrl+Alt+V` / `Ctrl+Alt+D`) to control the stream.

### 4. Stopping

* Right-click the system tray icon and select **Exit**, or run **`stop.bat`**.

---

## System Tray Menu

Right-click the tray icon to access quick controls:

```text
Asus Camera                            (Virtual Device Name)
Status: Active (200 ms)                (Live Status)
──────────────────────────────────────
Input Camera                           (Select physical webcam)
Delay                                  (0, 50, 100, 200, 300, 500, 1000 ms)
Custom Delay...                        (Enter custom ms)
──────────────────────────────────────
⏹ Stop Delay / ▶ Start Delay [Ctrl+Alt+D]
❄ Freeze Frame / ▶ Resume    [Ctrl+Alt+C / Ctrl+Alt+V]
──────────────────────────────────────
Live vs Delayed Preview...             (Side-by-side monitor)
Settings...                            (Preferences & autostart)
Exit                                   (Quit)
```

---

## Configuration

Click **Settings...** from the tray menu to configure:
* **Input Camera**: Choose your source webcam.
* **Virtual Camera Name**: Rename the virtual device (default: `Asus Camera`).
* **Default Delay**: Set your startup delay in milliseconds.
* **Maximum Resolution**: Select between `1080p`, `720p`, or `480p`.
* **Start with Windows**: Toggle automatic startup upon user login.
* **Admin Registration**: Optionally register the driver system-wide via elevated UAC.

---

## Project Structure

```text
cam-delay/
├── driver/                 # 64-bit and 32-bit DirectShow filter DLLs
├── main.py                 # Application entry point & single-instance mutex
├── camera_worker.py        # Capture loop, delay buffer & streaming engine
├── hotkey_manager.py       # Win32 global shortcut listener
├── camera_enumerator.py    # DirectShow physical camera device discovery
├── vcam_manager.py         # Virtual camera driver registration & naming
├── tray_app.py             # System tray icon and dynamic context menus
├── ui_settings.py          # Settings configuration dialog
├── ui_preview.py           # Side-by-side live vs delayed video monitor
├── ui_custom_delay.py      # Quick custom delay dialog
├── autostart.py            # Windows startup registry integration
├── start.bat               # 1-click launcher
├── stop.bat                # 1-click shutdown script
├── run_silently.vbs        # VBScript runner (no console popup)
└── requirements.txt        # Python package dependencies
```

---

## License

This project is licensed under the [MIT License](LICENSE).
