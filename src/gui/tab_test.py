import threading
import time as time_module
import tkinter as tk
from tkinter import ttk

import pavlok_controller as stimulus_controller
import config


class TestTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.grab_state = None
        self.test_stretch_var = tk.DoubleVar(value=0.0)
        self._ble_counter = 0
        self._create_unit_test_panel()
        self._create_ble_raw_panel()
        self._create_grab_sim_panel()

    def set_grab_state(self, grab_state):
        self.grab_state = grab_state

    # ------------------------------------------------------------------ #
    # 単体テストセクション                                                 #
    # ------------------------------------------------------------------ #

    def _create_unit_test_panel(self):
        frame = ttk.LabelFrame(self, text="単体テスト（Grab なし）", padding=10)
        frame.pack(fill="x", padx=10, pady=(10, 5))

        vib_frame = ttk.Frame(frame)
        vib_frame.pack(fill="x", pady=4)
        ttk.Label(vib_frame, text="Vibration:", width=15).pack(side="left")
        ttk.Button(vib_frame, text="弱", width=8,
                   command=lambda: self._send_vibration("weak")).pack(side="left", padx=2)
        ttk.Button(vib_frame, text="中", width=8,
                   command=lambda: self._send_vibration("mid")).pack(side="left", padx=2)
        ttk.Button(vib_frame, text="強", width=8,
                   command=lambda: self._send_vibration("strong")).pack(side="left", padx=2)

        zap_frame = ttk.Frame(frame)
        zap_frame.pack(fill="x", pady=4)
        ttk.Label(zap_frame, text="Zap:", width=15).pack(side="left")
        ttk.Button(zap_frame, text="弱", width=8,
                   command=lambda: self._send_zap("weak")).pack(side="left", padx=2)
        ttk.Button(zap_frame, text="中", width=8,
                   command=lambda: self._send_zap("mid")).pack(side="left", padx=2)
        ttk.Button(zap_frame, text="強", width=8,
                   command=lambda: self._send_zap("strong")).pack(side="left", padx=2)

    def _resolve_intensity(self, level: str) -> int:
        mn = config.MIN_STIMULUS_VALUE
        mx = config.MAX_STIMULUS_VALUE
        if level == "weak":
            return mn
        if level == "strong":
            return mx
        return (mn + mx) // 2  # mid

    def _send_vibration(self, level: str):
        intensity = self._resolve_intensity(level)
        threading.Thread(
            target=stimulus_controller.send_vibration,
            args=(intensity,),
            daemon=True,
        ).start()
        print(f"[Unit Test] Vibration {level} ({intensity})")

    def _send_zap(self, level: str):
        intensity = self._resolve_intensity(level)
        threading.Thread(
            target=stimulus_controller.send_zap,
            args=(intensity,),
            daemon=True,
        ).start()
        print(f"[Unit Test] Zap {level} ({intensity})")

    # ------------------------------------------------------------------ #
    # BLE 生コマンド テストセクション                                     #
    # ------------------------------------------------------------------ #

    def _create_ble_raw_panel(self):
        frame = ttk.LabelFrame(self, text="BLE 生コマンド（Vibration）", padding=10)
        frame.pack(fill="x", padx=10, pady=(5, 5))

        # パラメータ説明ラベル
        ttk.Label(frame, text="コマンド: [0x80|counter, mode, intensity, ton, toff]",
                  foreground="gray").pack(anchor="w", pady=(0, 6))

        grid = ttk.Frame(frame)
        grid.pack(fill="x")

        fields = [
            ("counter",   "カウンタ (0-127)",    0,   0, 127),
            ("mode",      "モード",              2,   0, 255),
            ("intensity", "強度 (0-100)",        50,  0, 100),
            ("ton",       "ton",                22,  0, 255),
            ("toff",      "toff",               22,  0, 255),
        ]

        self._raw_vars = {}
        for row, (key, label, default, mn, mx) in enumerate(fields):
            ttk.Label(grid, text=label, width=20).grid(row=row, column=0, sticky="w", pady=3)
            var = tk.IntVar(value=default)
            sb = ttk.Spinbox(grid, from_=mn, to=mx, textvariable=var, width=8)
            sb.grid(row=row, column=1, sticky="w", padx=5, pady=3)
            self._raw_vars[key] = var

        # カウンタ自動インクリメント
        auto_frame = ttk.Frame(frame)
        auto_frame.pack(fill="x", pady=(6, 2))
        self._auto_counter_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(auto_frame, text="送信ごとにカウンタを自動インクリメント",
                        variable=self._auto_counter_var).pack(side="left")

        # 送信ボタン & 結果表示
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill="x", pady=(4, 0))
        ttk.Button(btn_frame, text="送信", width=10, command=self._send_raw_vibe).pack(side="left", padx=2)
        self._raw_result_label = ttk.Label(btn_frame, text="", foreground="gray")
        self._raw_result_label.pack(side="left", padx=8)

    def _send_raw_vibe(self):
        counter   = self._raw_vars["counter"].get() & 0x7F
        mode      = self._raw_vars["mode"].get()
        intensity = self._raw_vars["intensity"].get()
        ton       = self._raw_vars["ton"].get()
        toff      = self._raw_vars["toff"].get()

        cmd = bytes([0x80 | counter, mode, intensity, ton, toff])
        label_text = f"送信: {list(cmd)}"
        self._raw_result_label.config(text=label_text)
        print(f"[BLE Raw] {label_text}")

        if self._auto_counter_var.get():
            next_counter = (counter + 1) & 0x7F
            self._raw_vars["counter"].set(next_counter)

        def _send():
            try:
                ok = stimulus_controller.send_raw_vibe(cmd)
                result = "OK" if ok else "FAILED"
            except Exception as e:
                result = f"ERROR: {e}"
            print(f"[BLE Raw] result={result}")
            self._raw_result_label.config(text=f"{label_text}  →  {result}")

        threading.Thread(target=_send, daemon=True).start()

    # ------------------------------------------------------------------ #
    # Grab シミュレーションセクション（tab_dashboard.py から移動）        #
    # ------------------------------------------------------------------ #

    def _create_grab_sim_panel(self):
        frame = ttk.LabelFrame(self, text="Grab シミュレーション", padding=10)
        frame.pack(fill="x", padx=10, pady=(5, 10))

        grab_frame = ttk.Frame(frame)
        grab_frame.pack(fill="x", pady=4)
        ttk.Label(grab_frame, text="Grab状態:", width=15).pack(side="left")
        ttk.Button(grab_frame, text="Grab開始", command=self.test_grab_start, width=10).pack(side="left", padx=2)
        ttk.Button(grab_frame, text="Grab終了", command=self.test_grab_end, width=10).pack(side="left", padx=2)

        stretch_frame = ttk.Frame(frame)
        stretch_frame.pack(fill="x", pady=4)
        ttk.Label(stretch_frame, text="Stretch値:", width=15).pack(side="left")
        self.test_stretch_slider = ttk.Scale(
            stretch_frame, from_=0.0, to=1.0, orient="horizontal",
            variable=self.test_stretch_var, command=self.on_test_stretch_change,
        )
        self.test_stretch_slider.pack(side="left", fill="x", expand=True, padx=5)
        self.test_stretch_label = ttk.Label(stretch_frame, text="0.000", width=6)
        self.test_stretch_label.pack(side="left")

        quick_frame = ttk.Frame(frame)
        quick_frame.pack(fill="x", pady=4)
        ttk.Label(quick_frame, text="クイックテスト:", width=15).pack(side="left")
        ttk.Button(quick_frame, text="弱い掴み", width=12,
                   command=lambda: self.test_grab_sequence(0.3, 1.5)).pack(side="left", padx=2)
        ttk.Button(quick_frame, text="中くらい", width=12,
                   command=lambda: self.test_grab_sequence(0.6, 2.0)).pack(side="left", padx=2)
        ttk.Button(quick_frame, text="強い掴み", width=12,
                   command=lambda: self.test_grab_sequence(0.9, 2.5)).pack(side="left", padx=2)

    def test_grab_start(self):
        self.test_stretch_var.set(0.0)
        self.test_stretch_label.config(text="0.000")
        if self.grab_state:
            self.grab_state.is_test_mode = True
            self.grab_state.on_grabbed_change(True)
        print("[Test Send] Grab Start")

    def test_grab_end(self):
        stretch = self.test_stretch_var.get()
        if self.grab_state:
            self.grab_state.on_grabbed_change(False)
            self.grab_state.is_test_mode = False
        self.test_stretch_var.set(0.0)
        self.test_stretch_label.config(text="0.000")
        print(f"[Test Send] Grab End (Final Stretch: {stretch:.3f})")

    def on_test_stretch_change(self, value):
        stretch = float(value)
        self.test_stretch_label.config(text=f"{stretch:.3f}")
        if self.grab_state and self.grab_state.is_grabbed:
            self.grab_state.on_stretch_change(stretch)

    def test_grab_sequence(self, max_stretch: float, duration: float):
        def sequence():
            if self.grab_state:
                self.grab_state.is_test_mode = True
            self.test_grab_start()
            time_module.sleep(0.1)
            steps = 20
            for i in range(steps + 1):
                stretch = (max_stretch / steps) * i
                self.test_stretch_var.set(stretch)
                self.on_test_stretch_change(stretch)
                time_module.sleep(duration / steps)
            self.test_grab_end()
            if self.grab_state:
                self.grab_state.is_test_mode = False
            print(f"[Test Complete] max_stretch={max_stretch:.1f}, duration={duration:.1f}s")

        threading.Thread(target=sequence, daemon=True).start()
