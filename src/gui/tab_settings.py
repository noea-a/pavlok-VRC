import tkinter as tk
from tkinter import ttk, messagebox
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import settings as settings_module


class SettingsTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self._create_widgets()
        self.load_settings()

    def _create_widgets(self):
        settings_frame = ttk.LabelFrame(self, text="パラメータ設定", padding=15)
        settings_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.setting_widgets = {}

        setting_items = [
            ("MIN_STIMULUS_VALUE", "Zapの最小値", "int", 15, 0, 100),
            ("MAX_STIMULUS_VALUE", "Zapの最大値", "int", 70, 0, 100),
            ("MIN_GRAB_DURATION", "グラブ時間（秒）", "float", 0.8, 0.1, 10.0),
            ("MIN_STRETCH_THRESHOLD", "Stretchの最小閾値", "float", 0.03, 0.0, 1.0),
            ("VIBRATION_ON_STRETCH_THRESHOLD", "高出力の警告（バイブ）", "float", 0.7, 0.0, 1.0),
            ("VIBRATION_HYSTERESIS_OFFSET", "ヒステリシス幅（オフセット）", "float", 0.15, 0.0, 1.0),
            ("GRAB_START_VIBRATION_INTENSITY", "グラブ開始 強度", "int", 20, 0, 100),
            ("GRAB_START_VIBRATION_COUNT", "グラブ開始 反復回数", "int", 1, 1, 127),
            ("GRAB_START_VIBRATION_TON", "グラブ開始 ON時間", "int", 22, 0, 255),
            ("GRAB_START_VIBRATION_TOFF", "グラブ開始 OFF時間", "int", 22, 0, 255),
            ("VIBRATION_ON_STRETCH_INTENSITY", "警告バイブ 強度", "int", 80, 0, 100),
            ("VIBRATION_ON_STRETCH_COUNT", "警告バイブ 反復回数", "int", 1, 1, 127),
            ("VIBRATION_ON_STRETCH_TON", "警告バイブ ON時間", "int", 22, 0, 255),
            ("VIBRATION_ON_STRETCH_TOFF", "警告バイブ OFF時間", "int", 22, 0, 255),
            ("OSC_SEND_INTERVAL", "OSC送信間隔（秒）", "float", 1.5, 0.0, 10.0),
        ]

        for setting_key, label_text, value_type, default_val, min_val, max_val in setting_items:
            ttk.Label(settings_frame, text=label_text, width=25).grid(
                row=len(self.setting_widgets), column=0, sticky="w", pady=5
            )
            if value_type == "int":
                spinbox = ttk.Spinbox(settings_frame, from_=min_val, to=max_val, width=10)
            else:
                spinbox = ttk.Spinbox(settings_frame, from_=min_val, to=max_val, width=10, increment=0.1)
            spinbox.insert(0, str(default_val))
            spinbox.grid(row=len(self.setting_widgets), column=1, sticky="ew", padx=5, pady=5)
            self.setting_widgets[setting_key] = {
                "widget": spinbox,
                "type": value_type,
                "label": label_text,
            }

        # リアルタイム Chatbox 送信（Checkbox）
        ttk.Label(settings_frame, text="リアルタイム Chatbox 送信", width=25).grid(
            row=len(self.setting_widgets), column=0, sticky="w", pady=5
        )
        self.send_realtime_var = tk.BooleanVar(value=False)
        checkbox = ttk.Checkbutton(settings_frame, variable=self.send_realtime_var)
        checkbox.grid(row=len(self.setting_widgets), column=1, sticky="w", padx=5, pady=5)
        self.setting_widgets["SEND_REALTIME_CHATBOX"] = {
            "widget": checkbox,
            "type": "bool",
            "label": "リアルタイム Chatbox 送信",
            "var": self.send_realtime_var,
        }

        button_frame = ttk.Frame(settings_frame)
        button_frame.grid(row=len(self.setting_widgets), column=0, columnspan=2, pady=15)
        ttk.Button(button_frame, text="保存", command=self.save_settings).pack(side="left", padx=5)
        ttk.Button(button_frame, text="キャンセル", command=self.load_settings).pack(side="left", padx=5)
        ttk.Button(button_frame, text="デフォルト", command=self.reset_settings).pack(side="left", padx=5)

    # --- 設定値を画面に反映 ---

    def _current_values(self) -> dict:
        """settings モジュールから現在値を CONFIG_KEY → value の dict で返す"""
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
        }

    def load_settings(self):
        """設定を読み込んでウィジェットに反映する"""
        try:
            values = self._current_values()
            for key, widget_info in self.setting_widgets.items():
                value = values.get(key)
                if value is None:
                    continue
                if widget_info["type"] == "bool":
                    widget_info["var"].set(bool(value))
                else:
                    widget_info["widget"].delete(0, "end")
                    widget_info["widget"].insert(0, str(value))
        except Exception as e:
            messagebox.showerror("エラー", f"設定の読み込みに失敗しました: {e}")

    def save_settings(self):
        """入力値を user.toml に保存する"""
        changed = {}
        for key, widget_info in self.setting_widgets.items():
            if widget_info["type"] == "bool":
                changed[key] = widget_info["var"].get()
            else:
                value_str = widget_info["widget"].get()
                try:
                    if widget_info["type"] == "int":
                        changed[key] = int(value_str)
                    else:
                        changed[key] = float(value_str)
                except ValueError:
                    messagebox.showerror("エラー", f"{widget_info['label']} の値が無効です: {value_str!r}")
                    return

        try:
            settings_module.save_user_settings(changed)
            messagebox.showinfo("成功", "設定を保存しました。\n次の操作から反映されます。")
            self.load_settings()
        except Exception as e:
            messagebox.showerror("エラー", f"設定の保存に失敗しました: {e}")

    def reset_settings(self):
        """デフォルト値（default.toml の値）をウィジェットに反映する（保存はしない）"""
        defaults = {
            "MIN_STIMULUS_VALUE": 15,
            "MAX_STIMULUS_VALUE": 70,
            "MIN_GRAB_DURATION": 0.8,
            "MIN_STRETCH_THRESHOLD": 0.03,
            "VIBRATION_ON_STRETCH_THRESHOLD": 0.7,
            "VIBRATION_HYSTERESIS_OFFSET": 0.15,
            "GRAB_START_VIBRATION_INTENSITY": 20,
            "GRAB_START_VIBRATION_COUNT": 1,
            "GRAB_START_VIBRATION_TON": 10,
            "GRAB_START_VIBRATION_TOFF": 10,
            "VIBRATION_ON_STRETCH_INTENSITY": 80,
            "VIBRATION_ON_STRETCH_COUNT": 2,
            "VIBRATION_ON_STRETCH_TON": 6,
            "VIBRATION_ON_STRETCH_TOFF": 12,
            "OSC_SEND_INTERVAL": 1.5,
            "SEND_REALTIME_CHATBOX": True,
        }
        for key, value in defaults.items():
            if key not in self.setting_widgets:
                continue
            info = self.setting_widgets[key]
            if info["type"] == "bool":
                info["var"].set(value)
            else:
                info["widget"].delete(0, "end")
                info["widget"].insert(0, str(value))
