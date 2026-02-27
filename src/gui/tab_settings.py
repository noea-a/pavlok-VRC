import tkinter as tk
from tkinter import ttk, messagebox
import ast
import importlib
from pathlib import Path


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
            ttk.Label(settings_frame, text=label_text, width=25).grid(row=len(self.setting_widgets), column=0, sticky="w", pady=5)
            if value_type == "int":
                spinbox = ttk.Spinbox(settings_frame, from_=min_val, to=max_val, width=10)
            else:
                spinbox = ttk.Spinbox(settings_frame, from_=min_val, to=max_val, width=10, increment=0.1)
            spinbox.insert(0, str(default_val))
            spinbox.grid(row=len(self.setting_widgets), column=1, sticky="ew", padx=5, pady=5)
            self.setting_widgets[setting_key] = {
                'widget': spinbox,
                'type': value_type,
                'label': label_text
            }

        # リアルタイム Chatbox 送信（Checkbox）
        ttk.Label(settings_frame, text="リアルタイム Chatbox 送信", width=25).grid(row=len(self.setting_widgets), column=0, sticky="w", pady=5)
        self.send_realtime_var = tk.BooleanVar(value=False)
        checkbox = ttk.Checkbutton(settings_frame, variable=self.send_realtime_var)
        checkbox.grid(row=len(self.setting_widgets), column=1, sticky="w", padx=5, pady=5)
        self.setting_widgets["SEND_REALTIME_CHATBOX"] = {
            'widget': checkbox,
            'type': 'bool',
            'label': 'リアルタイム Chatbox 送信',
            'var': self.send_realtime_var
        }

        button_frame = ttk.Frame(settings_frame)
        button_frame.grid(row=len(self.setting_widgets), column=0, columnspan=2, pady=15)
        ttk.Button(button_frame, text="保存", command=self.save_settings).pack(side="left", padx=5)
        ttk.Button(button_frame, text="キャンセル", command=self.load_settings).pack(side="left", padx=5)
        ttk.Button(button_frame, text="デフォルト", command=self.reset_settings).pack(side="left", padx=5)

    def load_settings(self):
        try:
            config_path = Path(__file__).parent.parent / "config.py"
            with open(config_path, 'r', encoding='utf-8') as f:
                config_content = f.read()

            for key, widget_info in self.setting_widgets.items():
                for line in config_content.split('\n'):
                    if line.strip().startswith(key + " ="):
                        value_part = line.split('=', 1)[1].strip()
                        if '#' in value_part:
                            value_part = value_part.split('#')[0].strip()
                        try:
                            value = ast.literal_eval(value_part)
                            if widget_info['type'] == 'bool':
                                widget_info['var'].set(value)
                            else:
                                widget_info['widget'].delete(0, "end")
                                widget_info['widget'].insert(0, str(value))
                        except:
                            pass
                        break
        except Exception as e:
            messagebox.showerror("エラー", f"設定の読み込みに失敗しました: {e}")

    def save_settings(self):
        try:
            config_path = Path(__file__).parent.parent / "config.py"
            with open(config_path, 'r', encoding='utf-8') as f:
                config_lines = f.readlines()

            for key, widget_info in self.setting_widgets.items():
                if widget_info['type'] == 'bool':
                    value = widget_info['var'].get()
                else:
                    value_str = widget_info['widget'].get()
                    try:
                        if widget_info['type'] == 'int':
                            value = int(value_str)
                        else:
                            value = float(value_str)
                    except ValueError:
                        messagebox.showerror("エラー", f"{key} の値が無効です")
                        return

                for i, line in enumerate(config_lines):
                    if line.strip().startswith(key + " ="):
                        if '#' in line:
                            comment_part = '#' + line.split('#', 1)[1]
                        else:
                            comment_part = ""
                        config_lines[i] = f"{key} = {value}  {comment_part}\n"
                        break

            with open(config_path, 'w', encoding='utf-8') as f:
                f.writelines(config_lines)

            import config as config_module
            importlib.reload(config_module)

            messagebox.showinfo("成功", "設定を保存しました。\n次の操作から反映されます。")
            self.load_settings()
        except Exception as e:
            messagebox.showerror("エラー", f"設定の保存に失敗しました: {e}")

    def reset_settings(self):
        defaults = {
            "MIN_STIMULUS_VALUE": 15,
            "MAX_STIMULUS_VALUE": 70,
            "MIN_GRAB_DURATION": 0.8,
            "MIN_STRETCH_THRESHOLD": 0.03,
            "VIBRATION_ON_STRETCH_THRESHOLD": 0.7,
            "VIBRATION_HYSTERESIS_OFFSET": 0.15,
            "GRAB_START_VIBRATION_INTENSITY": 20,
            "OSC_SEND_INTERVAL": 1.5,
            "SEND_REALTIME_CHATBOX": True,
        }
        for key, value in defaults.items():
            if key in self.setting_widgets:
                if self.setting_widgets[key]['type'] == 'bool':
                    self.setting_widgets[key]['var'].set(value)
                else:
                    self.setting_widgets[key]['widget'].delete(0, "end")
                    self.setting_widgets[key]['widget'].insert(0, str(value))
