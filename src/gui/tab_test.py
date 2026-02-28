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

        # スクロール可能なコンテナ
        scrollbar = ttk.Scrollbar(self, orient="vertical")
        scrollbar.pack(side="right", fill="y")
        self._canvas = tk.Canvas(self, yscrollcommand=scrollbar.set, highlightthickness=0)
        self._canvas.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self._canvas.yview)
        self._inner = ttk.Frame(self._canvas)
        self._inner_id = self._canvas.create_window((0, 0), window=self._inner, anchor="nw")
        self._inner.bind("<Configure>", lambda e: self._canvas.configure(
            scrollregion=(0, 0, e.width, e.height)))
        self._canvas.bind("<Configure>", lambda e: self._canvas.itemconfig(self._inner_id, width=e.width))

        self._create_unit_test_panel()
        self._create_ble_raw_panel()
        self._create_grab_sim_panel()

    def enable_scroll(self):
        self._canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def disable_scroll(self):
        self._canvas.unbind_all("<MouseWheel>")

    def _on_mousewheel(self, event):
        if isinstance(event.widget, ttk.Spinbox):
            return "break"
        if self._canvas.yview() == (0.0, 1.0):
            return
        self._canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def set_grab_state(self, grab_state):
        self.grab_state = grab_state

    # ------------------------------------------------------------------ #
    # 単体テストセクション                                                 #
    # ------------------------------------------------------------------ #

    def _create_unit_test_panel(self):
        frame = ttk.LabelFrame(self._inner, text="単体テスト", padding=10)
        frame.pack(fill="x", padx=10, pady=(10, 5))

        vib_frame = ttk.Frame(frame)
        vib_frame.pack(fill="x", pady=4)
        ttk.Label(vib_frame, text="バイブ:", width=15).pack(side="left")
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
        frame = ttk.LabelFrame(self._inner, text="BLE 生コマンド（バイブ）", padding=10)
        frame.pack(fill="x", padx=10, pady=(5, 5))

        # パラメータ説明ラベル
        ttk.Label(frame, text="コマンド: [0x80|counter, mode, intensity, ton, toff]",
                  foreground="gray").pack(anchor="w", pady=(0, 6))

        grid = ttk.Frame(frame)
        grid.pack(fill="x")

        fields = [
            ("counter",   "実行回数 (0-127)",    1,   0, 127),
            ("mode",      "モード（不明）",              2,   0, 255),
            ("intensity", "強度 (0-100)",        50,  0, 100),
            ("ton",       "実行時間",                22,  0, 255),
            ("toff",      "インターバル",               22,  0, 255),
        ]

        self._raw_vars = {}
        for row, (key, label, default, mn, mx) in enumerate(fields):
            ttk.Label(grid, text=label, width=20).grid(row=row, column=0, sticky="w", pady=3)
            var = tk.IntVar(value=default)
            sb = ttk.Spinbox(grid, from_=mn, to=mx, textvariable=var, width=8)
            sb.grid(row=row, column=1, sticky="w", padx=5, pady=3)
            self._raw_vars[key] = var

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
        frame = ttk.LabelFrame(self._inner, text="掴みシミュレーション", padding=10)
        frame.pack(fill="x", padx=10, pady=(5, 10))

        grab_frame = ttk.Frame(frame)
        grab_frame.pack(fill="x", pady=4)
        ttk.Label(grab_frame, text="掴み状態:", width=15).pack(side="left")
        ttk.Button(grab_frame, text="掴み開始", command=self.test_grab_start, width=10).pack(side="left", padx=2)
        ttk.Button(grab_frame, text="掴み終了", command=self.test_grab_end, width=10).pack(side="left", padx=2)

        stretch_frame = ttk.Frame(frame)
        stretch_frame.pack(fill="x", pady=4)
        ttk.Label(stretch_frame, text="引っ張り度:", width=15).pack(side="left")
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
        ttk.Button(quick_frame, text="弱", width=8,
                   command=lambda: self.test_grab_sequence(0.3, 1.5)).pack(side="left", padx=2)
        ttk.Button(quick_frame, text="中", width=8,
                   command=lambda: self.test_grab_sequence(0.6, 2.0)).pack(side="left", padx=2)
        ttk.Button(quick_frame, text="強", width=8,
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
