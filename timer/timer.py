import tkinter as tk
import time
import winsound
import math

# ═══════════════════════════════════════════════════════════════════════════════
#  全局配置
# ═══════════════════════════════════════════════════════════════════════════════

COLORS = {
    "bg": "#1e1e2e",
    "fg": "#cdd6f4",
    "accent": "#f5c2e7",
    "countdown": "#f38ba8",
    "stopwatch": "#89b4fa",
    "dark_card": "#181825",
    "border": "#313244",
    "subtext": "#6c7086",
    "success": "#a6e3a1",
    "warn": "#f9e2af",
    "red": "#f38ba8",
}

# ═══════════════════════════════════════════════════════════════════════════════
#  音效
# ═══════════════════════════════════════════════════════════════════════════════

def play_alarm():
    for _ in range(5):
        winsound.Beep(880, 150)
        time.sleep(0.1)
    winsound.Beep(660, 400)

# ═══════════════════════════════════════════════════════════════════════════════
#  主应用
# ═══════════════════════════════════════════════════════════════════════════════

class TimerApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("计时器")
        self.root.geometry("480x620+350+80")
        self.root.configure(bg=COLORS["bg"])
        self.root.resizable(False, False)

        # ── 状态 ──
        self.mode = "countdown"      # countdown | stopwatch
        self.running = False
        self._timer_id = None
        self._start_ts = None

        # 倒计时
        self.cd_hours = 0
        self.cd_minutes = 0
        self.cd_seconds = 0
        self.cd_total = 0            # 设定的总秒数
        self.cd_remaining = 0        # 剩余秒数

        # 秒表
        self.sw_elapsed = 0.0        # 已过秒数（浮点）
        self.laps = []               # 计次记录

        self._build_ui()
        self._show_countdown()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  UI
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _build_ui(self):
        # ── 标题 ──
        header = tk.Frame(self.root, bg=COLORS["bg"])
        header.pack(fill="x", padx=20, pady=(16, 0))
        tk.Label(header, text="⏱  计时器", font=("Segoe UI", 18, "bold"),
                 bg=COLORS["bg"], fg=COLORS["fg"]).pack(side="left")

        # ── 模式标签 ──
        tab_frame = tk.Frame(self.root, bg=COLORS["bg"])
        tab_frame.pack(pady=(14, 0))

        self.tabs = {}
        for key, label, color in [("countdown", "倒计时", COLORS["countdown"]),
                                   ("stopwatch", "秒表", COLORS["stopwatch"])]:
            lbl = tk.Label(tab_frame, text=label, font=("Segoe UI", 12, "bold"),
                           bg=COLORS["dark_card"], fg=COLORS["subtext"],
                           padx=24, pady=8, cursor="hand2")
            lbl.pack(side="left", padx=6)
            lbl.bind("<Button-1>", lambda e, k=key, c=color: self._switch_mode(k, c))
            lbl._active_color = color
            self.tabs[key] = lbl

        # ── 内容容器（倒计时 / 秒表 共用） ──
        self.content = tk.Frame(self.root, bg=COLORS["bg"])
        self.content.pack(fill="both", expand=True, padx=20, pady=(12, 0))

        # ═══ 倒计时界面 ═══
        self.cd_frame = tk.Frame(self.content, bg=COLORS["bg"])

        # 时间输入
        input_frame = tk.Frame(self.cd_frame, bg=COLORS["bg"])
        input_frame.pack(pady=(20, 0))

        self.cd_h_spin = self._make_spin(input_frame, 0, 99, 0)
        tk.Label(input_frame, text=":", font=("Segoe UI", 24, "bold"),
                 bg=COLORS["bg"], fg=COLORS["subtext"]).pack(side="left", padx=2)
        self.cd_m_spin = self._make_spin(input_frame, 0, 59, 5)
        tk.Label(input_frame, text=":", font=("Segoe UI", 24, "bold"),
                 bg=COLORS["bg"], fg=COLORS["subtext"]).pack(side="left", padx=2)
        self.cd_s_spin = self._make_spin(input_frame, 0, 59, 0)

        # 单位标注
        unit_frame = tk.Frame(self.cd_frame, bg=COLORS["bg"])
        unit_frame.pack()
        for txt in ["时", "分", "秒"]:
            tk.Label(unit_frame, text=txt, font=("Segoe UI", 10),
                     bg=COLORS["bg"], fg=COLORS["subtext"],
                     width=4).pack(side="left", padx=2)

        # 倒计时大数字显示
        self.cd_display = tk.Label(self.cd_frame, text="00:00:00",
                                   font=("Segoe UI", 56, "bold"),
                                   bg=COLORS["bg"], fg=COLORS["countdown"])
        self.cd_display.pack(pady=(24, 0))

        # 进度条（canvas）
        self.cd_canvas = tk.Canvas(self.cd_frame, width=400, height=12,
                                   bg=COLORS["dark_card"], highlightthickness=0)
        self.cd_canvas.pack(pady=(12, 0))
        self.cd_bar_bg = self.cd_canvas.create_rectangle(
            0, 0, 400, 12, fill=COLORS["dark_card"], outline="")
        self.cd_bar = self.cd_canvas.create_rectangle(
            0, 0, 400, 12, fill=COLORS["countdown"], outline="")

        # 倒计时按钮
        cd_btn_frame = tk.Frame(self.cd_frame, bg=COLORS["bg"])
        cd_btn_frame.pack(pady=(16, 0))
        self.cd_start_btn = self._mkbtn(cd_btn_frame, "▶  开始", COLORS["success"],
                                         self._cd_toggle)
        self.cd_reset_btn = self._mkbtn(cd_btn_frame, "⟳  重置", COLORS["subtext"],
                                         self._cd_reset)

        # ═══ 秒表界面 ═══
        self.sw_frame = tk.Frame(self.content, bg=COLORS["bg"])

        # 秒表大数字
        self.sw_display = tk.Label(self.sw_frame, text="00:00:00.00",
                                   font=("Segoe UI", 50, "bold"),
                                   bg=COLORS["bg"], fg=COLORS["stopwatch"])
        self.sw_display.pack(pady=(40, 0))

        # 秒表按钮
        sw_btn_frame = tk.Frame(self.sw_frame, bg=COLORS["bg"])
        sw_btn_frame.pack(pady=(16, 0))
        self.sw_start_btn = self._mkbtn(sw_btn_frame, "▶  开始", COLORS["success"],
                                         self._sw_toggle)
        self.sw_lap_btn = self._mkbtn(sw_btn_frame, "⏱  计次", COLORS["warn"],
                                       self._sw_lap)
        self.sw_reset_btn = self._mkbtn(sw_btn_frame, "⟳  重置", COLORS["subtext"],
                                         self._sw_reset)

        # 计次列表
        lap_frame = tk.Frame(self.sw_frame, bg=COLORS["dark_card"],
                             highlightbackground=COLORS["border"],
                             highlightthickness=1, relief="flat")
        lap_frame.pack(fill="both", expand=True, pady=(12, 0), padx=10)

        self.lap_listbox = tk.Listbox(lap_frame, bg=COLORS["dark_card"],
                                       fg=COLORS["fg"], font=("Consolas", 10),
                                       selectbackground=COLORS["border"],
                                       borderwidth=0, highlightthickness=0)
        self.lap_listbox.pack(fill="both", expand=True, padx=4, pady=4)

        # 给秒表按钮初始禁用计次按钮
        self.sw_lap_btn.configure(fg=COLORS["subtext"])

    def _make_spin(self, parent, fr, to, default):
        v = tk.StringVar(value=f"{default:02d}")
        spin = tk.Spinbox(parent, from_=fr, to=to, textvariable=v,
                          width=3, font=("Segoe UI", 22, "bold"),
                          justify="center", bd=0,
                          bg=COLORS["dark_card"], fg=COLORS["fg"],
                          buttonbackground=COLORS["border"],
                          highlightthickness=0)
        spin.pack(side="left", padx=2)
        # 格式化为两位数
        def _fmt(*_):
            try:
                val = int(spin.get())
                v.set(f"{min(max(val, fr), to):02d}")
            except ValueError:
                v.set(f"{default:02d}")
        spin.bind("<KeyRelease>", _fmt)
        spin.bind("<<Increment>>", _fmt)
        spin.bind("<<Decrement>>", _fmt)
        return spin

    def _mkbtn(self, parent, text, color, cmd):
        btn = tk.Label(parent, text=text, font=("Segoe UI", 12, "bold"),
                       bg=color, fg=COLORS["bg"], padx=20, pady=10,
                       cursor="hand2")
        btn.pack(side="left", padx=5)
        btn.bind("<Button-1>", lambda e: cmd())
        return btn

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  模式切换
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _switch_mode(self, mode, color):
        if self.running:
            if mode == self.mode:
                return
            # 切换模式先停止
            self._stop()
        self.mode = mode
        for key, lbl in self.tabs.items():
            is_on = key == mode
            lbl.configure(fg=color if is_on else COLORS["subtext"],
                          bg=COLORS["bg"] if is_on else COLORS["dark_card"])
        self._show_countdown() if mode == "countdown" else self._show_stopwatch()

    def _show_countdown(self):
        self.sw_frame.pack_forget()
        self.cd_frame.pack(fill="both", expand=True)

    def _show_stopwatch(self):
        self.cd_frame.pack_forget()
        self.sw_frame.pack(fill="both", expand=True)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  倒计时
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _cd_read_input(self):
        try:
            h = int(self.cd_h_spin.get())
            m = int(self.cd_m_spin.get())
            s = int(self.cd_s_spin.get())
        except ValueError:
            h = m = s = 0
        return h, m, s

    def _cd_toggle(self):
        if self.running:
            self._pause()
        else:
            self._cd_start()

    def _cd_start(self):
        if self.running:
            return
        h, m, s = self._cd_read_input()
        total = h * 3600 + m * 60 + s
        if total <= 0:
            return
        # 如果是从暂停恢复，保留剩余时间
        if self.cd_remaining <= 0:
            self.cd_total = total
            self.cd_remaining = total
        self.running = True
        self._start_ts = time.time() - (self.cd_total - self.cd_remaining)
        self._disable_spins(True)
        self.cd_start_btn.configure(text="⏸  暂停", fg=COLORS["countdown"])
        self._tick()

    def _cd_reset(self):
        self._stop()
        self.cd_remaining = 0
        self.cd_total = 0
        self.cd_display.configure(text="00:00:00")
        self.cd_canvas.coords(self.cd_bar, 0, 0, 400, 12)
        self._disable_spins(False)
        self.cd_start_btn.configure(text="▶  开始", fg=COLORS["success"])

    def _disable_spins(self, disabled):
        state = "disabled" if disabled else "normal"
        self.cd_h_spin.configure(state=state)
        self.cd_m_spin.configure(state=state)
        self.cd_s_spin.configure(state=state)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  秒表
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _sw_toggle(self):
        if self.running:
            self._pause()
        else:
            self._sw_start()

    def _sw_start(self):
        if self.running:
            return
        self.running = True
        self._start_ts = time.time() - self.sw_elapsed
        self.sw_start_btn.configure(text="⏸  暂停", fg=COLORS["stopwatch"])
        self.sw_lap_btn.configure(fg=COLORS["warn"])
        self._tick()

    def _sw_lap(self):
        if not self.running:
            return
        elapsed = time.time() - self._start_ts
        lap_str = self._format_sw(elapsed)
        lap_num = len(self.laps) + 1
        self.laps.append(elapsed)
        self.lap_listbox.insert(0, f"  计次 {lap_num:2d}   {lap_str}")
        self.lap_listbox.selection_clear(0, tk.END)

    def _sw_reset(self):
        self._stop()
        self.sw_elapsed = 0.0
        self.laps = []
        self.sw_display.configure(text="00:00:00.00")
        self.lap_listbox.delete(0, tk.END)
        self.sw_start_btn.configure(text="▶  开始", fg=COLORS["success"])
        self.sw_lap_btn.configure(fg=COLORS["subtext"])

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  共用计时核心
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _stop(self):
        self.running = False
        if self._timer_id:
            self.root.after_cancel(self._timer_id)
            self._timer_id = None

    def _pause(self):
        if self.mode == "countdown" and self.cd_remaining > 0:
            self.cd_remaining = max(0, self.cd_total - int(time.time() - self._start_ts))
        elif self.mode == "stopwatch":
            self.sw_elapsed = time.time() - self._start_ts
        self._stop()
        if self.mode == "countdown":
            self.cd_start_btn.configure(text="▶  继续", fg=COLORS["success"])
        else:
            self.sw_start_btn.configure(text="▶  继续", fg=COLORS["success"])

    def _tick(self):
        if not self.running:
            return
        elapsed = time.time() - self._start_ts
        if self.mode == "countdown":
            remaining = max(0, self.cd_total - int(elapsed))
            self.cd_remaining = remaining
            self._cd_update_display()
            if remaining <= 0:
                self._cd_complete()
                return
        else:
            self.sw_elapsed = elapsed
            self._sw_update_display()
        self._timer_id = self.root.after(30, self._tick)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  显示更新
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _cd_update_display(self):
        h = self.cd_remaining // 3600
        m = (self.cd_remaining % 3600) // 60
        s = self.cd_remaining % 60
        self.cd_display.configure(text=f"{h:02d}:{m:02d}:{s:02d}")
        # 进度条
        if self.cd_total > 0:
            w = int(400 * self.cd_remaining / self.cd_total)
            self.cd_canvas.coords(self.cd_bar, 0, 0, w, 12)

    def _sw_update_display(self):
        self.sw_display.configure(text=self._format_sw(self.sw_elapsed))

    def _format_sw(self, secs):
        h = int(secs // 3600)
        m = int((secs % 3600) // 60)
        s = int(secs % 60)
        cs = int((secs - int(secs)) * 100)
        return f"{h:02d}:{m:02d}:{s:02d}.{cs:02d}"

    def _cd_complete(self):
        self._stop()
        self.cd_remaining = 0
        self.cd_display.configure(text="00:00:00")
        self.cd_canvas.coords(self.cd_bar, 0, 0, 400, 12)
        self.cd_start_btn.configure(text="▶  开始", fg=COLORS["success"])
        self._disable_spins(False)
        play_alarm()
        # 闪烁窗口
        self.root.attributes("-topmost", True)
        self.root.after(600, lambda: self.root.attributes("-topmost", False))

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  退出
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _on_close(self):
        self._stop()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    TimerApp().run()
