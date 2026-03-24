"""
X68 HE → Virtual Xbox 360 Gamepad
Reads analog key data and maps it to a virtual controller via ViGEmBus.
"""

import tkinter as tk
from tkinter import ttk
import vgamepad as vg
import pywinusb.hid as hid_pywin
import hid as hid_api
import ctypes
import threading
import time
import json
import os
import math

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "key_config.json")
GAMEPAD_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "gamepad_config.json")

VID = 0x3151
PID = 0x502D
ENABLE_CMD = [0x1B, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0xE3] + [0x00] * 56
DISABLE_CMD = [0x1B, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xE4] + [0x00] * 56

hid_dll = ctypes.WinDLL('hid.dll')
kernel32 = ctypes.WinDLL('kernel32.dll')

ANALOG_MAX = 350.0

MODE_HYBRID = "hybrid"
MODE_FULL = "full_controller"

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

DEFAULT_BINDINGS = {
    "left_stick_up": "W", "left_stick_down": "S", "left_stick_left": "A", "left_stick_right": "D",
    "right_stick_up": "I", "right_stick_down": "K", "right_stick_left": "J", "right_stick_right": "L",
    "btn_a": "SPACE", "btn_b": "LSHIFT", "btn_x": "E", "btn_y": "Q",
    "left_bumper": "TAB", "right_bumper": "R", "left_trigger": "LCTRL", "right_trigger": "F",
    "dpad_up": "UP", "dpad_down": "DOWN", "dpad_left": "LEFT", "dpad_right": "RIGHT",
    "btn_start": "ENTER", "btn_back": "ESC", "btn_thumb_left": "C", "btn_thumb_right": "V",
}

DEFAULT_SETTINGS = {
    "mode": MODE_HYBRID, "deadzone": 0.05, "smoothing": 0.3, "sensitivity_curve": 1.0,
    "trigger_threshold": 0.15, "button_threshold": 0.15, "analog_max_override": 350,
}

class KeyboardState:
    def __init__(self, key_mapping):
        self.key_mapping = key_mapping
        self.id_to_key = {v: k for k, v in key_mapping.items()}
        self.values = {}
        self.lock = threading.Lock()

    def update(self, key_id, analog_value):
        key_label = self.id_to_key.get(key_id)
        if key_label:
            with self.lock:
                self.values[key_label] = analog_value

    def get(self, key_label):
        with self.lock:
            return self.values.get(key_label, 0)

    def get_normalized(self, key_label, settings):
        raw = self.get(key_label)
        max_val = settings.get("analog_max_override", ANALOG_MAX)
        normalized = min(1.0, raw / max_val) if max_val > 0 else 0.0

        dz = settings.get("deadzone", 0.05)
        if normalized < dz:
            return 0.0
        normalized = (normalized - dz) / (1.0 - dz)

        curve = settings.get("sensitivity_curve", 1.0)
        if curve != 1.0:
            normalized = math.pow(normalized, curve)

        return min(1.0, max(0.0, normalized))

class SmoothedAxis:
    def __init__(self):
        self.value = 0.0

    def update(self, target, smoothing):
        if smoothing <= 0:
            self.value = target
        else:
            self.value += (target - self.value) * (1.0 - smoothing)
        return self.value

class VirtualGamepad:
    def __init__(self):
        self.pad = vg.VX360Gamepad()
        self.lx = SmoothedAxis()
        self.ly = SmoothedAxis()
        self.rx = SmoothedAxis()
        self.ry = SmoothedAxis()
        self.lt = SmoothedAxis()
        self.rt = SmoothedAxis()

    def update(self, kb_state, bindings, settings):
        smoothing = settings.get("smoothing", 0.3)
        mode = settings.get("mode", MODE_HYBRID)

        up = kb_state.get_normalized(bindings.get("left_stick_up", ""), settings)
        down = kb_state.get_normalized(bindings.get("left_stick_down", ""), settings)
        left = kb_state.get_normalized(bindings.get("left_stick_left", ""), settings)
        right = kb_state.get_normalized(bindings.get("left_stick_right", ""), settings)

        raw_lx = right - left
        raw_ly = up - down

        mag = math.sqrt(raw_lx ** 2 + raw_ly ** 2)
        if mag > 1.0:
            raw_lx /= mag
            raw_ly /= mag

        lx_val = self.lx.update(raw_lx, smoothing)
        ly_val = self.ly.update(raw_ly, smoothing)

        self.pad.left_joystick_float(x_value_float=lx_val, y_value_float=ly_val)

        rx_val = ry_val = lt_val = rt_val = 0.0

        if mode == MODE_FULL:
            btn_thresh = settings.get("button_threshold", 0.15)

            r_up = kb_state.get_normalized(bindings.get("right_stick_up", ""), settings)
            r_down = kb_state.get_normalized(bindings.get("right_stick_down", ""), settings)
            r_left = kb_state.get_normalized(bindings.get("right_stick_left", ""), settings)
            r_right = kb_state.get_normalized(bindings.get("right_stick_right", ""), settings)

            raw_rx = r_right - r_left
            raw_ry = r_up - r_down
            mag = math.sqrt(raw_rx ** 2 + raw_ry ** 2)
            if mag > 1.0:
                raw_rx /= mag
                raw_ry /= mag

            rx_val = self.rx.update(raw_rx, smoothing)
            ry_val = self.ry.update(raw_ry, smoothing)
            self.pad.right_joystick_float(x_value_float=rx_val, y_value_float=ry_val)

            lt_raw = kb_state.get_normalized(bindings.get("left_trigger", ""), settings)
            rt_raw = kb_state.get_normalized(bindings.get("right_trigger", ""), settings)
            lt_val = self.lt.update(lt_raw, smoothing)
            rt_val = self.rt.update(rt_raw, smoothing)
            self.pad.left_trigger_float(value_float=lt_val)
            self.pad.right_trigger_float(value_float=rt_val)

            button_map = {
                "btn_a": vg.XUSB_BUTTON.XUSB_GAMEPAD_A, "btn_b": vg.XUSB_BUTTON.XUSB_GAMEPAD_B,
                "btn_x": vg.XUSB_BUTTON.XUSB_GAMEPAD_X, "btn_y": vg.XUSB_BUTTON.XUSB_GAMEPAD_Y,
                "left_bumper": vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER, "right_bumper": vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER,
                "btn_start": vg.XUSB_BUTTON.XUSB_GAMEPAD_START, "btn_back": vg.XUSB_BUTTON.XUSB_GAMEPAD_BACK,
                "btn_thumb_left": vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_THUMB, "btn_thumb_right": vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_THUMB,
            }

            for action, xbutton in button_map.items():
                key_label = bindings.get(action, "")
                val = kb_state.get_normalized(key_label, settings)
                if val > btn_thresh:
                    self.pad.press_button(button=xbutton)
                else:
                    self.pad.release_button(button=xbutton)

            dpad_up = kb_state.get_normalized(bindings.get("dpad_up", ""), settings) > btn_thresh
            dpad_down = kb_state.get_normalized(bindings.get("dpad_down", ""), settings) > btn_thresh
            dpad_left = kb_state.get_normalized(bindings.get("dpad_left", ""), settings) > btn_thresh
            dpad_right = kb_state.get_normalized(bindings.get("dpad_right", ""), settings) > btn_thresh

            if dpad_up and dpad_right:
                self.pad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_UP)
                self.pad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_RIGHT)
            elif dpad_up and dpad_left:
                self.pad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_UP)
                self.pad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_LEFT)
            elif dpad_down and dpad_right:
                self.pad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN)
                self.pad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_RIGHT)
            elif dpad_down and dpad_left:
                self.pad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN)
                self.pad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_LEFT)
            elif dpad_up:
                self.pad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_UP)
            elif dpad_down:
                self.pad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN)
            elif dpad_left:
                self.pad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_LEFT)
            elif dpad_right:
                self.pad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_RIGHT)
            else:
                for dp in [vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_UP, vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN,
                           vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_LEFT, vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_RIGHT]:
                    self.pad.release_button(button=dp)

        self.pad.update()
        return lx_val, ly_val, rx_val, ry_val, lt_val, rt_val

class GamepadApp:
    def __init__(self, root):
        self.root = root
        self.root.title("X68 HE → Xbox 360 Gamepad")
        self.root.geometry("900x750")
        self.root.configure(bg=COLOR_BG_MAIN)
        self.root.resizable(True, True)

        # Style configuration
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        self.style.configure("TFrame", background=COLOR_BG_MAIN)
        self.style.configure("TLabel", background=COLOR_BG_MAIN, foreground=COLOR_TEXT_MAIN, font=("Segoe UI", 10))
        self.style.configure("TScale", background=COLOR_BG_FRAME, troughcolor=COLOR_BG_INPUT, sliderlength=20)
        self.style.configure("TCombobox", fieldbackground=COLOR_BG_INPUT, background=COLOR_BTN_NORMAL, foreground=COLOR_TEXT_MAIN)
        self.style.map("TCombobox", fieldbackground=[('readonly', COLOR_BG_INPUT)], background=[('readonly', COLOR_BTN_NORMAL)])

        self.running = True
        self.active = False

        self.key_mapping = self._load_key_config()
        self.bindings, self.settings = self._load_gamepad_config()

        self.kb_state = KeyboardState(self.key_mapping)
        self.gamepad = None
        self.opened_devices = []
        self.config_path = None

        self.lx_display = 0.0
        self.ly_display = 0.0
        self.rx_display = 0.0
        self.ry_display = 0.0
        self.lt_display = 0.0
        self.rt_display = 0.0

        self._build_ui()
        self._init_hid()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._gamepad_loop()
        self._ui_update_loop()

    def _load_key_config(self):
        if not os.path.exists(CONFIG_PATH): return {}
        with open(CONFIG_PATH) as f:
            cfg = json.load(f)
        mapping = cfg.get("key_mapping", {})
        return {k: int(v) for k, v in mapping.items()}

    def _load_gamepad_config(self):
        if os.path.exists(GAMEPAD_CONFIG_PATH):
            with open(GAMEPAD_CONFIG_PATH) as f:
                cfg = json.load(f)
            bindings = cfg.get("bindings", DEFAULT_BINDINGS)
            settings = {**DEFAULT_SETTINGS, **cfg.get("settings", {})}
        else:
            bindings = dict(DEFAULT_BINDINGS)
            settings = dict(DEFAULT_SETTINGS)
        return bindings, settings

    def _save_gamepad_config(self):
        self.settings["mode"] = self.mode_var.get()
        cfg = {"bindings": self.bindings, "settings": self.settings}
        with open(GAMEPAD_CONFIG_PATH, 'w') as f:
            json.dump(cfg, f, indent=2)

    def _build_ui(self):
        self.root.bind_all('<space>', lambda e: 'break')
        self.root.bind_all('<Return>', lambda e: 'break')

        # Top Header
        header = tk.Frame(self.root, bg=COLOR_BG_FRAME)
        header.pack(fill=tk.X, padx=0, pady=0)
        
        inner_header = tk.Frame(header, bg=COLOR_BG_FRAME)
        inner_header.pack(fill=tk.X, padx=20, pady=15)

        self.status_label = tk.Label(inner_header, text="● DISCONNECTED", font=("Segoe UI", 14, "bold"), fg=COLOR_DANGER, bg=COLOR_BG_FRAME)
        self.status_label.pack(side=tk.LEFT, padx=5)

        # Top Controls
        ctrl_frame = tk.Frame(inner_header, bg=COLOR_BG_FRAME)
        ctrl_frame.pack(side=tk.RIGHT)

        self.toggle_btn = tk.Button(ctrl_frame, text="ACTIVATE", font=("Segoe UI", 10, "bold"), 
                                    bg="#00aa55", fg="white", relief=tk.FLAT, padx=20, pady=8, command=self._toggle_active)
        self.toggle_btn.pack(side=tk.RIGHT, padx=10)
        self._add_hover(self.toggle_btn, "#00cc66", "#00aa55")

        mode_frame = tk.Frame(ctrl_frame, bg=COLOR_BG_FRAME)
        mode_frame.pack(side=tk.RIGHT, padx=10)
        tk.Label(mode_frame, text="Mode:", font=("Segoe UI", 10), fg=COLOR_TEXT_DIM, bg=COLOR_BG_FRAME).pack(side=tk.LEFT, padx=(0,5))
        
        self.mode_var = tk.StringVar(value=self.settings.get("mode", MODE_HYBRID))
        self.mode_combo = ttk.Combobox(mode_frame, textvariable=self.mode_var, values=[MODE_HYBRID, MODE_FULL], width=18, font=("Segoe UI", 10), state="readonly")
        self.mode_combo.pack(side=tk.LEFT)
        self.mode_combo.bind("<<ComboboxSelected>>", self._on_mode_change)

        # Main Content
        main = tk.Frame(self.root, bg=COLOR_BG_MAIN)
        main.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # Visualization Panel (Left)
        self.viz_frame = tk.Frame(main, bg=COLOR_BG_FRAME, highlightbackground=COLOR_ACCENT, highlightthickness=1)
        self.viz_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        viz_header = tk.Label(self.viz_frame, text=" CONTROLLER STATE ", font=("Segoe UI", 10, "bold"), fg=COLOR_HIGHLIGHT, bg=COLOR_BG_FRAME, anchor=tk.W)
        viz_header.pack(fill=tk.X, padx=15, pady=(15, 5))

        self.sticks_frame = tk.Frame(self.viz_frame, bg=COLOR_BG_FRAME)
        self.sticks_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)

        # Left Stick Canvas
        ls_frame = tk.Frame(self.sticks_frame, bg=COLOR_BG_FRAME)
        ls_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tk.Label(ls_frame, text="LEFT STICK", font=("Segoe UI", 9, "bold"), fg=COLOR_TEXT_DIM, bg=COLOR_BG_FRAME).pack()
        self.left_canvas = tk.Canvas(ls_frame, bg=COLOR_BG_INPUT, width=180, height=180, highlightthickness=0)
        self.left_canvas.pack(padx=5, pady=5)
        self.ls_label = tk.Label(ls_frame, text="X: 0.00  Y: 0.00", font=("Consolas", 10), fg=COLOR_SUCCESS, bg=COLOR_BG_FRAME)
        self.ls_label.pack()

        # Right Stick Canvas
        self.rs_frame = tk.Frame(self.sticks_frame, bg=COLOR_BG_FRAME)
        tk.Label(self.rs_frame, text="RIGHT STICK", font=("Segoe UI", 9, "bold"), fg=COLOR_TEXT_DIM, bg=COLOR_BG_FRAME).pack()
        self.right_canvas = tk.Canvas(self.rs_frame, bg=COLOR_BG_INPUT, width=180, height=180, highlightthickness=0)
        self.right_canvas.pack(padx=5, pady=5)
        self.rs_label = tk.Label(self.rs_frame, text="X: 0.00  Y: 0.00", font=("Consolas", 10), fg=COLOR_SUCCESS, bg=COLOR_BG_FRAME)
        self.rs_label.pack()

        # Triggers & Buttons
        self.trig_frame = tk.Frame(self.viz_frame, bg=COLOR_BG_FRAME)
        
        tk.Label(self.trig_frame, text="LT", font=("Segoe UI", 9, "bold"), fg=COLOR_TEXT_DIM, bg=COLOR_BG_FRAME).pack(side=tk.LEFT)
        self.lt_bar = tk.Canvas(self.trig_frame, bg=COLOR_BG_INPUT, height=25, highlightthickness=0)
        self.lt_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)
        
        self.rt_bar = tk.Canvas(self.trig_frame, bg=COLOR_BG_INPUT, height=25, highlightthickness=0)
        self.rt_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)
        tk.Label(self.trig_frame, text="RT", font=("Segoe UI", 9, "bold"), fg=COLOR_TEXT_DIM, bg=COLOR_BG_FRAME).pack(side=tk.LEFT)

        self.btn_label = tk.Label(self.viz_frame, text="Buttons: ---", font=("Consolas", 10), fg=COLOR_WARNING, bg=COLOR_BG_FRAME, anchor=tk.W)
        self.btn_label.pack(fill=tk.X, padx=15, pady=5)

        self.raw_label = tk.Label(self.viz_frame, text="Raw Input: ---", font=("Consolas", 9), fg=COLOR_TEXT_DIM, bg=COLOR_BG_FRAME, anchor=tk.W)
        self.raw_label.pack(fill=tk.X, padx=15, pady=(0, 15))

        # --- REORGANIZED SETTINGS PANEL (Right) ---
        self.settings_frame = tk.Frame(main, bg=COLOR_BG_FRAME, highlightbackground=COLOR_ACCENT, highlightthickness=1, width=320)
        self.settings_frame.pack(side=tk.RIGHT, fill=tk.Y)
        self.settings_frame.pack_propagate(False)

        set_header = tk.Label(self.settings_frame, text=" SETTINGS ", font=("Segoe UI", 10, "bold"), fg=COLOR_HIGHLIGHT, bg=COLOR_BG_FRAME, anchor=tk.W)
        set_header.pack(fill=tk.X, padx=15, pady=(15, 5))

        # Sliders Container
        self.sliders_container = tk.Frame(self.settings_frame, bg=COLOR_BG_FRAME)
        self.sliders_container.pack(fill=tk.X, padx=15, pady=5)

        self.sliders = {}
        self.slider_widgets = {} # Store widgets to show/hide later
        
        # Definitions: key, label, min, max, default, show_in_hybrid
        self.slider_defs = [
            ("deadzone", "Deadzone", 0, 0.5, self.settings["deadzone"], True),
            ("smoothing", "Smoothing", 0, 0.95, self.settings["smoothing"], True),
            ("sensitivity_curve", "Sensitivity", 0.2, 3.0, self.settings["sensitivity_curve"], True),
            ("analog_max_override", "Analog Max", 100, 730, self.settings["analog_max_override"], True),
            ("button_threshold", "Btn Threshold", 0.01, 0.5, self.settings["button_threshold"], False),
            ("trigger_threshold", "Trig Threshold", 0.01, 0.5, self.settings["trigger_threshold"], False),
        ]

        for key, label, min_v, max_v, default, show_hybrid in self.slider_defs:
            f = tk.Frame(self.sliders_container, bg=COLOR_BG_FRAME)
            f.pack(fill=tk.X, pady=2)
            
            # Row 1: Label and Entry
            top_row = tk.Frame(f, bg=COLOR_BG_FRAME)
            top_row.pack(fill=tk.X)
            
            tk.Label(top_row, text=f"{label}:", font=("Segoe UI", 9), fg=COLOR_TEXT_MAIN, bg=COLOR_BG_FRAME).pack(side=tk.LEFT)
            
            # Custom Entry for value
            val_entry = tk.Entry(top_row, width=8, font=("Consolas", 9), bg=COLOR_BG_INPUT, fg=COLOR_TEXT_MAIN, 
                                 insertbackground=COLOR_TEXT_MAIN, relief=tk.FLAT, borderwidth=0, highlightthickness=1, 
                                 highlightbackground=COLOR_ACCENT, highlightcolor=COLOR_HIGHLIGHT)
            val_entry.pack(side=tk.RIGHT, padx=2)
            val_entry.insert(0, f"{default:.2f}")
            
            # Bind Entry to update settings
            val_entry.bind("<Return>", lambda e, k=key, v_entry=val_entry, s_min=min_v, s_max=max_v: self._on_entry_change(k, v_entry, s_min, s_max))
            val_entry.bind("<FocusOut>", lambda e, k=key, v_entry=val_entry, s_min=min_v, s_max=max_v: self._on_entry_change(k, v_entry, s_min, s_max))

            # Row 2: Slider
            slider = ttk.Scale(f, from_=min_v, to=max_v, value=default, orient=tk.HORIZONTAL, 
                               command=lambda v, k=key, v_entry=val_entry: self._on_slider(k, v, v_entry))
            slider.pack(fill=tk.X, pady=(2, 0))
            
            self.sliders[key] = slider
            self.slider_widgets[key] = {'frame': f, 'entry': val_entry, 'show_hybrid': show_hybrid}

        # Bindings Section
        bind_header = tk.Label(self.settings_frame, text=" KEY BINDINGS ", font=("Segoe UI", 10, "bold"), fg=COLOR_HIGHLIGHT, bg=COLOR_BG_FRAME, anchor=tk.W)
        bind_header.pack(fill=tk.X, padx=15, pady=(15, 5))

        self.bind_container = tk.Frame(self.settings_frame, bg=COLOR_BG_FRAME)
        self.bind_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 5))

        bind_canvas = tk.Canvas(self.bind_container, bg=COLOR_BG_FRAME, highlightthickness=0)
        bind_scroll = ttk.Scrollbar(self.bind_container, orient=tk.VERTICAL, command=bind_canvas.yview)
        bind_inner = tk.Frame(bind_canvas, bg=COLOR_BG_FRAME)

        bind_inner.bind("<Configure>", lambda e: bind_canvas.configure(scrollregion=bind_canvas.bbox("all")))
        bind_canvas.create_window((0, 0), window=bind_inner, anchor=tk.NW)
        bind_canvas.configure(yscrollcommand=bind_scroll.set)

        bind_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        bind_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.bind_vars = {}
        self.bind_rows = {} # Stores frame reference for show/hide
        all_keys = sorted(self.key_mapping.keys()) if self.key_mapping else ["(No Config)"]

        HYBRID_BINDINGS = {"left_stick_up", "left_stick_down", "left_stick_left", "left_stick_right"}

        for action in sorted(self.bindings.keys()):
            f = tk.Frame(bind_inner, bg=COLOR_BG_FRAME)
            f.pack(fill=tk.X, pady=1, padx=5)
            
            short = action.replace("left_stick_", "LS_").replace("right_stick_", "RS_").replace("btn_", "").replace("thumb_", "Th")
            
            tk.Label(f, text=f"{short}:", font=("Consolas", 9), fg=COLOR_TEXT_DIM, bg=COLOR_BG_FRAME, width=12, anchor=tk.E).pack(side=tk.LEFT)
            
            var = tk.StringVar(value=self.bindings[action])
            combo = ttk.Combobox(f, textvariable=var, values=all_keys, width=8, font=("Consolas", 9), state="readonly")
            combo.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
            combo.bind("<<ComboboxSelected>>", lambda e, a=action, v=var: self._on_binding_change(a, v))
            
            self.bind_vars[action] = var
            self.bind_rows[action] = (f, action in HYBRID_BINDINGS)

        save_btn = tk.Button(self.settings_frame, text="SAVE CONFIG", font=("Segoe UI", 10, "bold"), bg="#2266cc", fg="white", relief=tk.FLAT, command=self._save_gamepad_config)
        save_btn.pack(fill=tk.X, padx=15, pady=15, ipady=5)
        self._add_hover(save_btn, "#3377dd", "#2266cc")

        self.mode_desc = tk.Label(self.root, text="", font=("Segoe UI", 9), fg=COLOR_TEXT_DIM, bg=COLOR_BG_MAIN, anchor=tk.W)
        self.mode_desc.pack(fill=tk.X, padx=20, pady=(0, 10))
        
        self._update_mode_ui()

    def _add_hover(self, widget, enter_color, leave_color):
        widget.bind("<Enter>", lambda e: widget.config(bg=enter_color))
        widget.bind("<Leave>", lambda e: widget.config(bg=leave_color))

    def _on_slider(self, key, value, entry_widget):
        v = float(value)
        self.settings[key] = v
        # Update entry without triggering its callback
        entry_widget.delete(0, tk.END)
        entry_widget.insert(0, f"{v:.2f}")

    def _on_entry_change(self, key, entry_widget, slider_min, slider_max):
        try:
            val = float(entry_widget.get())
            # Update settings
            self.settings[key] = val
            
            # Update slider if value is within range, otherwise clamp visually
            # We don't clamp the actual setting (val), only the slider position
            slider_val = max(slider_min, min(slider_max, val))
            
            # Avoid update loop
            if abs(self.sliders[key].get() - slider_val) > 0.001:
                self.sliders[key].set(slider_val)
            
            # Clean up entry text
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, f"{val:.2f}")
            
        except ValueError:
            # Restore previous valid value if input is garbage
            current_val = self.settings.get(key, 0)
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, f"{current_val:.2f}")

    def _on_mode_change(self, event=None):
        self.settings["mode"] = self.mode_var.get()
        self._update_mode_ui()

    def _update_mode_ui(self):
        mode = self.settings.get("mode", MODE_HYBRID)
        is_hybrid = (mode == MODE_HYBRID)

        if is_hybrid:
            self.mode_desc.config(text="Mode: HYBRID (Left stick only. Keyboard passthrough active).", fg=COLOR_SUCCESS)
        else:
            self.mode_desc.config(text="Mode: FULL CONTROLLER (All inputs mapped).", fg=COLOR_WARNING)

        # --- Visibility Logic ---
        
        # 1. Visuals (Left side)
        if is_hybrid:
            self.rs_frame.pack_forget()
            self.trig_frame.pack_forget()
            self.btn_label.pack_forget()
        else:
            self.rs_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, in_=self.sticks_frame)
            self.btn_label.pack(fill=tk.X, padx=15, pady=5, in_=self.viz_frame, before=self.raw_label)
            self.trig_frame.pack(fill=tk.X, padx=15, pady=5, in_=self.viz_frame, before=self.btn_label)

        # 2. Sliders (Right side)
        for key, data in self.slider_widgets.items():
            frame = data['frame']
            show_hybrid = data['show_hybrid']
            
            if is_hybrid:
                if show_hybrid:
                    frame.pack(fill=tk.X, pady=2)
                else:
                    frame.pack_forget()
            else:
                frame.pack(fill=tk.X, pady=2)

        # 3. Bindings (Right side)
        for action, (frame, show_hybrid) in self.bind_rows.items():
            if is_hybrid:
                if show_hybrid:
                    frame.pack(fill=tk.X, pady=1, padx=5)
                else:
                    frame.pack_forget()
            else:
                frame.pack(fill=tk.X, pady=1, padx=5)

    def _on_binding_change(self, action, var):
        self.bindings[action] = var.get()

    def _init_hid(self):
        raw_devices = hid_api.enumerate(VID, PID)
        self.config_path = None
        for d in raw_devices:
            path = d['path']
            if isinstance(path, bytes):
                path = path.decode('utf-8')
            
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
        buf[0] = 0 
        for i in range(64):
            if i < len(cmd):
                buf[i + 1] = cmd[i]
            else:
                buf[i + 1] = 0
                
        r = hid_dll.HidD_SetFeature(h, ctypes.byref(buf), 65)
        kernel32.CloseHandle(h)
        return bool(r)

    def _hid_handler(self, data):
        if 0x1B not in data:
            return
        idx = data.index(0x1B)
        if idx + 3 >= len(data):
            return

        analog = data[idx+1] + data[idx+2] * 256
        key_id = data[idx+3]
        self.kb_state.update(key_id, analog)

    def _toggle_active(self):
        if self.active:
            self._deactivate()
        else:
            self._activate()

    def _activate(self):
        if not self._send_feature(ENABLE_CMD):
            self.status_label.config(text="● ENABLE FAILED", fg=COLOR_DANGER)
            return
        try:
            self.gamepad = VirtualGamepad()
        except Exception as e:
            self.status_label.config(text=f"● ViGEm ERROR: {e}", fg=COLOR_DANGER)
            return
        self.active = True
        self.status_label.config(text="● GAMEPAD ACTIVE", fg=COLOR_SUCCESS)
        self.toggle_btn.config(text="DEACTIVATE", bg="#cc2222")
        self._add_hover(self.toggle_btn, "#ee3333", "#cc2222")

    def _deactivate(self):
        self.active = False
        self._send_feature(DISABLE_CMD)
        if self.gamepad:
            self.gamepad.pad.reset()
            self.gamepad.pad.update()
            del self.gamepad.pad
            self.gamepad = None
        self.status_label.config(text="● GAMEPAD OFF", fg=COLOR_WARNING)
        self.toggle_btn.config(text="ACTIVATE", bg="#00aa55")
        self._add_hover(self.toggle_btn, "#00cc66", "#00aa55")

    def _gamepad_loop(self):
        if self.active and self.gamepad:
            vals = self.gamepad.update(self.kb_state, self.bindings, self.settings)
            self.lx_display, self.ly_display = vals[0], vals[1]
            self.rx_display, self.ry_display = vals[2], vals[3]
            self.lt_display, self.rt_display = vals[4], vals[5]
        self.root.after(8, self._gamepad_loop)

    def _ui_update_loop(self):
        if not self.running:
            return
        mode = self.settings.get("mode", MODE_HYBRID)
        self._draw_stick(self.left_canvas, self.lx_display, self.ly_display)
        self.ls_label.config(text=f"X:{self.lx_display:+.2f}  Y:{self.ly_display:+.2f}")

        if mode == MODE_FULL:
            self._draw_stick(self.right_canvas, self.rx_display, self.ry_display)
            self._draw_trigger(self.lt_bar, self.lt_display)
            self._draw_trigger(self.rt_bar, self.rt_display)
            self.rs_label.config(text=f"X:{self.rx_display:+.2f}  Y:{self.ry_display:+.2f}")
            thresh = self.settings.get("button_threshold", 0.15)
            active_btns = []
            for action in ["btn_a", "btn_b", "btn_x", "btn_y", "left_bumper", "right_bumper",
                           "btn_start", "btn_back", "btn_thumb_left", "btn_thumb_right"]:
                key = self.bindings.get(action, "")
                if self.kb_state.get_normalized(key, self.settings) > thresh:
                    short = action.replace("btn_", "").replace("left_", "L").replace("right_", "R").upper()
                    active_btns.append(short)
            self.btn_label.config(text=f"Buttons: {' '.join(active_btns) if active_btns else '---'}")

        w = self.kb_state.get(self.bindings.get("left_stick_up", ""))
        a = self.kb_state.get(self.bindings.get("left_stick_left", ""))
        s = self.kb_state.get(self.bindings.get("left_stick_down", ""))
        d = self.kb_state.get(self.bindings.get("left_stick_right", ""))
        self.raw_label.config(text=f"Raw: W={w:3d} A={a:3d} S={s:3d} D={d:3d}")
        self.root.after(33, self._ui_update_loop)

    def _draw_stick(self, canvas, x, y):
        canvas.delete("all")
        w = canvas.winfo_width()
        h = canvas.winfo_height()
        if w < 10: return
        cx, cy = w / 2, h / 2
        r = min(cx, cy) - 15
        
        canvas.create_rectangle(0, 0, w, h, fill=COLOR_BG_INPUT, outline="")
        canvas.create_oval(cx - r, cy - r, cx + r, cy + r, outline="#333355", width=2)
        canvas.create_line(cx - r, cy, cx + r, cy, fill="#222244", width=1)
        canvas.create_line(cx, cy - r, cx, cy + r, fill="#222244", width=1)
        
        dz = self.settings.get("deadzone", 0.05)
        dz_r = r * dz
        canvas.create_oval(cx - dz_r, cy - dz_r, cx + dz_r, cy + dz_r, outline="#442222", width=1, dash=(3, 3))
        
        dx = cx + x * r
        dy = cy - y * r
        
        mag = math.sqrt(x ** 2 + y ** 2)
        if mag > 0.01:
            intensity = min(255, int(mag * 255))
            color = f'#{intensity:02X}{max(0, 255 - intensity):02X}00'
            canvas.create_oval(dx - 12, dy - 12, dx + 12, dy + 12, fill="", outline=color, width=3)
        
        canvas.create_oval(dx - 6, dy - 6, dx + 6, dy + 6, fill=COLOR_SUCCESS, outline="white", width=2)

    def _draw_trigger(self, canvas, value):
        canvas.delete("all")
        w = canvas.winfo_width()
        h = canvas.winfo_height()
        if w < 10: return
        bar_w = int(value * w)
        intensity = min(255, int(value * 255))
        color = f'#{intensity:02X}{max(0, 200 - intensity):02X}00'
        
        canvas.create_rectangle(0, 0, w, h, fill=COLOR_BG_INPUT, outline="")
        if bar_w > 0:
            canvas.create_rectangle(0, 0, bar_w, h, fill=color, outline="")

    def _on_close(self):
        self.running = False
        if self.active:
            self._deactivate()
        for d in self.opened_devices:
            try:
                d.close()
            except:
                pass
        self.root.destroy()

def main():
    root = tk.Tk()
    app = GamepadApp(root)
    root.mainloop()

if __name__ == '__main__':
    main()