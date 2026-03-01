import threading
import time as time_module
import tkinter as tk
from tkinter import ttk

import pavlok_controller as stimulus_controller
import config
from intensity import IntensityConfig, calculate_intensity, normalize_for_display


class TestTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.grab_state = None
        self.test_stretch_var = tk.DoubleVar(value=0.0)
        self._ble_counter = 0
        self._polling = False
        self._last_mode = None  # pack/unpack の不要な再実行を防ぐ

        # スクロール可能なコンテナ
        scrollbar = ttk.Scrollbar(self, orient="vertical")
        scrollbar.pack(side="right", fill="y")
        self._canvas = tk.Canvas(self, yscrollcommand=scrollbar.set, highlightthickness=0)
        self._canvas.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self._canvas.yview)
        self._inner = ttk.Frame(self._canvas)
        self._inner_id = self._canvas.create_window((0, 0), window=self._inner, anchor="nw")
        self._inner.bind("<Configure>", lambda e: self._canvas.configure(
            scrollregion=(0, 0, e.width, e.height)))
        self._canvas.bind("<Configure>", lambda e: self._canvas.itemconfig(self._inner_id, width=e.width))

        self._create_realtime_panel()
        self._create_intensity_preview_panel()
        self._create_unit_test_panel()
        self._create_ble_raw_panel()
        self._create_grab_sim_panel()

    def _on_mousewheel(self, event):
        if isinstance(event.widget, ttk.Spinbox):
            return "break"
        if self._canvas.yview() == (0.0, 1.0):
            return
        self._canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def set_grab_state(self, grab_state):
        self.grab_state = grab_state

    # ------------------------------------------------------------------ #
    # リアルタイム状態パネル                                               #
    # ------------------------------------------------------------------ #

    def _create_realtime_panel(self):
        frame = ttk.LabelFrame(self._inner, text="リアルタイム状態", padding=10)
        frame.pack(fill="x", padx=10, pady=(10, 5))

        # --- 基本状態 ---
        basic = ttk.Frame(frame)
        basic.pack(fill="x")

        # Grab 状態
        row0 = ttk.Frame(basic)
        row0.pack(fill="x", pady=2)
        ttk.Label(row0, text="Grab:", width=16).pack(side="left")
        self._rt_grab_label = ttk.Label(row0, text="—", width=10)
        self._rt_grab_label.pack(side="left")

        # Stretch
        row1 = ttk.Frame(basic)
        row1.pack(fill="x", pady=2)
        ttk.Label(row1, text="Stretch:", width=16).pack(side="left")
        self._rt_stretch_label = ttk.Label(row1, text="—", width=8)
        self._rt_stretch_label.pack(side="left")
        self._rt_stretch_bar = ttk.Progressbar(row1, maximum=100, length=180)
        self._rt_stretch_bar.pack(side="left", padx=6)

        # 計算強度
        row2 = ttk.Frame(basic)
        row2.pack(fill="x", pady=2)
        ttk.Label(row2, text="計算強度:", width=16).pack(side="left")
        self._rt_intensity_label = ttk.Label(
            row2, text="—", width=16, font=("", 11, "bold"), foreground="#0066cc")
        self._rt_intensity_label.pack(side="left")
        self._rt_intensity_bar = ttk.Progressbar(row2, maximum=100, length=180)
        self._rt_intensity_bar.pack(side="left", padx=6)

        # 最終 Zap
        row3 = ttk.Frame(basic)
        row3.pack(fill="x", pady=2)
        ttk.Label(row3, text="最終 Zap:", width=16).pack(side="left")
        self._rt_last_zap_label = ttk.Label(row3, text="—", foreground="#cc3300")
        self._rt_last_zap_label.pack(side="left")

        ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=(8, 4))

        # --- Speed モード詳細（speed モード時のみ表示） ---
        self._speed_detail_frame = ttk.LabelFrame(frame, text="Speed モード詳細", padding=6)
        # pack は _poll_realtime で条件判定して制御

        sg = ttk.Frame(self._speed_detail_frame)
        sg.pack(fill="x")

        self._sd_labels = {}
        rows = [
            ("mode_state",    "状態:"),
            ("origin",        "原点 Stretch:"),
            ("peak",          "Peak Stretch:"),
            ("delta",         "引っ張り量 (delta):"),
            ("recent_speed",  "直近速度 (s/s):"),
            ("history",       "履歴:"),
        ]
        for i, (key, text) in enumerate(rows):
            ttk.Label(sg, text=text, width=18).grid(row=i, column=0, sticky="w", pady=2)
            lbl = ttk.Label(sg, text="—", width=20)
            lbl.grid(row=i, column=1, sticky="w", padx=4, pady=2)
            self._sd_labels[key] = lbl

        # stretch モード詳細
        self._stretch_detail_frame = ttk.LabelFrame(frame, text="Stretch モード詳細", padding=6)

        sh = ttk.Frame(self._stretch_detail_frame)
        sh.pack(fill="x")
        self._sh_labels = {}
        srows = [
            ("min_stretch", "有効 Stretch 最小:"),
            ("max_stretch", "有効 Stretch 最大:"),
            ("min_int",     "強度 最小 (内部値):"),
            ("max_int",     "強度 最大 (内部値):"),
            ("position",    "現在位置:"),
        ]
        for i, (key, text) in enumerate(srows):
            ttk.Label(sh, text=text, width=18).grid(row=i, column=0, sticky="w", pady=2)
            lbl = ttk.Label(sh, text="—", width=20)
            lbl.grid(row=i, column=1, sticky="w", padx=4, pady=2)
            self._sh_labels[key] = lbl

    def enable_scroll(self):
        self._canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        # タブがアクティブになったときにポーリング開始
        if not self._polling:
            self._polling = True
            self._poll_realtime()

    def disable_scroll(self):
        self._canvas.unbind_all("<MouseWheel>")

    def _poll_realtime(self):
        if not self._polling:
            return
        try:
            self._refresh_realtime()
        except Exception:
            pass
        self.after(200, self._poll_realtime)

    def _refresh_realtime(self):
        gs = self.grab_state
        if gs is None:
            return

        import settings as s_mod
        from intensity import IntensityConfig, calculate_intensity, normalize_for_display

        mode = s_mod.settings.device.zap_mode
        cfg = IntensityConfig.from_settings()

        # Grab 状態
        if gs.is_grabbed:
            self._rt_grab_label.config(text="掴み中", foreground="#007700", font=("", 10, "bold"))
        else:
            self._rt_grab_label.config(text="未掴み", foreground="#555555", font=("", 10, ""))

        # Stretch
        stretch = gs.current_stretch
        self._rt_stretch_label.config(text=f"{stretch:.3f}")
        self._rt_stretch_bar["value"] = int(stretch * 100)

        # 計算強度
        if gs.is_grabbed:
            intensity = calculate_intensity(stretch, cfg)
            display = normalize_for_display(intensity, cfg) if intensity > 0 else 0
            if intensity > 0:
                self._rt_intensity_label.config(
                    text=f"内部: {intensity}  /  {display}%", foreground="#0066cc")
            else:
                self._rt_intensity_label.config(text="0 (刺激なし)", foreground="gray")
            self._rt_intensity_bar["value"] = display
        else:
            self._rt_intensity_label.config(text="—", foreground="gray")
            self._rt_intensity_bar["value"] = 0

        # 最終 Zap
        d = gs.last_zap_display_intensity
        a = gs.last_zap_actual_intensity
        if d > 0:
            self._rt_last_zap_label.config(text=f"表示: {d}%  /  内部値: {a}", foreground="#cc3300")
        else:
            self._rt_last_zap_label.config(text="—", foreground="gray")

        # モード別詳細の切り替え（モードが変わったときだけ pack/unpack）
        if mode != self._last_mode:
            if mode == "speed":
                self._stretch_detail_frame.pack_forget()
                self._speed_detail_frame.pack(fill="x")
            else:
                self._speed_detail_frame.pack_forget()
                self._stretch_detail_frame.pack(fill="x")
            self._last_mode = mode

        if mode == "speed":
            self._refresh_speed_detail(gs.speed_mode_state)
        else:
            self._refresh_stretch_detail(stretch, cfg)

    def _refresh_speed_detail(self, state: dict):
        if not state:
            for lbl in self._sd_labels.values():
                lbl.config(text="—", foreground="gray")
            return

        # 状態文字列
        if state.get("zap_fired"):
            state_text = "Zap 済み（pullback 待ち）"
            state_fg = "#cc3300"
        elif state.get("measuring"):
            if state.get("stop_detecting"):
                state_text = "停止検知中"
                state_fg = "#cc6600"
            else:
                state_text = "計測中"
                state_fg = "#007700"
        elif state.get("settled"):
            state_text = "onset 待ち"
            state_fg = "#555555"
        else:
            state_text = "settle 待ち"
            state_fg = "#aaaaaa"

        self._sd_labels["mode_state"].config(text=state_text, foreground=state_fg)
        self._sd_labels["origin"].config(
            text=f"{state.get('origin_stretch', 0):.3f}", foreground="black")
        self._sd_labels["peak"].config(
            text=f"{state.get('peak_stretch', 0):.3f}", foreground="black")
        delta = state.get("delta", 0)
        self._sd_labels["delta"].config(
            text=f"{delta:.3f}  ← 強度計算に使用", foreground="#0055aa")
        spd = state.get("recent_speed", 0)
        spd_fg = "#007700" if spd > 0.5 else "black"
        self._sd_labels["recent_speed"].config(text=f"{spd:.3f}", foreground=spd_fg)
        self._sd_labels["history"].config(
            text=f"{state.get('history_len', 0)} エントリ", foreground="gray")

    def _refresh_stretch_detail(self, stretch: float, cfg):
        from intensity import calculate_intensity, normalize_for_display
        mn_s = cfg.min_stretch_for_calc
        mx_s = cfg.max_stretch_for_calc
        mn_i = calculate_intensity(mn_s, cfg)
        mx_i = calculate_intensity(mx_s, cfg)
        cur_i = calculate_intensity(stretch, cfg)

        self._sh_labels["min_stretch"].config(text=f"{mn_s:.3f}")
        self._sh_labels["max_stretch"].config(text=f"{mx_s:.3f}")
        self._sh_labels["min_int"].config(text=str(mn_i))
        self._sh_labels["max_int"].config(text=str(mx_i))
        if mx_i > mn_i:
            pct = int((cur_i - mn_i) / (mx_i - mn_i) * 100)
            self._sh_labels["position"].config(
                text=f"内部値 {cur_i}  ({pct}%)", foreground="#0066cc")
        else:
            self._sh_labels["position"].config(text=f"内部値 {cur_i}", foreground="black")

    # ------------------------------------------------------------------ #
    # 強度プレビューセクション                                             #
    # ------------------------------------------------------------------ #

    def _create_intensity_preview_panel(self):
        frame = ttk.LabelFrame(self._inner, text="強度プレビュー", padding=10)
        frame.pack(fill="x", padx=10, pady=(10, 5))

        # Stretch スライダー
        s_frame = ttk.Frame(frame)
        s_frame.pack(fill="x", pady=3)
        ttk.Label(s_frame, text="Stretch:", width=18).pack(side="left")
        self._preview_stretch_var = tk.DoubleVar(value=0.5)
        ttk.Scale(s_frame, from_=0.0, to=1.0, orient="horizontal",
                  variable=self._preview_stretch_var,
                  command=lambda _: self._update_intensity_preview()).pack(
            side="left", fill="x", expand=True, padx=5)
        self._preview_stretch_label = ttk.Label(s_frame, text="0.500", width=6)
        self._preview_stretch_label.pack(side="left")

        # 結果表示
        result_frame = ttk.Frame(frame)
        result_frame.pack(fill="x", pady=(8, 2))
        ttk.Label(result_frame, text="計算結果:").pack(side="left")
        self._preview_result_label = ttk.Label(
            result_frame, text="—", font=("", 14, "bold"), foreground="#0066cc")
        self._preview_result_label.pack(side="left", padx=12)
        self._preview_effective_label = ttk.Label(result_frame, text="", foreground="gray")
        self._preview_effective_label.pack(side="left")

        self._update_intensity_preview()

    def _update_intensity_preview(self):
        cfg = IntensityConfig.from_settings()
        stretch = self._preview_stretch_var.get()
        self._preview_stretch_label.config(text=f"{stretch:.3f}")

        intensity = calculate_intensity(stretch, cfg)
        display = normalize_for_display(intensity, cfg) if intensity > 0 else 0

        if intensity == 0:
            self._preview_result_label.config(text="0  (刺激なし)", foreground="gray")
            self._preview_effective_label.config(text="")
        else:
            self._preview_result_label.config(
                text=f"内部値: {intensity}  /  表示: {display}%", foreground="#0066cc")
            self._preview_effective_label.config(text="")

    # ------------------------------------------------------------------ #
    # 単体テストセクション                                                 #
    # ------------------------------------------------------------------ #

    def _create_unit_test_panel(self):
        frame = ttk.LabelFrame(self._inner, text="単体テスト", padding=10)
        frame.pack(fill="x", padx=10, pady=(10, 5))

        vib_frame = ttk.Frame(frame)
        vib_frame.pack(fill="x", pady=4)
        ttk.Label(vib_frame, text="バイブ:", width=15).pack(side="left")
        ttk.Button(vib_frame, text="弱", width=8,
                   command=lambda: self._send_vibration("weak")).pack(side="left", padx=2)
        ttk.Button(vib_frame, text="中", width=8,
                   command=lambda: self._send_vibration("mid")).pack(side="left", padx=2)
        ttk.Button(vib_frame, text="強", width=8,
                   command=lambda: self._send_vibration("strong")).pack(side="left", padx=2)

        zap_frame = ttk.Frame(frame)
        zap_frame.pack(fill="x", pady=4)
        ttk.Label(zap_frame, text="Zap:", width=15).pack(side="left")
        ttk.Button(zap_frame, text="弱", width=8,
                   command=lambda: self._send_zap("weak")).pack(side="left", padx=2)
        ttk.Button(zap_frame, text="中", width=8,
                   command=lambda: self._send_zap("mid")).pack(side="left", padx=2)
        ttk.Button(zap_frame, text="強", width=8,
                   command=lambda: self._send_zap("strong")).pack(side="left", padx=2)

    def _resolve_intensity(self, level: str) -> int:
        mn = config.MIN_STIMULUS_VALUE
        mx = config.MAX_STIMULUS_VALUE
        if level == "weak":
            return mn
        if level == "strong":
            return mx
        return (mn + mx) // 2  # mid

    def _send_vibration(self, level: str):
        intensity = self._resolve_intensity(level)
        threading.Thread(
            target=stimulus_controller.send_vibration,
            args=(intensity,),
            daemon=True,
        ).start()
        print(f"[Unit Test] Vibration {level} ({intensity})")

    def _send_zap(self, level: str):
        intensity = self._resolve_intensity(level)
        threading.Thread(
            target=stimulus_controller.send_zap,
            args=(intensity,),
            daemon=True,
        ).start()
        print(f"[Unit Test] Zap {level} ({intensity})")

    # ------------------------------------------------------------------ #
    # BLE 生コマンド テストセクション                                     #
    # ------------------------------------------------------------------ #

    def _create_ble_raw_panel(self):
        frame = ttk.LabelFrame(self._inner, text="BLE 生コマンド（バイブ）", padding=10)
        frame.pack(fill="x", padx=10, pady=(5, 5))

        # パラメータ説明ラベル
        ttk.Label(frame, text="コマンド: [0x80|counter, mode, intensity, ton, toff]",
                  foreground="gray").pack(anchor="w", pady=(0, 6))

        grid = ttk.Frame(frame)
        grid.pack(fill="x")

        fields = [
            ("counter",   "実行回数 (0-127)",    1,   0, 127),
            ("mode",      "モード（不明）",              2,   0, 255),
            ("intensity", "強度 (0-100)",        50,  0, 100),
            ("ton",       "実行時間",                22,  0, 255),
            ("toff",      "インターバル",               22,  0, 255),
        ]

        self._raw_vars = {}
        for row, (key, label, default, mn, mx) in enumerate(fields):
            ttk.Label(grid, text=label, width=20).grid(row=row, column=0, sticky="w", pady=3)
            var = tk.IntVar(value=default)
            sb = ttk.Spinbox(grid, from_=mn, to=mx, textvariable=var, width=8)
            sb.grid(row=row, column=1, sticky="w", padx=5, pady=3)
            self._raw_vars[key] = var

        # 送信ボタン & 結果表示
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill="x", pady=(4, 0))
        ttk.Button(btn_frame, text="送信", width=10, command=self._send_raw_vibe).pack(side="left", padx=2)
        self._raw_result_label = ttk.Label(btn_frame, text="", foreground="gray")
        self._raw_result_label.pack(side="left", padx=8)

    def _send_raw_vibe(self):
        counter   = self._raw_vars["counter"].get() & 0x7F
        mode      = self._raw_vars["mode"].get()
        intensity = self._raw_vars["intensity"].get()
        ton       = self._raw_vars["ton"].get()
        toff      = self._raw_vars["toff"].get()

        cmd = bytes([0x80 | counter, mode, intensity, ton, toff])
        label_text = f"送信: {list(cmd)}"
        self._raw_result_label.config(text=label_text)
        print(f"[BLE Raw] {label_text}")

        def _send():
            try:
                ok = stimulus_controller.send_raw_vibe(cmd)
                result = "OK" if ok else "FAILED"
            except Exception as e:
                result = f"ERROR: {e}"
            print(f"[BLE Raw] result={result}")
            self._raw_result_label.config(text=f"{label_text}  →  {result}")

        threading.Thread(target=_send, daemon=True).start()

    # ------------------------------------------------------------------ #
    # Grab シミュレーションセクション（tab_dashboard.py から移動）        #
    # ------------------------------------------------------------------ #

    def _create_grab_sim_panel(self):
        frame = ttk.LabelFrame(self._inner, text="掴みシミュレーション", padding=10)
        frame.pack(fill="x", padx=10, pady=(5, 10))

        grab_frame = ttk.Frame(frame)
        grab_frame.pack(fill="x", pady=4)
        ttk.Label(grab_frame, text="掴み状態:", width=15).pack(side="left")
        ttk.Button(grab_frame, text="掴み開始", command=self.test_grab_start, width=10).pack(side="left", padx=2)
        ttk.Button(grab_frame, text="掴み終了", command=self.test_grab_end, width=10).pack(side="left", padx=2)

        stretch_frame = ttk.Frame(frame)
        stretch_frame.pack(fill="x", pady=4)
        ttk.Label(stretch_frame, text="引っ張り度:", width=15).pack(side="left")
        self.test_stretch_slider = ttk.Scale(
            stretch_frame, from_=0.0, to=1.0, orient="horizontal",
            variable=self.test_stretch_var, command=self.on_test_stretch_change,
        )
        self.test_stretch_slider.pack(side="left", fill="x", expand=True, padx=5)
        self.test_stretch_label = ttk.Label(stretch_frame, text="0.000", width=6)
        self.test_stretch_label.pack(side="left")

        quick_frame = ttk.Frame(frame)
        quick_frame.pack(fill="x", pady=4)
        ttk.Label(quick_frame, text="クイックテスト:", width=15).pack(side="left")
        ttk.Button(quick_frame, text="弱", width=8,
                   command=lambda: self.test_grab_sequence(0.3, 1.5)).pack(side="left", padx=2)
        ttk.Button(quick_frame, text="中", width=8,
                   command=lambda: self.test_grab_sequence(0.6, 2.0)).pack(side="left", padx=2)
        ttk.Button(quick_frame, text="強", width=8,
                   command=lambda: self.test_grab_sequence(0.9, 2.5)).pack(side="left", padx=2)

    def test_grab_start(self):
        self.test_stretch_var.set(0.0)
        self.test_stretch_label.config(text="0.000")
        if self.grab_state:
            self.grab_state.is_test_mode = True
            self.grab_state.on_grabbed_change(True)
        print("[Test Send] Grab Start")

    def test_grab_end(self):
        stretch = self.test_stretch_var.get()
        if self.grab_state:
            self.grab_state.on_grabbed_change(False)
            self.grab_state.is_test_mode = False
        self.test_stretch_var.set(0.0)
        self.test_stretch_label.config(text="0.000")
        print(f"[Test Send] Grab End (Final Stretch: {stretch:.3f})")

    def on_test_stretch_change(self, value):
        stretch = float(value)
        self.test_stretch_label.config(text=f"{stretch:.3f}")
        if self.grab_state and self.grab_state.is_grabbed:
            self.grab_state.on_stretch_change(stretch)

    def test_grab_sequence(self, max_stretch: float, duration: float):
        def sequence():
            if self.grab_state:
                self.grab_state.is_test_mode = True
            self.test_grab_start()
            time_module.sleep(0.1)
            steps = 20
            for i in range(steps + 1):
                stretch = (max_stretch / steps) * i
                self.test_stretch_var.set(stretch)
                self.on_test_stretch_change(stretch)
                time_module.sleep(duration / steps)
            self.test_grab_end()
            if self.grab_state:
                self.grab_state.is_test_mode = False
            print(f"[Test Complete] max_stretch={max_stretch:.1f}, duration={duration:.1f}s")

        threading.Thread(target=sequence, daemon=True).start()
