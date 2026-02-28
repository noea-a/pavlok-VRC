import tkinter as tk
from tkinter import ttk, messagebox
import logging
from queue import Queue, Empty

from version import __version__
from gui.tab_dashboard import DashboardTab
from gui.tab_settings import SettingsTab
from gui.tab_log import LogTab
from gui.tab_stats import StatsTab
from gui.tab_test import TestTab


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


class PavlokGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"VRChat Pavlok Connector v{__version__}")
        self.geometry("800x600")

        self.status_queue = Queue()
        self.log_queue = Queue()
        self._grab_state = None
        self.is_running = True

        # メニューバー
        menu_bar = tk.Menu(self)
        self.config(menu=menu_bar)
        file_menu = tk.Menu(menu_bar, tearoff=False)
        menu_bar.add_cascade(label="ファイル", menu=file_menu)
        file_menu.add_command(label="終了", command=self.on_close)
        help_menu = tk.Menu(menu_bar, tearoff=False)
        menu_bar.add_cascade(label="ヘルプ", menu=help_menu)
        help_menu.add_command(label="バージョン", command=self.show_about)

        # タブ
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=5, pady=5)

        self.tab_dashboard = DashboardTab(self.notebook)
        self.notebook.add(self.tab_dashboard, text="ダッシュボード")

        self.tab_settings = SettingsTab(self.notebook)
        self.notebook.add(self.tab_settings, text="設定")

        self.tab_log = LogTab(self.notebook)
        self.notebook.add(self.tab_log, text="ログ")

        self.tab_stats = StatsTab(self.notebook)
        self.notebook.add(self.tab_stats, text="統計")

        self.tab_test = TestTab(self.notebook)
        self.notebook.add(self.tab_test, text="テスト")

        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.poll_data()

    @property
    def grab_state(self):
        return self._grab_state

    @grab_state.setter
    def grab_state(self, value):
        self._grab_state = value
        if hasattr(self, 'tab_dashboard'):
            self.tab_dashboard.set_grab_state(value)
        if hasattr(self, 'tab_stats'):
            self.tab_stats.set_grab_state(value)
        if hasattr(self, 'tab_test'):
            self.tab_test.set_grab_state(value)

    def set_device(self, device):
        if hasattr(self, 'tab_dashboard'):
            self.tab_dashboard.set_device(device)

    def poll_data(self):
        try:
            while True:
                try:
                    data = self.status_queue.get_nowait()
                    self.tab_dashboard.update(data)
                except Empty:
                    break

            while True:
                try:
                    level, message = self.log_queue.get_nowait()
                    self.tab_log.update(level, message)
                except Empty:
                    break

            self.tab_stats.update()
        except Exception as e:
            print(f"Error in poll_data: {e}")

        if self.is_running:
            self.after(1000, self.poll_data)

    def show_about(self):
        messagebox.showinfo("バージョン情報", f"VRChat Pavlok Connector\nv{__version__}\n\n🎮 VRChatのPhysBoneを\nPavlokデバイスへ刺激送信\n\n📝 Zap実行記録・統計機能搭載")

    def on_close(self):
        self.is_running = False
        self.destroy()

    def run(self):
        self.mainloop()
