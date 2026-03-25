# X68 HE Virtual Gamepad

**Turn your analog Hall Effect keyboard into a true analog Xbox 360 controller.**

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/platform-Windows-lightgrey.svg)](#requirements)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

---
## **Fork that forks on X68 HE**

This project reverse engineers the vendor-specific HID protocol of the **Attack Shark X68 HE** Hall Effect keyboard to extract real-time 16-bit analog key travel data, then feeds it into a virtual Xbox 360 controller via ViGEmBus. The result is **true analog stick input from WASD keys** -- not binary on/off, but smooth, pressure-sensitive movement proportional to how far you press each key.

## Features

- **True analog input** -- WASD keys drive the left stick with full 0-100% travel, not digital emulation
- **Two operating modes:**
  - **Hybrid** -- Only WASD maps to the left stick; keyboard and mouse pass through to the game normally. Ideal for games that support simultaneous gamepad + keyboard/mouse input.
  - **Full Controller** -- All keys mapped to Xbox buttons, sticks, and triggers. For games that require a single input device.
- **Dual analog sticks** (Full Controller mode) -- Left stick (WASD) and right stick (IJKL) with independent analog axes
- **Analog triggers** (Full Controller mode) -- Left and right triggers respond to key travel depth
- **All 67 keys mapped** -- Complete key-to-ID mapping for every key on the 65% layout
- **Live controller visualization** -- Real-time GUI showing stick position, trigger bars, and active buttons
- **Configurable curves** -- Deadzone, smoothing (EMA), and sensitivity curve (linear/exponential) sliders
- **Customizable bindings** -- Remap any keyboard key to any gamepad action via the settings panel
- **Persistent configuration** -- Bindings, settings, and selected mode saved to JSON, loaded automatically on startup
- **Interactive key mapper** -- Visual tool to map (or remap) every physical key to its analog ID
- **WebHID interceptor** -- JavaScript snippet for capturing the keyboard's protocol traffic in the browser
- **120 Hz update rate** -- Gamepad state refreshed at ~120 Hz for low-latency response
- **One-click launcher** -- `run.vbs` to start the app with a double-click, no terminal needed

## Requirements

- **OS:** Windows 10 or later (uses native Windows HID API via ctypes)
- **Python:** 3.10 or later
- **Hardware:** Attack Shark X68 HE keyboard (Hall Effect variant)
- **ViGEmBus driver:** Required for virtual Xbox 360 controller emulation
  - Download from [ViGEmBus releases](https://github.com/nefarius/ViGEmBus/releases)

#
