import tkinter as tk
from tkinter import ttk, messagebox
import threading
import logging
from queue import Queue, Empty
from datetime import datetime
import ast
import importlib
from pathlib import Path
from pavlok_controller import normalize_intensity_for_display

# ===== ログハンドラ =====
class QueueHandler(logging.Handler):
    """ログメッセージをキューに送信するカスタムハンドラ"""
    def __init__(self, queue):
        super().__init__()
        self.queue = queue

    def emit(self, record):
        try:
            msg = self.format(record)
            self.queue.put((record.levelname, msg))
        except Exception:
            pass


# ===== GUI メイン =====
class PavlokGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("VRChat Pavlok Connector - Dashboard")
        self.geometry("800x600")

        # データ共有用キュー
        self.status_queue = Queue()
        self.log_queue = Queue()

        # GrabState オブジェクト（main.py から設定される）
        self.grab_state = None

        # GUI 状態
        self.is_running = True

        # ===== ツールバー =====
        menu_bar = tk.Menu(self)
        self.config(menu=menu_bar)

        # ファイルメニュー
        file_menu = tk.Menu(menu_bar, tearoff=False)
        menu_bar.add_cascade(label="ファイル", menu=file_menu)
        file_menu.add_command(label="終了", command=self.on_close)

        # ヘルプメニュー
        help_menu = tk.Menu(menu_bar, tearoff=False)
        menu_bar.add_cascade(label="ヘルプ", menu=help_menu)
        help_menu.add_command(label="バージョン", command=self.show_about)

        # ===== タブ UI =====
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=5, pady=5)

        # ダッシュボード タブ
        self.dashboard_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.dashboard_frame, text="ダッシュボード")
        self._create_dashboard_tab()

        # 設定 タブ
        self.settings_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.settings_frame, text="設定")
        self._create_settings_tab()

        # ログ タブ
        self.log_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.log_frame, text="ログ")
        self._create_log_tab()

        # 統計 タブ
        self.stats_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.stats_frame, text="統計")
        self._create_stats_tab()

        # クローズボタンハンドラ
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        # ポーリングループ開始
        self.poll_data()

    def _create_dashboard_tab(self):
        """ダッシュボード タブ作成"""
        frame = ttk.LabelFrame(self.dashboard_frame, text="リアルタイム状態", padding=10)
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

        # Grab状態テスト
        grab_test_frame = ttk.Frame(test_frame)
        grab_test_frame.pack(fill="x", pady=5)
        ttk.Label(grab_test_frame, text="Grab状態:", width=15).pack(side="left")
        ttk.Button(grab_test_frame, text="Grab開始", command=self.test_grab_start, width=10).pack(side="left", padx=2)
        ttk.Button(grab_test_frame, text="Grab終了", command=self.test_grab_end, width=10).pack(side="left", padx=2)

        # Stretch値テスト
        stretch_test_frame = ttk.Frame(test_frame)
        stretch_test_frame.pack(fill="x", pady=5)
        ttk.Label(stretch_test_frame, text="Stretch値:", width=15).pack(side="left")
        self.test_stretch_var = tk.DoubleVar(value=0.0)
        self.test_stretch_slider = ttk.Scale(stretch_test_frame, from_=0.0, to=1.0, orient="horizontal",
                                              variable=self.test_stretch_var, command=self.on_test_stretch_change)
        self.test_stretch_slider.pack(side="left", fill="x", expand=True, padx=5)
        self.test_stretch_label = ttk.Label(stretch_test_frame, text="0.000", width=6)
        self.test_stretch_label.pack(side="left")

        # クイックテストボタン
        quick_test_frame = ttk.Frame(test_frame)
        quick_test_frame.pack(fill="x", pady=5)
        ttk.Label(quick_test_frame, text="クイックテスト:", width=15).pack(side="left")
        ttk.Button(quick_test_frame, text="弱い掴み", command=lambda: self.test_grab_sequence(0.3, 1.5), width=12).pack(side="left", padx=2)
        ttk.Button(quick_test_frame, text="中くらい", command=lambda: self.test_grab_sequence(0.6, 2.0), width=12).pack(side="left", padx=2)
        ttk.Button(quick_test_frame, text="強い掴み", command=lambda: self.test_grab_sequence(0.9, 2.5), width=12).pack(side="left", padx=2)

    def _create_settings_tab(self):
        """設定 タブ作成"""
        settings_frame = ttk.LabelFrame(self.settings_frame, text="パラメータ設定", padding=15)
        settings_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # 設定項目を定義
        self.setting_widgets = {}

        setting_items = [
            ("MIN_STIMULUS_VALUE", "Zapの最小値", "int", 15, 0, 100),
            ("MAX_STIMULUS_VALUE", "Zapの最大値", "int", 70, 0, 100),
            ("MIN_GRAB_DURATION", "グラブ時間（秒）", "float", 0.8, 0.1, 10.0),
            ("MIN_STRETCH_THRESHOLD", "Stretchの最小閾値", "float", 0.03, 0.0, 1.0),
            ("VIBRATION_ON_STRETCH_THRESHOLD", "高出力の警告（バイブ）", "float", 0.7, 0.0, 1.0),
            ("VIBRATION_HYSTERESIS_OFFSET", "ヒステリシス幅（オフセット）", "float", 0.15, 0.0, 1.0),
            ("GRAB_START_VIBRATION_INTENSITY", "グラブ開始強度", "int", 20, 0, 100),
            ("OSC_SEND_INTERVAL", "OSC送信間隔（秒）", "float", 1.5, 0.0, 10.0),
        ]

        for setting_key, label_text, value_type, default_val, min_val, max_val in setting_items:
            # ラベル
            ttk.Label(settings_frame, text=label_text, width=25).grid(row=len(self.setting_widgets), column=0, sticky="w", pady=5)

            # Spinbox
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

        # ボタンフレーム
        button_frame = ttk.Frame(settings_frame)
        button_frame.grid(row=len(self.setting_widgets), column=0, columnspan=2, pady=15)

        ttk.Button(button_frame, text="保存", command=self.save_settings).pack(side="left", padx=5)
        ttk.Button(button_frame, text="キャンセル", command=self.load_settings).pack(side="left", padx=5)
        ttk.Button(button_frame, text="デフォルト", command=self.reset_settings).pack(side="left", padx=5)

        # 初期値を読み込み
        self.load_settings()

    def _create_log_tab(self):
        """ログ タブ作成"""
        button_frame = ttk.Frame(self.log_frame)
        button_frame.pack(fill="x", padx=10, pady=5)

        ttk.Button(button_frame, text="ログをクリア", command=self.clear_log).pack(side="left", padx=5)
        self.autoscroll_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(button_frame, text="自動スクロール", variable=self.autoscroll_var).pack(side="left", padx=5)

        # ログテキストウィジェット
        log_frame = ttk.LabelFrame(self.log_frame, text="アプリケーションログ", padding=5)
        log_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # スクロールバー付き
        scrollbar = ttk.Scrollbar(log_frame)
        scrollbar.pack(side="right", fill="y")

        self.log_text = tk.Text(log_frame, height=20, width=80, yscrollcommand=scrollbar.set)
        self.log_text.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.log_text.yview)

        # テキストタグの設定
        self.log_text.tag_config("INFO", foreground="black")
        self.log_text.tag_config("DEBUG", foreground="gray")
        self.log_text.tag_config("WARNING", foreground="orange")
        self.log_text.tag_config("ERROR", foreground="red")
        self.log_text.tag_config("CRITICAL", foreground="darkred", background="yellow")

    def _create_stats_tab(self):
        """統計 タブ作成"""
        stats_frame = ttk.LabelFrame(self.stats_frame, text="Zap 実行統計", padding=15)
        stats_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # セッション統計
        session_frame = ttk.LabelFrame(stats_frame, text="このセッション", padding=10)
        session_frame.pack(fill="x", pady=10)
        self.session_stats_text = tk.Text(session_frame, height=6, width=60, state="disabled")
        self.session_stats_text.pack(fill="both", expand=True)

        # 総計統計
        total_frame = ttk.LabelFrame(stats_frame, text="総計（保存済みデータ）", padding=10)
        total_frame.pack(fill="x", pady=10)
        self.total_stats_text = tk.Text(total_frame, height=6, width=60, state="disabled")
        self.total_stats_text.pack(fill="both", expand=True)

        # ボタン
        button_frame = ttk.Frame(stats_frame)
        button_frame.pack(fill="x", pady=10)
        ttk.Button(button_frame, text="統計を更新", command=self.update_stats).pack(side="left", padx=5)
        ttk.Button(button_frame, text="記録をリセット", command=self.reset_stats).pack(side="left", padx=5)

        # 初期表示
        self.update_stats()

    def poll_data(self):
        """状態とログデータをポーリング（1秒毎）"""
        try:
            # ステータス更新を受け取り
            while True:
                try:
                    data = self.status_queue.get_nowait()
                    self.update_dashboard(data)
                except Empty:
                    break

            # ログメッセージを受け取り
            while True:
                try:
                    level, message = self.log_queue.get_nowait()
                    self.update_log(level, message)
                except Empty:
                    break

            # 統計情報を定期更新
            self.update_stats()
        except Exception as e:
            print(f"Error in poll_data: {e}")

        # 1秒後に再度ポーリング
        if self.is_running:
            self.after(1000, self.poll_data)

    def update_dashboard(self, data):
        """ダッシュボード更新"""
        try:
            is_grabbed = data.get('is_grabbed', False)
            stretch = data.get('stretch', 0.0)
            intensity = data.get('intensity', 0)
            last_zap_display = data.get('last_zap_display_intensity', 0)
            last_zap_actual = data.get('last_zap_actual_intensity', 0)

            # Grab 状態
            if is_grabbed:
                self.grab_status_label.config(text="True", foreground="red")
            else:
                self.grab_status_label.config(text="False", foreground="blue")

            # Stretch 値
            self.stretch_slider.set(stretch)
            self.stretch_label.config(text=f"{stretch:.3f}")

            # 計算強度（Chatbox 表示値と同じロジック：15～70 を 20～100 に正規化）
            if intensity == 0:
                intensity_percent = 0
            else:
                intensity_percent = normalize_intensity_for_display(intensity)
            self.intensity_progressbar['value'] = intensity_percent
            self.intensity_label.config(text=f"{intensity_percent}%")

            # 詳細情報
            self.detail_text.config(state="normal")
            self.detail_text.delete("1.0", "end")
            detail_info = f"時刻: {datetime.now().strftime('%H:%M:%S')}\n"
            detail_info += f"計算強度: {intensity_percent}% (表示値) / {intensity} (内部値)\n"
            if last_zap_display > 0:
                detail_info += f"最終Zap: {last_zap_display}% (内部値: {last_zap_actual})\n"
            else:
                detail_info += f"最終Zap: なし\n"
            self.detail_text.insert("1.0", detail_info)
            self.detail_text.config(state="disabled")
        except Exception as e:
            print(f"Error updating dashboard: {e}")

    def update_log(self, level, message):
        """ログ更新"""
        try:
            self.log_text.config(state="normal")
            self.log_text.insert("end", message + "\n", level)

            # 自動スクロール
            if self.autoscroll_var.get():
                self.log_text.see("end")

            self.log_text.config(state="disabled")
        except Exception as e:
            print(f"Error updating log: {e}")

    def clear_log(self):
        """ログクリア"""
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.config(state="disabled")

    def load_settings(self):
        """config.py から設定値を読み込み"""
        try:
            config_path = Path(__file__).parent / "config.py"
            with open(config_path, 'r', encoding='utf-8') as f:
                config_content = f.read()

            # 設定値を解析
            for key, widget_info in self.setting_widgets.items():
                # config.py から該当行を探す
                for line in config_content.split('\n'):
                    if line.strip().startswith(key + " ="):
                        # 値を抽出
                        value_part = line.split('=', 1)[1].strip()
                        # コメントを削除
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
        """設定値を config.py に保存"""
        try:
            config_path = Path(__file__).parent / "config.py"

            # config.py を読み込み
            with open(config_path, 'r', encoding='utf-8') as f:
                config_lines = f.readlines()

            # 新しい設定値を反映
            for key, widget_info in self.setting_widgets.items():
                # 値を取得
                if widget_info['type'] == 'bool':
                    value = widget_info['var'].get()
                else:
                    value_str = widget_info['widget'].get()
                    # 型変換
                    try:
                        if widget_info['type'] == 'int':
                            value = int(value_str)
                        else:
                            value = float(value_str)
                    except ValueError:
                        messagebox.showerror("エラー", f"{key} の値が無効です")
                        return

                # config.py の該当行を更新
                for i, line in enumerate(config_lines):
                    if line.strip().startswith(key + " ="):
                        # コメント部分を保持
                        if '#' in line:
                            comment_part = '#' + line.split('#', 1)[1]
                        else:
                            comment_part = ""

                        config_lines[i] = f"{key} = {value}  {comment_part}\n"
                        break

            # ファイルに書き込み
            with open(config_path, 'w', encoding='utf-8') as f:
                f.writelines(config_lines)

            # config モジュールをリロード
            import config as config_module
            importlib.reload(config_module)

            messagebox.showinfo("成功", "設定を保存しました。\n次の操作から反映されます。")
            self.load_settings()
        except Exception as e:
            messagebox.showerror("エラー", f"設定の保存に失敗しました: {e}")

    def reset_settings(self):
        """デフォルト値にリセット"""
        defaults = {
            "MIN_STIMULUS_VALUE": 15,
            "MAX_STIMULUS_VALUE": 70,
            "MIN_GRAB_DURATION": 0.8,
            "MIN_STRETCH_THRESHOLD": 0.07,
            "VIBRATION_ON_STRETCH_THRESHOLD": 0.7,
            "VIBRATION_HYSTERESIS_OFFSET": 0.15,
            "GRAB_START_VIBRATION_INTENSITY": 20,
            "OSC_SEND_INTERVAL": 0.3,
            "SEND_REALTIME_CHATBOX": False,
        }

        for key, value in defaults.items():
            if key in self.setting_widgets:
                if self.setting_widgets[key]['type'] == 'bool':
                    self.setting_widgets[key]['var'].set(value)
                else:
                    self.setting_widgets[key]['widget'].delete(0, "end")
                    self.setting_widgets[key]['widget'].insert(0, str(value))

    def test_grab_start(self):
        """テスト: Grab 開始を送信"""
        # Stretch を 0 にリセット
        self.test_stretch_var.set(0.0)
        self.test_stretch_label.config(text="0.000")

        # GrabState のコールバックを呼び出し（OSC メッセージ送信）
        if self.grab_state:
            self.grab_state.is_test_mode = True
            self.grab_state.on_grabbed_change(True)
        print("🧪 テスト送信: Grab開始")

    def test_grab_end(self):
        """テスト: Grab 終了を送信"""
        # 現在の Stretch 値を取得
        stretch = self.test_stretch_var.get()

        # GrabState のコールバックを呼び出し（OSC メッセージ送信）
        if self.grab_state:
            self.grab_state.on_grabbed_change(False)
            self.grab_state.is_test_mode = False

        # Stretch を 0 にリセット
        self.test_stretch_var.set(0.0)
        self.test_stretch_label.config(text="0.000")

        print(f"🧪 テスト送信: Grab終了 (最終Stretch: {stretch:.3f})")

    def on_test_stretch_change(self, value):
        """テスト: Stretch 値を変更"""
        stretch = float(value)
        self.test_stretch_label.config(text=f"{stretch:.3f}")

        # Grab 中の場合のみ Stretch を送信
        if self.grab_status_label.cget("text") == "True":
            # GrabState のコールバックを呼び出し（OSC メッセージ送信）
            if self.grab_state:
                self.grab_state.on_stretch_change(stretch)

    def test_grab_sequence(self, max_stretch, duration):
        """テスト: Grab シーケンス（自動テスト）"""
        import threading
        import time as time_module

        def sequence():
            # テストモード開始
            if self.grab_state:
                self.grab_state.is_test_mode = True

            # Grab 開始
            self.test_grab_start()
            time_module.sleep(0.1)

            # Stretch を段階的に上げる
            steps = 20
            for i in range(steps + 1):
                stretch = (max_stretch / steps) * i
                self.test_stretch_var.set(stretch)
                self.on_test_stretch_change(stretch)
                time_module.sleep(duration / steps)

            # Grab 終了
            self.test_grab_end()

            # テストモード終了
            if self.grab_state:
                self.grab_state.is_test_mode = False

            print(f"✅ テスト完了: max_stretch={max_stretch:.1f}, duration={duration:.1f}s")

        # バックグラウンドスレッドで実行
        thread = threading.Thread(target=sequence, daemon=True)
        thread.start()

    def update_stats(self):
        """統計情報を更新表示"""
        if hasattr(self, 'grab_state') and self.grab_state:
            try:
                session_stats = self.grab_state.zap_recorder.get_session_stats()
                total_stats = self.grab_state.zap_recorder.get_total_stats()

                # セッション統計表示
                session_text = f"""Zap 数:           {session_stats['total_zaps']}
平均強度:         {session_stats['avg_display_intensity']:.1f} %
平均強度（実値）: {session_stats['avg_actual_intensity']:.0f}
最大強度:         {session_stats['max_display_intensity']} %
最大強度（実値）: {session_stats['max_actual_intensity']}
        """
                self.session_stats_text.config(state="normal")
                self.session_stats_text.delete("1.0", "end")
                self.session_stats_text.insert("1.0", session_text)
                self.session_stats_text.config(state="disabled")

                # 総計統計表示
                total_text = f"""セッション平均:       {total_stats['session_avg_zaps']:.1f} 回/セッション
Zap 数:               {total_stats['total_zaps']}
平均強度:             {total_stats['avg_display_intensity']:.1f} %
平均強度（実値）:     {total_stats['avg_actual_intensity']:.0f}
最大強度:             {total_stats['max_display_intensity']} %
最大強度（実値）:     {total_stats['max_actual_intensity']}
        """
                self.total_stats_text.config(state="normal")
                self.total_stats_text.delete("1.0", "end")
                self.total_stats_text.insert("1.0", total_text)
                self.total_stats_text.config(state="disabled")
            except Exception as e:
                print(f"Error updating stats: {e}")

    def reset_stats(self):
        """記録をリセット"""
        if messagebox.askyesno("確認", "すべての Zap 記録を削除してもいいですか？"):
            if hasattr(self, 'grab_state') and self.grab_state:
                self.grab_state.zap_recorder.reset_records()
                self.update_stats()

    def show_about(self):
        """バージョン情報を表示"""
        messagebox.showinfo("バージョン情報", "VRChat Pavlok Connector\nGUI Dashboard v1.1")

    def on_close(self):
        """アプリケーション終了"""
        self.is_running = False
        self.destroy()

    def run(self):
        """GUI メインループ"""
        self.mainloop()


if __name__ == "__main__":
    gui = PavlokGUI()
    gui.run()
