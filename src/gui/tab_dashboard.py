import tkinter as tk
from tkinter import ttk


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

