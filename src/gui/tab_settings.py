import tkinter as tk
from tkinter import ttk, messagebox
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import settings as settings_module


class SettingsTab(ttk.Frame):
    _LABEL_WIDTH = 28  # スピンボックス・チェックボックスのラベル幅（統一）

    def __init__(self, parent):
        super().__init__(parent)
        self._adv_visible = False
        self._create_widgets()
        self.load_settings()

    # ------------------------------------------------------------------ #
    #  スクロール可能なコンテナ
    # ------------------------------------------------------------------ #

    def _create_widgets(self):
        scrollbar = ttk.Scrollbar(self, orient="vertical")
        scrollbar.pack(side="right", fill="y")

        self._canvas = tk.Canvas(self, yscrollcommand=scrollbar.set, highlightthickness=0)
        self._canvas.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self._canvas.yview)

        self._inner = ttk.Frame(self._canvas)
        self._inner_id = self._canvas.create_window((0, 0), window=self._inner, anchor="nw")

        self._inner.bind("<Configure>", self._on_inner_configure)
        self._canvas.bind("<Configure>", self._on_canvas_configure)
        self._canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        self.setting_widgets = {}
        self._build_content(self._inner)

    def _on_inner_configure(self, _event):
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self._canvas.itemconfig(self._inner_id, width=event.width)

    def _on_mousewheel(self, event):
        # スピンボックス上ではウィンドウスクロール無視、Box外では普通にスクロール
        if isinstance(event.widget, ttk.Spinbox):
            return "break"
        self._canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    # ------------------------------------------------------------------ #
    #  コンテンツ本体
    # ------------------------------------------------------------------ #

    def _build_content(self, parent):
        outer = ttk.Frame(parent, padding=10)
        outer.pack(fill="both", expand=True)

        # ===== 基本設定 =====
        basic_frame = ttk.LabelFrame(outer, text="基本設定", padding=10)
        basic_frame.pack(fill="x", pady=(0, 6))

        self._add_spinbox_items(basic_frame, [
            ("MIN_STIMULUS_VALUE", "Zap の最小値（％）", "int", 15, 0, 100, 1, ""),
            ("MAX_STIMULUS_VALUE", "Zap の最大値（％）", "int", 70, 0, 100, 1, ""),
            ("VIBRATION_ON_STRETCH_THRESHOLD", "高出力の警告（％）", "float", 70, 0, 100, 100, "高出力の場合にバイブで警告します"),
        ])

        # ===== 詳細設定 トグル =====
        self._toggle_btn = ttk.Button(
            outer, text="▶ 詳細設定", command=self._toggle_advanced
        )
        self._toggle_btn.pack(fill="x", pady=(4, 0))

        self._advanced_frame = ttk.Frame(outer)
        self._build_advanced(self._advanced_frame)

        # ===== 保存ボタン =====
        self._btn_frame = ttk.Frame(outer)
        self._btn_frame.pack(fill="x", pady=12)
        ttk.Button(self._btn_frame, text="保存",      command=self.save_settings).pack(side="left", padx=5)
        ttk.Button(self._btn_frame, text="キャンセル", command=self.load_settings).pack(side="left", padx=5)
        ttk.Button(self._btn_frame, text="デフォルト", command=self.reset_settings).pack(side="left", padx=5)

    def _build_advanced(self, parent):
        # --- Zap 強度・閾値 ---
        zap_frame = ttk.LabelFrame(parent, text="Zap 強度・閾値", padding=8)
        zap_frame.pack(fill="x", pady=(6, 4))
        self._add_spinbox_items(zap_frame, [
            ("MIN_GRAB_DURATION", "掴み判定時間（秒）", "float", 0.8, 0.1, 10.0, 1, "これ未満の掴み時間は処理しません"),
            ("MIN_STRETCH_THRESHOLD", "最小閾値", "float", 0.03, 0.0, 1.0, 1, "これ未満の引っ張り度は処理しません"),
            ("VIBRATION_HYSTERESIS_OFFSET", "高出力警告のヒステリシス（％）", "float", 15, 0, 100, 100, "チャタリング防止"),
        ])

        # --- 掴み開始バイブ ---
        gs_frame = ttk.LabelFrame(parent, text="掴み開始バイブ", padding=8)
        gs_frame.pack(fill="x", pady=4)
        self._add_spinbox_items(gs_frame, [
            ("GRAB_START_VIBRATION_INTENSITY", "強度（％）", "int", 20, 0, 100, 1, ""),
            ("GRAB_START_VIBRATION_TON", "継続時間（ms）", "int", 10, 0, 255, 1, ""),
            ("GRAB_START_VIBRATION_COUNT", "実行回数", "int", 1, 1, 127, 1, ""),
            ("GRAB_START_VIBRATION_TOFF", "インターバル（ms）", "int", 10, 0, 255, 1, ""),
        ])

        # --- 警告バイブ ---
        sv_frame = ttk.LabelFrame(parent, text="高出力の警告バイブ", padding=8)
        sv_frame.pack(fill="x", pady=4)
        self._add_spinbox_items(sv_frame, [
            ("VIBRATION_ON_STRETCH_INTENSITY", "強度（％）", "int", 80, 0, 100, 1, ""),
            ("VIBRATION_ON_STRETCH_TON", "継続時間（ms）", "int", 6, 0, 255, 1, ""),
            ("VIBRATION_ON_STRETCH_COUNT", "実行回数", "int", 2, 1, 127, 1, ""),
            ("VIBRATION_ON_STRETCH_TOFF", "インターバル（ms）", "int", 12, 0, 255, 1, ""),
        ])

        # --- OSC ---
        osc_frame = ttk.LabelFrame(parent, text="OSC", padding=8)
        osc_frame.pack(fill="x", pady=4)
        self._add_spinbox_items(osc_frame, [
            ("OSC_LISTEN_PORT", "受信ポート", "int", 9001, 1024, 65535, 1, "VRChat からの OSC 受信ポート"),
            ("OSC_SEND_PORT", "送信ポート", "int", 9000, 1024, 65535, 1, "VRChat への OSC 送信ポート"),
        ])
        # Zap予測値関連
        row = 2
        self._add_bool_item(osc_frame, "SEND_REALTIME_CHATBOX", "掴み中の Zap 予測値", True,
                            row=row, desc="Zap の予測値をリアルタイム表示")
        row += 1
        # 更新間隔
        ttk.Label(osc_frame, text="Chatbox 更新間隔（秒）", width=self._LABEL_WIDTH).grid(row=row, column=0, sticky="w", pady=3)
        spinbox = ttk.Spinbox(osc_frame, from_=0.0, to=10.0, width=8, increment=0.1)
        spinbox.insert(0, "1.5")
        spinbox.grid(row=row, column=1, sticky="w", padx=5, pady=3)
        ttk.Label(osc_frame, text="極端に短くするとスパムとして扱われる可能性があります", foreground="gray").grid(
            row=row, column=2, sticky="w", padx=(0, 8), pady=3
        )
        self.setting_widgets["OSC_SEND_INTERVAL"] = {
            "widget": spinbox, "type": "float", "label": "Chatbox 更新間隔（秒）",
            "display_scale": 1,
        }
        row += 1
        self._add_bool_item(osc_frame, "SEND_FINAL_CHATBOX", "Zap 実行値", True,
                            row=row, desc="実際に実行された Zap 値を表示")

        # --- BLE ---
        ble_frame = ttk.LabelFrame(parent, text="BLE 接続", padding=8)
        ble_frame.pack(fill="x", pady=4)
        self._add_spinbox_items(ble_frame, [
            ("BLE_CONNECT_TIMEOUT", "接続タイムアウト（秒）", "float", 10.0, 1.0, 60.0, 1, "接続試行を諦めるまでの時間"),
            ("BLE_RECONNECT_INTERVAL", "再接続間隔（秒）", "float", 5.0, 1.0, 30.0, 1, "切断後に再接続を試みる周期"),
            ("BLE_KEEPALIVE_INTERVAL", "接続維持間隔（秒）", "float", 5.5, 1.0, 60.0, 1, "接続維持信号の送信周期（6秒未満を推奨）"),
            ("BLE_BATTERY_REFRESH_INTERVAL", "バッテリー更新間隔（秒）", "float", 180.0, 0.0, 600.0, 1, ""),
        ])

        # --- デバッグログ ---
        log_frame = ttk.LabelFrame(parent, text="デバッグログ", padding=8)
        log_frame.pack(fill="x", pady=(4, 6))
        log_items = [
            ("LOG_STRETCH", "Stretch", True, "引っ張り度"),
            ("LOG_IS_GRABBED", "IsGrabbed", True, "掴み状態"),
            ("LOG_ANGLE", "Angle", False, "角度"),
            ("LOG_IS_POSED", "IsPosed", False, "固定状態"),
            ("LOG_OSC_SEND", "OSC 送信", True, "OSC 送信内容"),
            ("LOG_ALL_OSC", "OSC 受信（全て）", False, "OSC 受信内容（大量に出るので注意）"),
        ]
        for i, (key, label, default, desc) in enumerate(log_items):
            self._add_bool_item(log_frame, key, label, default, row=i, desc=desc)

    # ------------------------------------------------------------------ #
    #  ウィジェット生成ヘルパー
    # ------------------------------------------------------------------ #

    def _add_spinbox_items(self, parent, items):
        for i, item in enumerate(items):
            key, label, value_type, default, min_val, max_val = item[:6]
            display_scale = item[6] if len(item) > 6 else 1
            desc = item[7] if len(item) > 7 else ""
            ttk.Label(parent, text=label, width=self._LABEL_WIDTH).grid(row=i, column=0, sticky="w", pady=3)
            inc = 1 if value_type == "int" else 0.1
            spinbox = ttk.Spinbox(parent, from_=min_val, to=max_val, width=8, increment=inc)
            spinbox.insert(0, str(default))
            spinbox.grid(row=i, column=1, sticky="w", padx=5, pady=3)
            if desc:
                ttk.Label(parent, text=desc, foreground="gray").grid(
                    row=i, column=2, sticky="w", padx=(0, 8), pady=3
                )
            self.setting_widgets[key] = {
                "widget": spinbox, "type": value_type, "label": label,
                "display_scale": display_scale,
            }

    def _add_bool_item(self, parent, key, label, default, row, desc=""):
        ttk.Label(parent, text=label, width=self._LABEL_WIDTH).grid(row=row, column=0, sticky="w", pady=3)
        var = tk.BooleanVar(value=default)
        cb = ttk.Checkbutton(parent, variable=var)
        cb.grid(row=row, column=1, sticky="w", padx=5, pady=3)
        if desc:
            ttk.Label(parent, text=desc, foreground="gray").grid(
                row=row, column=2, sticky="w", padx=(0, 8), pady=3
            )
        self.setting_widgets[key] = {"widget": cb, "type": "bool", "label": label, "var": var}

    # ------------------------------------------------------------------ #
    #  トグル
    # ------------------------------------------------------------------ #

    def _toggle_advanced(self):
        self._adv_visible = not self._adv_visible
        if self._adv_visible:
            self._advanced_frame.pack(fill="x", before=self._btn_frame)
            self._toggle_btn.config(text="▼ 詳細設定")
        else:
            self._advanced_frame.pack_forget()
            self._toggle_btn.config(text="▶ 詳細設定")

    # ------------------------------------------------------------------ #
    #  設定値 ↔ ウィジェット
    # ------------------------------------------------------------------ #

    def _current_values(self) -> dict:
        s = settings_module.settings
        return {
            "MIN_STIMULUS_VALUE":             s.device.min_stimulus_value,
            "MAX_STIMULUS_VALUE":             s.device.max_stimulus_value,
            "MIN_GRAB_DURATION":              s.logic.min_grab_duration,
            "MIN_STRETCH_THRESHOLD":          s.logic.min_stretch_threshold,
            "VIBRATION_ON_STRETCH_THRESHOLD": s.stretch_vibration.threshold,
            "VIBRATION_HYSTERESIS_OFFSET":    s.stretch_vibration.hysteresis_offset,
            "GRAB_START_VIBRATION_INTENSITY": s.grab_start_vibration.intensity,
            "GRAB_START_VIBRATION_COUNT":     s.grab_start_vibration.count,
            "GRAB_START_VIBRATION_TON":       s.grab_start_vibration.ton,
            "GRAB_START_VIBRATION_TOFF":      s.grab_start_vibration.toff,
            "VIBRATION_ON_STRETCH_INTENSITY": s.stretch_vibration.intensity,
            "VIBRATION_ON_STRETCH_COUNT":     s.stretch_vibration.count,
            "VIBRATION_ON_STRETCH_TON":       s.stretch_vibration.ton,
            "VIBRATION_ON_STRETCH_TOFF":      s.stretch_vibration.toff,
            "OSC_SEND_INTERVAL":              s.osc.send.interval,
            "SEND_REALTIME_CHATBOX":          s.osc.send.realtime_chatbox,
            "SEND_FINAL_CHATBOX":             s.osc.send.final_chatbox,
            "BLE_CONNECT_TIMEOUT":            s.ble.connect_timeout,
            "BLE_RECONNECT_INTERVAL":         s.ble.reconnect_interval,
            "BLE_KEEPALIVE_INTERVAL":         s.ble.keepalive_interval,
            "BLE_BATTERY_REFRESH_INTERVAL":   s.ble.battery_refresh_interval,
            "OSC_LISTEN_PORT":                s.osc.listen_port,
            "OSC_SEND_PORT":                  s.osc.send.port,
            "LOG_STRETCH":                    s.debug.log_stretch,
            "LOG_IS_GRABBED":                 s.debug.log_is_grabbed,
            "LOG_ANGLE":                      s.debug.log_angle,
            "LOG_IS_POSED":                   s.debug.log_is_posed,
            "LOG_OSC_SEND":                   s.debug.log_osc_send,
            "LOG_ALL_OSC":                    s.debug.log_all_osc,
        }

    def load_settings(self):
        try:
            values = self._current_values()
            for key, info in self.setting_widgets.items():
                value = values.get(key)
                if value is None:
                    continue
                if info["type"] == "bool":
                    info["var"].set(bool(value))
                else:
                    scale = info.get("display_scale", 1)
                    info["widget"].delete(0, "end")
                    info["widget"].insert(0, str(round(value * scale, 10)))
        except Exception as e:
            messagebox.showerror("エラー", f"設定の読み込みに失敗しました: {e}")

    def save_settings(self):
        changed = {}
        for key, info in self.setting_widgets.items():
            if info["type"] == "bool":
                changed[key] = info["var"].get()
            else:
                value_str = info["widget"].get()
                try:
                    scale = info.get("display_scale", 1)
                    if info["type"] == "int":
                        raw = int(float(value_str))  # "15.0" も "15" も対応
                        changed[key] = int(raw / scale) if scale != 1 else raw
                    else:
                        raw = float(value_str)
                        changed[key] = raw / scale
                except ValueError:
                    messagebox.showerror("エラー", f"{info['label']} の値が無効です: {value_str!r}")
                    return
        try:
            settings_module.save_user_settings(changed)
            messagebox.showinfo("成功", "設定を保存しました。\n次の操作から反映されます。")
            self.load_settings()
        except Exception as e:
            messagebox.showerror("エラー", f"設定の保存に失敗しました: {e}")

    def reset_settings(self):
        """設定をデフォルト値（default.toml）にリセット"""
        # default.toml から直接値を読み込む（常に最新で型を保証）
        from settings import _load_toml, _DEFAULT_TOML, _apply_toml, Settings
        default_data = _load_toml(_DEFAULT_TOML)
        default_settings = Settings()
        _apply_toml(default_settings, default_data)

        defaults = {
            "MIN_STIMULUS_VALUE":             default_settings.device.min_stimulus_value,
            "MAX_STIMULUS_VALUE":             default_settings.device.max_stimulus_value,
            "MIN_GRAB_DURATION":              default_settings.logic.min_grab_duration,
            "MIN_STRETCH_THRESHOLD":          default_settings.logic.min_stretch_threshold,
            "VIBRATION_ON_STRETCH_THRESHOLD": default_settings.stretch_vibration.threshold,
            "VIBRATION_HYSTERESIS_OFFSET":    default_settings.stretch_vibration.hysteresis_offset,
            "GRAB_START_VIBRATION_INTENSITY": default_settings.grab_start_vibration.intensity,
            "GRAB_START_VIBRATION_COUNT":     default_settings.grab_start_vibration.count,
            "GRAB_START_VIBRATION_TON":       default_settings.grab_start_vibration.ton,
            "GRAB_START_VIBRATION_TOFF":      default_settings.grab_start_vibration.toff,
            "VIBRATION_ON_STRETCH_INTENSITY": default_settings.stretch_vibration.intensity,
            "VIBRATION_ON_STRETCH_COUNT":     default_settings.stretch_vibration.count,
            "VIBRATION_ON_STRETCH_TON":       default_settings.stretch_vibration.ton,
            "VIBRATION_ON_STRETCH_TOFF":      default_settings.stretch_vibration.toff,
            "OSC_SEND_INTERVAL":              default_settings.osc.send.interval,
            "SEND_REALTIME_CHATBOX":          default_settings.osc.send.realtime_chatbox,
            "SEND_FINAL_CHATBOX":             default_settings.osc.send.final_chatbox,
            "BLE_CONNECT_TIMEOUT":            default_settings.ble.connect_timeout,
            "BLE_RECONNECT_INTERVAL":         default_settings.ble.reconnect_interval,
            "BLE_KEEPALIVE_INTERVAL":         default_settings.ble.keepalive_interval,
            "BLE_BATTERY_REFRESH_INTERVAL":   default_settings.ble.battery_refresh_interval,
            "OSC_LISTEN_PORT":                default_settings.osc.listen_port,
            "OSC_SEND_PORT":                  default_settings.osc.send.port,
            "LOG_STRETCH":                    default_settings.debug.log_stretch,
            "LOG_IS_GRABBED":                 default_settings.debug.log_is_grabbed,
            "LOG_ANGLE":                      default_settings.debug.log_angle,
            "LOG_IS_POSED":                   default_settings.debug.log_is_posed,
            "LOG_OSC_SEND":                   default_settings.debug.log_osc_send,
            "LOG_ALL_OSC":                    default_settings.debug.log_all_osc,
        }
        for key, value in defaults.items():
            if key not in self.setting_widgets:
                continue
            info = self.setting_widgets[key]
            if info["type"] == "bool":
                info["var"].set(value)
            else:
                info["widget"].delete(0, "end")
                scale = info.get("display_scale", 1)
                display_value = value * scale
                info["widget"].insert(0, str(round(display_value, 10)))
