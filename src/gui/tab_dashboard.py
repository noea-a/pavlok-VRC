import threading
import tkinter as tk
from tkinter import ttk
from version import __version__


class DashboardTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.grab_state = None
        self._device = None
        self._create_widgets()

    def set_grab_state(self, grab_state):
        self.grab_state = grab_state

    def set_device(self, device):
        self._device = device
        self._refresh_ble_status()
        # 初回起動時は自動で接続を試みる
        self.after(500, self._on_connect)

    def _create_widgets(self):
        # ---- アプリケーション情報 ----
        info_frame = ttk.Frame(self, padding=5)
        info_frame.pack(fill="x", padx=10, pady=(10, 0))
        ttk.Label(info_frame, text=f"VRChat Pavlok Connector v{__version__}", font=("", 9, "bold")).pack(side="left")

        # ---- BLE 接続パネル ----
        ble_frame = ttk.LabelFrame(self, text="デバイス接続", padding=10)
        ble_frame.pack(fill="x", padx=10, pady=(10, 0))

        status_row = ttk.Frame(ble_frame)
        status_row.pack(fill="x")
        ttk.Label(status_row, text="接続状態:", width=12).pack(side="left")
        self._ble_status_label = ttk.Label(status_row, text="未接続", foreground="gray")
        self._ble_status_label.pack(side="left", padx=5)

        batt_row = ttk.Frame(ble_frame)
        batt_row.pack(fill="x", pady=(4, 0))
        ttk.Label(batt_row, text="バッテリー:", width=12).pack(side="left")
        self._batt_label = ttk.Label(batt_row, text="--", foreground="gray")
        self._batt_label.pack(side="left", padx=5)

        btn_row = ttk.Frame(ble_frame)
        btn_row.pack(fill="x", pady=(6, 0))
        self._connect_btn = ttk.Button(btn_row, text="接続", width=10, command=self._on_connect)
        self._connect_btn.pack(side="left", padx=(0, 4))
        self._disconnect_btn = ttk.Button(btn_row, text="切断", width=10, command=self._on_disconnect, state="disabled")
        self._disconnect_btn.pack(side="left", padx=(0, 8))
        self._batt_btn = ttk.Button(btn_row, text="残量更新", width=10, command=self._refresh_battery, state="disabled")
        self._batt_btn.pack(side="left")

        # ---- リアルタイム状態 ----
        frame = ttk.LabelFrame(self, text="リアルタイム状態", padding=10)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        # 掴み状態
        grab_frame = ttk.Frame(frame)
        grab_frame.pack(fill="x", pady=10)
        ttk.Label(grab_frame, text="掴み状態:", width=15).pack(side="left")
        self.grab_status_label = ttk.Label(grab_frame, text="False", foreground="blue")
        self.grab_status_label.pack(side="left")

        # 引っ張り度
        stretch_frame = ttk.Frame(frame)
        stretch_frame.pack(fill="x", pady=10)
        ttk.Label(stretch_frame, text="引っ張り度:", width=15).pack(side="left")
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


    # ------------------------------------------------------------------ #
    # BLE 接続制御                                                         #
    # ------------------------------------------------------------------ #

    def _refresh_ble_status(self):
        if self._device is None:
            return
        connected = getattr(self._device, 'is_connected', False)
        if connected:
            self._ble_status_label.config(text="接続済み", foreground="green")
            self._connect_btn.config(state="disabled")
            self._disconnect_btn.config(state="normal")
        else:
            self._ble_status_label.config(text="未接続", foreground="gray")
            self._connect_btn.config(state="normal")
            self._disconnect_btn.config(state="disabled")

    def _on_connect(self):
        if self._device is None:
            return
        self._connect_btn.config(state="disabled")
        self._ble_status_label.config(text="接続中...", foreground="orange")

        def _do_connect():
            ok = self._device.connect()
            self.after(0, lambda: self._after_connect(ok))

        threading.Thread(target=_do_connect, daemon=True).start()

    def _after_connect(self, ok: bool):
        if ok:
            self._ble_status_label.config(text="接続済み", foreground="green")
            self._connect_btn.config(state="disabled")
            self._disconnect_btn.config(state="normal")
            self._batt_btn.config(state="normal")
            self._refresh_battery()
            self._schedule_battery_refresh()
        else:
            self._ble_status_label.config(text="接続失敗", foreground="red")
            self._connect_btn.config(state="normal")

    def _schedule_battery_refresh(self):
        import settings as s_mod
        interval_sec = s_mod.settings.ble.battery_refresh_interval
        if interval_sec <= 0:
            return
        interval_ms = int(interval_sec * 1000)
        self._batt_timer = self.after(interval_ms, self._periodic_battery_refresh)

    def _periodic_battery_refresh(self):
        if self._device is None or not getattr(self._device, 'is_connected', False):
            return
        self._refresh_battery()
        self._schedule_battery_refresh()

    def _on_disconnect(self):
        if self._device is None:
            return
        self._disconnect_btn.config(state="disabled")
        self._batt_btn.config(state="disabled")
        if hasattr(self, '_batt_timer'):
            self.after_cancel(self._batt_timer)
            self._batt_timer = None
        self._device.disconnect()
        self._ble_status_label.config(text="未接続", foreground="gray")
        self._batt_label.config(text="--", foreground="gray")
        self._connect_btn.config(state="normal")

    def _refresh_battery(self):
        if self._device is None:
            return

        def _do_read():
            level = None
            if hasattr(self._device, 'read_battery'):
                level = self._device.read_battery()
            self.after(0, lambda: self._update_battery(level))

        threading.Thread(target=_do_read, daemon=True).start()

    def _update_battery(self, level: int | None):
        if level is None:
            self._batt_label.config(text="取得失敗", foreground="red")
        else:
            color = "green" if level > 30 else "orange" if level > 15 else "red"
            self._batt_label.config(text=f"{level}%", foreground=color)

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

