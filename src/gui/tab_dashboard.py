import threading
import tkinter as tk
from tkinter import ttk

_EXAMPLE_MAC = "XX:XX:XX:XX:XX:XX"


def _get_valid_mac() -> str:
    """有効な MAC アドレスを返す。未設定またはサンプル値の場合は空文字。"""
    import os
    mac = os.getenv("BLE_DEVICE_MAC", "").strip()
    if mac == _EXAMPLE_MAC:
        return ""
    return mac


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
        # MAC が設定されている場合のみ自動接続を試みる
        if _get_valid_mac():
            self.after(500, self._on_connect)
        else:
            self._ble_status_label.config(text="未設定", foreground="orange")

    def _create_widgets(self):
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
        self._delete_btn = ttk.Button(btn_row, text="削除", width=10, command=self._on_delete_mac)
        self._delete_btn.pack(side="left")

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
        # MAC アドレスが未設定の場合はスキャン
        if not _get_valid_mac():
            self._on_scan_devices()
            return

        if self._device is None:
            return
        self._connect_btn.config(state="disabled")
        self._ble_status_label.config(text="接続中...", foreground="orange")

        def _do_connect():
            ok = self._device.connect()
            self.after(0, lambda: self._after_connect(ok))

        threading.Thread(target=_do_connect, daemon=True).start()

    _BATT_RETRY_MS = 5_000  # 取得失敗時のリトライ間隔

    def _after_connect(self, ok: bool):
        if ok:
            self._ble_status_label.config(text="接続済み", foreground="green")
            self._connect_btn.config(state="disabled")
            self._disconnect_btn.config(state="normal")
            self._refresh_battery()
        else:
            self._ble_status_label.config(text="接続失敗", foreground="red")
            self._connect_btn.config(state="normal")

    def _schedule_battery_refresh(self, failed: bool = False):
        import settings as s_mod
        if failed:
            interval_ms = self._BATT_RETRY_MS
        else:
            interval_sec = s_mod.settings.ble.battery_refresh_interval
            if interval_sec <= 0:
                return
            interval_ms = int(interval_sec * 1000)
        self._batt_timer = self.after(interval_ms, self._periodic_battery_refresh)

    def _periodic_battery_refresh(self):
        if self._device is None or not getattr(self._device, 'is_connected', False):
            return
        self._refresh_battery()

    def _on_disconnect(self):
        if self._device is None:
            return
        self._disconnect_btn.config(state="disabled")
        if hasattr(self, '_batt_timer') and self._batt_timer:
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
            self._schedule_battery_refresh(failed=True)
        else:
            color = "green" if level > 30 else "orange" if level > 15 else "red"
            self._batt_label.config(text=f"{level}%", foreground=color)
            self._schedule_battery_refresh(failed=False)

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

    def _on_scan_devices(self):
        """BLE デバイスをスキャンして見つかったデバイスを選択"""
        import asyncio
        from bleak import BleakScanner

        self._ble_status_label.config(text="スキャン中...", foreground="orange")
        self._connect_btn.config(state="disabled")

        def scan():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    devices = loop.run_until_complete(BleakScanner.discover(timeout=5.0))
                finally:
                    loop.close()
                self.after(0, lambda: self._show_scan_results(devices))
            except Exception as e:
                self.after(0, lambda: self._on_scan_error(str(e)))

        threading.Thread(target=scan, daemon=True).start()

    def _on_scan_error(self, msg: str):
        from tkinter import messagebox
        self._ble_status_label.config(text="スキャン失敗", foreground="red")
        self._connect_btn.config(state="normal")
        messagebox.showerror("エラー", f"スキャン失敗: {msg}")

    def _show_scan_results(self, devices):
        """スキャン結果をリストボックスで表示（メインスレッド）"""
        from tkinter import messagebox, Toplevel, Listbox, Scrollbar, Button, Label, END, SINGLE

        self._ble_status_label.config(text="未接続", foreground="gray")
        self._connect_btn.config(state="normal")

        if not devices:
            messagebox.showwarning("スキャン結果", "BLE デバイスが見つかりませんでした。\nPavlok の電源が入っているか確認してください。")
            return

        # モーダルダイアログを作成
        dialog = Toplevel(self)
        dialog.title("BLE デバイス選択")
        dialog.resizable(False, False)
        dialog.grab_set()

        Label(dialog, text="接続するデバイスを選択してください:", padx=10, pady=8).pack()

        frame = ttk.Frame(dialog, padding=5)
        frame.pack(fill="both", expand=True)

        scrollbar = Scrollbar(frame)
        scrollbar.pack(side="right", fill="y")

        listbox = Listbox(frame, yscrollcommand=scrollbar.set, width=50, height=min(len(devices), 10),
                          selectmode=SINGLE)
        listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=listbox.yview)

        for d in devices:
            listbox.insert(END, f"{d.name or 'Unknown'}  |  {d.address}")

        btn_frame = ttk.Frame(dialog, padding=5)
        btn_frame.pack(fill="x")

        selected_mac = [None]

        def on_select():
            idx = listbox.curselection()
            if not idx:
                messagebox.showwarning("未選択", "デバイスを選択してください", parent=dialog)
                return
            line = listbox.get(idx[0])
            mac = line.split("|")[-1].strip()
            selected_mac[0] = mac
            dialog.destroy()

        Button(btn_frame, text="選択", width=10, command=on_select).pack(side="left", padx=5, pady=5)
        Button(btn_frame, text="キャンセル", width=10, command=dialog.destroy).pack(side="left", padx=5, pady=5)

        dialog.wait_window()

        mac = selected_mac[0]
        if not mac:
            return

        self._save_mac_to_env(mac)
        # os.environ に反映してから接続
        import os
        os.environ["BLE_DEVICE_MAC"] = mac

        self._connect_with_new_mac(mac)

    def _connect_with_new_mac(self, mac: str):
        """新しい MAC アドレスでデバイスを再生成して接続"""
        import settings as s_mod
        # settings オブジェクトの MAC を更新
        s_mod.settings.ble.device_mac = mac

        # デバイスオブジェクトを再生成
        from devices.factory import create_device
        if self._device is not None:
            try:
                self._device.disconnect()
            except Exception:
                pass
        self._device = create_device()

        self._connect_btn.config(state="disabled")
        self._ble_status_label.config(text="接続中...", foreground="orange")

        def _do_connect():
            ok = self._device.connect()
            self.after(0, lambda: self._after_connect(ok))

        threading.Thread(target=_do_connect, daemon=True).start()

    def _save_mac_to_env(self, mac: str):
        """MAC アドレスを .env に保存"""
        from pathlib import Path
        env_path = Path(__file__).parent.parent.parent / ".env"

        if env_path.exists():
            with open(env_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        else:
            lines = []

        # BLE_DEVICE_MAC 行を探すか、新規追加
        found = False
        for i, line in enumerate(lines):
            if line.startswith("BLE_DEVICE_MAC="):
                lines[i] = f"BLE_DEVICE_MAC={mac}\n"
                found = True
                break

        if not found:
            lines.append(f"BLE_DEVICE_MAC={mac}\n")

        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(lines)

    def _on_delete_mac(self):
        """MAC アドレスを .env から削除"""
        import os
        from pathlib import Path
        from tkinter import messagebox

        env_path = Path(__file__).parent.parent.parent / ".env"

        if env_path.exists():
            with open(env_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            for i, line in enumerate(lines):
                if line.startswith("BLE_DEVICE_MAC="):
                    lines[i] = f"BLE_DEVICE_MAC={_EXAMPLE_MAC}\n"
                    break
            with open(env_path, "w", encoding="utf-8") as f:
                f.writelines(lines)

        # os.environ からも削除してセッション内で即反映
        os.environ.pop("BLE_DEVICE_MAC", None)

        # デバイスを切断
        if self._device is not None:
            try:
                self._device.disconnect()
            except Exception:
                pass

        self._ble_status_label.config(text="未設定", foreground="orange")
        self._connect_btn.config(state="normal")
        self._disconnect_btn.config(state="disabled")
        self._batt_btn.config(state="disabled")
        self._batt_label.config(text="--", foreground="gray")

