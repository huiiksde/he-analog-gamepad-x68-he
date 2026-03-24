"""
X68PRO HE - Interactive Key Mapper GUI
Maps every physical key to its analog key_id.
Saves a complete config JSON for the virtual gamepad.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import ctypes
from ctypes import wintypes
import pywinusb.hid as hid_pywin
import hid as hid_api
import threading
import time
import json
import os

VID = 0x3151
PID = 0x502D

ENABLE_CMD = [0x1B, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0xE3] + [0x00] * 56
DISABLE_CMD = [0x1B, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xE4] + [0x00] * 56

hid_dll = ctypes.WinDLL('hid.dll')
kernel32 = ctypes.WinDLL('kernel32.dll')

# --- Modern Theme Colors ---
COLOR_BG_MAIN = "#0f0f1a"
COLOR_BG_FRAME = "#1a1a2e"
COLOR_BG_INPUT = "#16213e"
COLOR_ACCENT = "#0f3460"
COLOR_TEXT_MAIN = "#eaeaea"
COLOR_TEXT_DIM = "#888888"
COLOR_HIGHLIGHT = "#00ccff"
COLOR_SUCCESS = "#00ff88"
COLOR_DANGER = "#ff4444"
COLOR_WARNING = "#ffcc00"
COLOR_BTN_NORMAL = "#2a2a4e"
COLOR_BTN_HOVER = "#3a3a6e"
COLOR_KEY_IDLE = "#2a2a4e"
COLOR_KEY_MAPPED = "#1a5a2a"
COLOR_KEY_ACTIVE = "#cc4400"

KEYBOARD_LAYOUT = [
    [("ESC", 1), ("1", 1), ("2", 1), ("3", 1), ("4", 1), ("5", 1), ("6", 1),
     ("7", 1), ("8", 1), ("9", 1), ("0", 1), ("-", 1), ("=", 1), ("BKSP", 2), ("DEL", 1)],
    [("TAB", 1.5), ("Q", 1), ("W", 1), ("E", 1), ("R", 1), ("T", 1), ("Y", 1),
     ("U", 1), ("I", 1), ("O", 1), ("P", 1), ("[", 1), ("]", 1), ("\\", 1.5), ("PGUP", 1)],
    [("CAPS", 1.75), ("A", 1), ("S", 1), ("D", 1), ("F", 1), ("G", 1), ("H", 1),
     ("J", 1), ("K", 1), ("L", 1), (";", 1), ("'", 1), ("ENTER", 2.25), ("PGDN", 1)],
    [("LSHIFT", 2.25), ("Z", 1), ("X", 1), ("C", 1), ("V", 1), ("B", 1), ("N", 1),
     ("M", 1), (",", 1), (".", 1), ("/", 1), ("RSHIFT", 1.75), ("UP", 1)],
    [("LCTRL", 1.25), ("WIN", 1.25), ("LALT", 1.25), ("SPACE", 6.25),
     ("RALT", 1), ("FN", 1), ("LEFT", 1), ("DOWN", 1), ("RIGHT", 1)],
]

ALL_KEYS = []
for row in KEYBOARD_LAYOUT:
    for key_label, _ in row:
        ALL_KEYS.append(key_label)

class KeyMapperGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("X68 HE - Key Mapper")
        self.root.configure(bg=COLOR_BG_MAIN)
        self.root.resizable(True, True)

        # Style
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure("TFrame", background=COLOR_BG_MAIN)
        self.style.configure("TLabel", background=COLOR_BG_MAIN, foreground=COLOR_TEXT_MAIN, font=("Segoe UI", 10))
        self.style.configure("Header.TLabel", font=("Segoe UI", 12, "bold"), foreground=COLOR_HIGHLIGHT)

        self.mapping = {}
        self.current_key_index = -1
        self.is_mapping = False
        self.analog_enabled = False

        self.config_path = None
        self.opened_devices = []
        self.latest_key_id = None
        self.latest_analog = 0
        self.peak_analog = 0
        self.data_lock = threading.Lock()
        self.last_event_time = 0

        self.key_buttons = {}

        self._build_ui()
        self._init_hid()
        self._load_existing()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._update_loop()

    def _build_ui(self):
        self.root.bind_all('<space>', lambda e: 'break')
        self.root.bind_all('<Return>', lambda e: 'break')

        # Top Bar
        top = tk.Frame(self.root, bg=COLOR_BG_FRAME, highlightbackground=COLOR_ACCENT, highlightthickness=1)
        top.pack(fill=tk.X, padx=10, pady=10)

        inner_top = tk.Frame(top, bg=COLOR_BG_FRAME)
        inner_top.pack(fill=tk.X, padx=15, pady=10)

        self.status_label = tk.Label(inner_top, text="● Initializing...", font=("Segoe UI", 12, "bold"), fg=COLOR_SUCCESS, bg=COLOR_BG_FRAME)
        self.status_label.pack(side=tk.LEFT)

        self.progress_label = tk.Label(inner_top, text="0/68 mapped", font=("Segoe UI", 11), fg=COLOR_TEXT_DIM, bg=COLOR_BG_FRAME)
        self.progress_label.pack(side=tk.RIGHT, padx=10)
        
        self.analog_label = tk.Label(inner_top, text="Analog: ---", font=("Consolas", 11), fg=COLOR_WARNING, bg=COLOR_BG_FRAME)
        self.analog_label.pack(side=tk.RIGHT)

        # Keyboard Frame
        kbd_container = tk.Frame(self.root, bg=COLOR_BG_MAIN)
        kbd_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        kbd_frame = tk.Frame(kbd_container, bg=COLOR_BG_FRAME, highlightbackground=COLOR_ACCENT, highlightthickness=1)
        kbd_frame.pack(fill=tk.BOTH, expand=True)

        KEY_W = 52
        KEY_H = 48
        PAD = 3

        for row_idx, row in enumerate(KEYBOARD_LAYOUT):
            row_frame = tk.Frame(kbd_frame, bg=COLOR_BG_FRAME)
            row_frame.pack(anchor=tk.W, pady=PAD, padx=PAD)

            for key_label, width_units in row:
                w = int(KEY_W * width_units) - PAD * 2
                btn = tk.Button(row_frame, text=key_label, width=0, font=("Consolas", 9, "bold"),
                                bg=COLOR_KEY_IDLE, fg=COLOR_TEXT_DIM, activebackground=COLOR_KEY_ACTIVE, 
                                relief=tk.FLAT, bd=0, padx=2, pady=2,
                                command=lambda k=key_label: self._manual_select(k))
                btn.config(height=2)
                btn.pack(side=tk.LEFT, padx=PAD, ipadx=max(0, (w - 40) // 2))
                
                # Hover effects
                btn.bind("<Enter>", lambda e, b=btn: b.config(bg=COLOR_BTN_HOVER) if b['bg'] == COLOR_KEY_IDLE else None)
                btn.bind("<Leave>", lambda e, b=btn: b.config(bg=COLOR_KEY_IDLE) if b['bg'] == COLOR_BTN_HOVER else None)
                
                self.key_buttons[key_label] = btn

        # Controls
        ctrl_frame = tk.Frame(self.root, bg=COLOR_BG_MAIN)
        ctrl_frame.pack(fill=tk.X, padx=10, pady=10)

        self.instr_label = tk.Label(ctrl_frame, text="Press START to begin mapping all keys", 
                                    font=("Segoe UI", 14, "bold"), fg=COLOR_TEXT_MAIN, bg=COLOR_BG_FRAME, 
                                    height=2, relief=tk.FLAT, padx=10)
        self.instr_label.pack(fill=tk.X, pady=(0, 10), ipady=10)

        btn_bar = tk.Frame(ctrl_frame, bg=COLOR_BG_MAIN)
        btn_bar.pack(fill=tk.X)

        self.start_btn = tk.Button(btn_bar, text="START MAPPING", font=("Segoe UI", 11, "bold"), 
                                   bg="#00aa55", fg="white", relief=tk.FLAT, padx=20, pady=10, command=self._start_mapping)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        self._add_hover(self.start_btn, "#00cc66", "#00aa55")

        self.skip_btn = tk.Button(btn_bar, text="SKIP KEY", font=("Segoe UI", 11, "bold"), 
                                  bg="#aa5500", fg="white", relief=tk.FLAT, padx=20, pady=10, command=self._skip_key, state=tk.DISABLED)
        self.skip_btn.pack(side=tk.LEFT, padx=5)
        
        self.undo_btn = tk.Button(btn_bar, text="UNDO", font=("Segoe UI", 11, "bold"), 
                                  bg="#555577", fg="white", relief=tk.FLAT, padx=20, pady=10, command=self._undo_key, state=tk.DISABLED)
        self.undo_btn.pack(side=tk.LEFT, padx=5)

        self.save_btn = tk.Button(btn_bar, text="SAVE CONFIG", font=("Segoe UI", 11, "bold"), 
                                  bg="#2266cc", fg="white", relief=tk.FLAT, padx=20, pady=10, command=self._save_config)
        self.save_btn.pack(side=tk.RIGHT, padx=5)
        self._add_hover(self.save_btn, "#3377dd", "#2266cc")

        self.freemode_btn = tk.Button(btn_bar, text="FREE MODE", font=("Segoe UI", 11, "bold"), 
                                      bg="#663399", fg="white", relief=tk.FLAT, padx=20, pady=10, command=self._toggle_freemode)
        self.freemode_btn.pack(side=tk.RIGHT, padx=5)

        self.free_mode = False

    def _add_hover(self, widget, enter_color, leave_color):
        widget.bind("<Enter>", lambda e: widget.config(bg=enter_color))
        widget.bind("<Leave>", lambda e: widget.config(bg=leave_color))

    def _init_hid(self):
        raw_devices = hid_api.enumerate(VID, PID)
        self.config_path = None
        for d in raw_devices:
            path = d['path']
            if isinstance(path, bytes):
                path = path.decode('utf-8')
            
            # Hardcoding MI_02 because we know it's that channel!
            if 'mi_02' in path.lower():
                self.config_path = path
                break

        hid_devs = hid_pywin.find_all_hid_devices()
        kbd_devs = [d for d in hid_devs if d.vendor_id == VID and d.product_id == PID]

        for d in kbd_devs:
            try:
                d.open()
                d.set_raw_data_handler(self._hid_handler)
                self.opened_devices.append(d)
            except:
                pass

        n = len(self.opened_devices)
        self.status_label.config(
            text=f"● CONNECTED ({n} interfaces)" if n > 0 else "● CONNECTION ERROR",
            fg=COLOR_SUCCESS if n > 0 else COLOR_DANGER
        )

    def _send_feature(self, cmd):
        if not self.config_path:
            return False
        h = kernel32.CreateFileW(self.config_path, 0xC0000000, 0x03, None, 3, 0, None)
        if h == ctypes.c_void_p(-1).value:
            return False
            
        buf = (ctypes.c_byte * 65)()
        buf[0] = 0  # <--- OUR WINNING REPORT ID
        for i in range(64):
            if i < len(cmd):
                buf[i + 1] = cmd[i]
            else:
                buf[i + 1] = 0
                
        r = hid_dll.HidD_SetFeature(h, ctypes.byref(buf), 65)
        kernel32.CloseHandle(h)
        return bool(r)

    def _enable_analog(self):
        if self._send_feature(ENABLE_CMD):
            self.analog_enabled = True
            return True
        return False

    def _disable_analog(self):
        if self._send_feature(DISABLE_CMD):
            self.analog_enabled = False
            return True
        return False

    def _hid_handler(self, data):
        if 0x1B not in data:
            return
        idx = data.index(0x1B)
        if idx + 3 >= len(data):
            return

        analog_lo = data[idx+1]
        analog_hi = data[idx+2]
        key_id = data[idx+3]
        analog_value = analog_lo + analog_hi * 256

        with self.data_lock:
            self.latest_analog = analog_value
            if analog_value > 0:
                self.latest_key_id = key_id
                self.last_event_time = time.time()
                if analog_value > self.peak_analog:
                    self.peak_analog = analog_value

    def _update_loop(self):
        with self.data_lock:
            key_id = self.latest_key_id
            analog = self.latest_analog
            peak = self.peak_analog

        if analog > 0:
            bar_len = int(analog / 10)
            bar = '█' * min(bar_len, 40)
            self.analog_label.config(text=f"ID: {key_id}  Val: {analog:4d} {bar}")
        else:
            self.analog_label.config(text=f"Analog: idle")

        if self.is_mapping and self.current_key_index >= 0:
            now = time.time()
            if peak > 30 and analog == 0 and (now - self.last_event_time) > 0.15:
                self._assign_current_key(key_id)

        if self.free_mode and key_id is not None and analog > 30:
            found = [k for k, v in self.mapping.items() if v == key_id]
            if found:
                self.instr_label.config(text=f"Key ID {key_id} = {found[0]}  (analog: {analog})")
            else:
                self.instr_label.config(text=f"Key ID {key_id} = UNMAPPED  (analog: {analog})")

        mapped = len(self.mapping)
        total = len(ALL_KEYS)
        self.progress_label.config(text=f"{mapped}/{total} mapped")

        self.root.after(33, self._update_loop)

    def _start_mapping(self):
        if not self.analog_enabled:
            ok = self._enable_analog()
            if not ok:
                messagebox.showerror("Error", "Cannot enable analog mode!")
                return
        self.is_mapping = True
        self.free_mode = False
        self.current_key_index = 0
        self.start_btn.config(state=tk.DISABLED)
        self.skip_btn.config(state=tk.NORMAL)
        self.undo_btn.config(state=tk.NORMAL)
        self._advance_to_next_unmapped()
        self._highlight_current()

    def _advance_to_next_unmapped(self):
        while (self.current_key_index < len(ALL_KEYS) and ALL_KEYS[self.current_key_index] in self.mapping):
            self.current_key_index += 1

    def _highlight_current(self):
        for label, btn in self.key_buttons.items():
            if label in self.mapping:
                btn.config(bg=COLOR_KEY_MAPPED, fg=COLOR_SUCCESS)
            else:
                btn.config(bg=COLOR_KEY_IDLE, fg=COLOR_TEXT_DIM)

        if self.current_key_index >= len(ALL_KEYS):
            self._finish_mapping()
            return

        key = ALL_KEYS[self.current_key_index]
        self.key_buttons[key].config(bg=COLOR_KEY_ACTIVE, fg="white")
        self.instr_label.config(text=f"Press the key:  {key}  (then release)")
        with self.data_lock:
            self.peak_analog = 0
            self.latest_key_id = None

    def _assign_current_key(self, key_id):
        if self.current_key_index >= len(ALL_KEYS):
            return
        key_label = ALL_KEYS[self.current_key_index]
        existing = [k for k, v in self.mapping.items() if v == key_id]
        if existing:
            self.instr_label.config(text=f"Key ID {key_id} already used for {existing[0]}! Try again.", fg=COLOR_DANGER)
            with self.data_lock:
                self.peak_analog = 0
                self.latest_key_id = None
            self.root.after(1500, lambda: self.instr_label.config(fg=COLOR_TEXT_MAIN))
            return

        self.mapping[key_label] = key_id
        self.key_buttons[key_label].config(bg=COLOR_KEY_MAPPED, fg=COLOR_SUCCESS)
        self.current_key_index += 1
        self._advance_to_next_unmapped()
        self._highlight_current()

    def _skip_key(self):
        if self.current_key_index < len(ALL_KEYS):
            self.current_key_index += 1
            self._advance_to_next_unmapped()
            with self.data_lock:
                self.peak_analog = 0
                self.latest_key_id = None
            self._highlight_current()

    def _undo_key(self):
        if not self.mapping:
            return
        for i in range(self.current_key_index - 1, -1, -1):
            key = ALL_KEYS[i]
            if key in self.mapping:
                del self.mapping[key]
                self.current_key_index = i
                with self.data_lock:
                    self.peak_analog = 0
                    self.latest_key_id = None
                self._highlight_current()
                return

    def _manual_select(self, key_label):
        if not self.analog_enabled:
            return
        self.is_mapping = True
        self.free_mode = False
        idx = ALL_KEYS.index(key_label)
        self.current_key_index = idx
        if key_label in self.mapping:
            del self.mapping[key_label]
        self.skip_btn.config(state=tk.NORMAL)
        self.undo_btn.config(state=tk.NORMAL)
        self._highlight_current()

    def _toggle_freemode(self):
        if not self.analog_enabled:
            ok = self._enable_analog()
            if not ok:
                messagebox.showerror("Error", "Cannot enable analog mode!")
                return
        self.free_mode = not self.free_mode
        self.is_mapping = not self.free_mode

        if self.free_mode:
            self.freemode_btn.config(bg="#9944cc", text="EXIT FREE MODE")
            self.instr_label.config(text="FREE MODE: press any key to see its ID")
            self.start_btn.config(state=tk.NORMAL)
        else:
            self.freemode_btn.config(bg="#663399", text="FREE MODE")
            self.instr_label.config(text="Press START to continue mapping")
            self.start_btn.config(state=tk.NORMAL)

    def _finish_mapping(self):
        self.is_mapping = False
        self.skip_btn.config(state=tk.DISABLED)
        self.start_btn.config(state=tk.NORMAL, text="RESTART")
        self.instr_label.config(text=f"COMPLETED! {len(self.mapping)}/{len(ALL_KEYS)} keys mapped. Press SAVE.")

    def _save_config(self):
        config = {
            "device": {
                "name": "X68 HE",
                "vid": f"0x{VID:04X}",
                "pid": f"0x{PID:04X}",
                "vid_int": VID,
                "pid_int": PID,
            },
            "protocol": {
                "enable_cmd": ENABLE_CMD,
                "disable_cmd": DISABLE_CMD,
                "report_id": 5,
                "prefix": 0x1B,
                "analog_byte_lo": 2,
                "analog_byte_hi": 3,
                "key_id_byte": 4,
                "analog_max": 350,
                "note": "pywinusb byte indices (byte[0]=report_id)"
            },
            "key_mapping": self.mapping,
            "reverse_mapping": {v: k for k, v in self.mapping.items()},
            "unmapped_keys": [k for k in ALL_KEYS if k not in self.mapping],
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        path = os.path.join(os.path.dirname(__file__), "key_config.json")
        with open(path, 'w') as f:
            json.dump(config, f, indent=2)

        mapped = len(self.mapping)
        self.instr_label.config(text=f"Saved to key_config.json ({mapped} keys)")
        messagebox.showinfo("Saved", f"Config saved to:\n{path}\n\n{mapped} keys mapped.")

    def _load_existing(self):
        path = os.path.join(os.path.dirname(__file__), "key_config.json")
        if os.path.exists(path):
            try:
                with open(path) as f:
                    config = json.load(f)
                self.mapping = config.get("key_mapping", {})
                self.mapping = {k: int(v) for k, v in self.mapping.items()}
                for label in self.mapping:
                    if label in self.key_buttons:
                        self.key_buttons[label].config(bg=COLOR_KEY_MAPPED, fg=COLOR_SUCCESS)
                self.instr_label.config(text=f"Loaded existing mapping ({len(self.mapping)} keys). Press START to continue.")
            except Exception as e:
                pass

    def _on_close(self):
        if self.analog_enabled:
            self._disable_analog()
        for d in self.opened_devices:
            try:
                d.close()
            except:
                pass
        self.root.destroy()

def main():
    root = tk.Tk()
    root.update_idletasks()
    app = KeyMapperGUI(root)
    root.mainloop()

if __name__ == '__main__':
    main()