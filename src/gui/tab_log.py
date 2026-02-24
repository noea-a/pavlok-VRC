import tkinter as tk
from tkinter import ttk


class LogTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self._create_widgets()

    def _create_widgets(self):
        button_frame = ttk.Frame(self)
        button_frame.pack(fill="x", padx=10, pady=5)
        ttk.Button(button_frame, text="ログをクリア", command=self.clear_log).pack(side="left", padx=5)
        self.autoscroll_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(button_frame, text="自動スクロール", variable=self.autoscroll_var).pack(side="left", padx=5)

        log_frame = ttk.LabelFrame(self, text="アプリケーションログ", padding=5)
        log_frame.pack(fill="both", expand=True, padx=10, pady=10)

        scrollbar = ttk.Scrollbar(log_frame)
        scrollbar.pack(side="right", fill="y")

        self.log_text = tk.Text(log_frame, height=20, width=80, yscrollcommand=scrollbar.set)
        self.log_text.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.log_text.yview)

        self.log_text.tag_config("INFO", foreground="black")
        self.log_text.tag_config("DEBUG", foreground="gray")
        self.log_text.tag_config("WARNING", foreground="orange")
        self.log_text.tag_config("ERROR", foreground="red")
        self.log_text.tag_config("CRITICAL", foreground="darkred", background="yellow")

    def update(self, level: str, message: str):
        try:
            self.log_text.config(state="normal")
            self.log_text.insert("end", message + "\n", level)
            if self.autoscroll_var.get():
                self.log_text.see("end")
            self.log_text.config(state="disabled")
        except Exception as e:
            print(f"Error updating log: {e}")

    def clear_log(self):
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.config(state="disabled")
