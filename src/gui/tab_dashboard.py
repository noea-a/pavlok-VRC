import tkinter as tk
from tkinter import ttk
import threading
import time as time_module


class DashboardTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.grab_state = None
        self._create_widgets()

    def set_grab_state(self, grab_state):
        self.grab_state = grab_state

    def _create_widgets(self):
        frame = ttk.LabelFrame(self, text="リアルタイム状態", padding=10)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Grab 状態
        grab_frame = ttk.Frame(frame)
        grab_frame.pack(fill="x", pady=10)
        ttk.Label(grab_frame, text="Grab 状態:", width=15).pack(side="left")
        self.grab_status_label = ttk.Label(grab_frame, text="False", foreground="blue")
        self.grab_status_label.pack(side="left")

        # Stretch 値
        stretch_frame = ttk.Frame(frame)
        stretch_frame.pack(fill="x", pady=10)
        ttk.Label(stretch_frame, text="Stretch 値:", width=15).pack(side="left")
        self.stretch_slider = ttk.Scale(stretch_frame, from_=0.0, to=1.0, orient="horizontal", state="disabled")
        self.stretch_slider.pack(side="left", fill="x", expand=True, padx=5)
        self.stretch_label = ttk.Label(stretch_frame, text="0.000", width=6)
        self.stretch_label.pack(side="left")

        # 計算強度
        intensity_frame = ttk.Frame(frame)
        intensity_frame.pack(fill="x", pady=10)
        ttk.Label(intensity_frame, text="計算強度:", width=15).pack(side="left")
        self.intensity_progressbar = ttk.Progressbar(intensity_frame, length=300, mode="determinate", maximum=100)
        self.intensity_progressbar.pack(side="left", fill="x", expand=True, padx=5)
        self.intensity_label = ttk.Label(intensity_frame, text="0", width=6)
        self.intensity_label.pack(side="left")

        # OSC 接続状態
        osc_frame = ttk.Frame(frame)
        osc_frame.pack(fill="x", pady=10)
        ttk.Label(osc_frame, text="OSC 接続:", width=15).pack(side="left")
        self.osc_status_label = ttk.Label(osc_frame, text="接続中", foreground="green")
        self.osc_status_label.pack(side="left")

        # 詳細情報
        detail_frame = ttk.LabelFrame(frame, text="詳細情報", padding=10)
        detail_frame.pack(fill="x", pady=10)
        self.detail_text = tk.Text(detail_frame, height=5, width=60, state="disabled")
        self.detail_text.pack(fill="both", expand=True)

        # テスト送信パネル
        test_frame = ttk.LabelFrame(frame, text="テスト送信（VRChat不要）", padding=10)
        test_frame.pack(fill="x", pady=10)

        grab_test_frame = ttk.Frame(test_frame)
        grab_test_frame.pack(fill="x", pady=5)
        ttk.Label(grab_test_frame, text="Grab状態:", width=15).pack(side="left")
        ttk.Button(grab_test_frame, text="Grab開始", command=self.test_grab_start, width=10).pack(side="left", padx=2)
        ttk.Button(grab_test_frame, text="Grab終了", command=self.test_grab_end, width=10).pack(side="left", padx=2)

        stretch_test_frame = ttk.Frame(test_frame)
        stretch_test_frame.pack(fill="x", pady=5)
        ttk.Label(stretch_test_frame, text="Stretch値:", width=15).pack(side="left")
        self.test_stretch_var = tk.DoubleVar(value=0.0)
        self.test_stretch_slider = ttk.Scale(stretch_test_frame, from_=0.0, to=1.0, orient="horizontal",
                                              variable=self.test_stretch_var, command=self.on_test_stretch_change)
        self.test_stretch_slider.pack(side="left", fill="x", expand=True, padx=5)
        self.test_stretch_label = ttk.Label(stretch_test_frame, text="0.000", width=6)
        self.test_stretch_label.pack(side="left")

        quick_test_frame = ttk.Frame(test_frame)
        quick_test_frame.pack(fill="x", pady=5)
        ttk.Label(quick_test_frame, text="クイックテスト:", width=15).pack(side="left")
        ttk.Button(quick_test_frame, text="弱い掴み", command=lambda: self.test_grab_sequence(0.3, 1.5), width=12).pack(side="left", padx=2)
        ttk.Button(quick_test_frame, text="中くらい", command=lambda: self.test_grab_sequence(0.6, 2.0), width=12).pack(side="left", padx=2)
        ttk.Button(quick_test_frame, text="強い掴み", command=lambda: self.test_grab_sequence(0.9, 2.5), width=12).pack(side="left", padx=2)

    def update(self, data: dict):
        from datetime import datetime
        from pavlok_controller import normalize_intensity_for_display
        try:
            is_grabbed = data.get('is_grabbed', False)
            stretch = data.get('stretch', 0.0)
            intensity = data.get('intensity', 0)
            last_zap_display = data.get('last_zap_display_intensity', 0)
            last_zap_actual = data.get('last_zap_actual_intensity', 0)

            if is_grabbed:
                self.grab_status_label.config(text="True", foreground="red")
            else:
                self.grab_status_label.config(text="False", foreground="blue")

            self.stretch_slider.set(stretch)
            self.stretch_label.config(text=f"{stretch:.3f}")

            if intensity == 0:
                intensity_percent = 0
            else:
                intensity_percent = normalize_intensity_for_display(intensity)
            self.intensity_progressbar['value'] = intensity_percent
            self.intensity_label.config(text=f"{intensity_percent}%")

            self.detail_text.config(state="normal")
            self.detail_text.delete("1.0", "end")
            detail_info = f"時刻: {datetime.now().strftime('%H:%M:%S')}\n"
            detail_info += f"計算強度: {intensity_percent}% (表示値) / {intensity} (内部値)\n"
            if last_zap_display > 0:
                detail_info += f"最終Zap: {last_zap_display}% (内部値: {last_zap_actual})\n"
            else:
                detail_info += "最終Zap: なし\n"
            self.detail_text.insert("1.0", detail_info)
            self.detail_text.config(state="disabled")
        except Exception as e:
            print(f"Error updating dashboard: {e}")

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
        if self.grab_status_label.cget("text") == "True":
            if self.grab_state:
                self.grab_state.on_stretch_change(stretch)

    def test_grab_sequence(self, max_stretch, duration):
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
