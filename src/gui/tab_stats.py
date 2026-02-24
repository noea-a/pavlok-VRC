import tkinter as tk
from tkinter import ttk, messagebox


class StatsTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.grab_state = None
        self._create_widgets()

    def set_grab_state(self, grab_state):
        self.grab_state = grab_state

    def _create_widgets(self):
        stats_frame = ttk.LabelFrame(self, text="Zap 実行統計", padding=15)
        stats_frame.pack(fill="both", expand=True, padx=10, pady=10)

        session_frame = ttk.LabelFrame(stats_frame, text="このセッション", padding=10)
        session_frame.pack(fill="x", pady=10)
        self.session_stats_text = tk.Text(session_frame, height=6, width=60, state="disabled")
        self.session_stats_text.pack(fill="both", expand=True)

        total_frame = ttk.LabelFrame(stats_frame, text="総計（保存済みデータ）", padding=10)
        total_frame.pack(fill="x", pady=10)
        self.total_stats_text = tk.Text(total_frame, height=6, width=60, state="disabled")
        self.total_stats_text.pack(fill="both", expand=True)

        button_frame = ttk.Frame(stats_frame)
        button_frame.pack(fill="x", pady=10)
        ttk.Button(button_frame, text="統計を更新", command=self.update).pack(side="left", padx=5)
        ttk.Button(button_frame, text="記録をリセット", command=self.reset_stats).pack(side="left", padx=5)

    def update(self, data: dict = None):
        if not self.grab_state:
            return
        try:
            session_stats = self.grab_state.zap_recorder.get_session_stats()
            total_stats = self.grab_state.zap_recorder.get_total_stats()

            session_text = (
                f"Zap 数:           {session_stats['total_zaps']}\n"
                f"平均強度:         {session_stats['avg_display_intensity']:.1f} %\n"
                f"平均強度（実値）: {session_stats['avg_actual_intensity']:.0f}\n"
                f"最大強度:         {session_stats['max_display_intensity']} %\n"
                f"最大強度（実値）: {session_stats['max_actual_intensity']}\n"
            )
            self.session_stats_text.config(state="normal")
            self.session_stats_text.delete("1.0", "end")
            self.session_stats_text.insert("1.0", session_text)
            self.session_stats_text.config(state="disabled")

            total_text = (
                f"セッション平均:       {total_stats['session_avg_zaps']:.1f} 回/セッション\n"
                f"Zap 数:               {total_stats['total_zaps']}\n"
                f"平均強度:             {total_stats['avg_display_intensity']:.1f} %\n"
                f"平均強度（実値）:     {total_stats['avg_actual_intensity']:.0f}\n"
                f"最大強度:             {total_stats['max_display_intensity']} %\n"
                f"最大強度（実値）:     {total_stats['max_actual_intensity']}\n"
            )
            self.total_stats_text.config(state="normal")
            self.total_stats_text.delete("1.0", "end")
            self.total_stats_text.insert("1.0", total_text)
            self.total_stats_text.config(state="disabled")
        except Exception as e:
            print(f"Error updating stats: {e}")

    def reset_stats(self):
        if messagebox.askyesno("確認", "すべての Zap 記録を削除してもいいですか？"):
            if self.grab_state:
                self.grab_state.zap_recorder.reset_records()
                self.update()
