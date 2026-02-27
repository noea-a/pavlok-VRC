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
        self._create_unit_test_panel()
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
