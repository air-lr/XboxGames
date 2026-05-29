import tkinter as tk
import time
import winsound  # Windows 系统提示音库，用于计时结束播放蜂鸣声
import json
import os
from datetime import datetime

# ═══════════════════════════════════════════════════════════════════════════════
#  全局配置常量
# ═══════════════════════════════════════════════════════════════════════════════

WORK_MIN = 25               # 每个番茄钟（专注时段）的时长，单位：分钟
SHORT_BREAK_MIN = 5         # 短休息时长，单位：分钟
LONG_BREAK_MIN = 15         # 长休息时长，单位：分钟
LONG_BREAK_INTERVAL = 4     # 每完成 N 个番茄钟后，进入一次长休息
SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "pomodoro_settings.json")
                            # 设置文件的保存路径（与脚本同目录）

# 颜色主题：Catppuccin Mocha 风格（深色主题）
COLORS = {
    "bg": "#1e1e2e",        # 主背景色（深紫黑）
    "fg": "#cdd6f4",        # 前景/文字颜色（浅灰白）
    "accent": "#f5c2e7",    # 强调色（粉紫）
    "work": "#f38ba8",      # 专注模式颜色（粉红）
    "break": "#a6e3a1",     # 休息模式颜色（嫩绿）
    "dark_card": "#181825", # 卡片/面板背景色（更深色）
    "border": "#313244",    # 边框颜色
    "subtext": "#6c7086",   # 辅助文字颜色（中灰色）
    "success": "#a6e3a1",   # 成功/开始按钮颜色（绿色）
}

# 各模式时长（秒），避免重复创建字典
MODE_DURATIONS = {
    "work": WORK_MIN * 60,
    "short": SHORT_BREAK_MIN * 60,
    "long": LONG_BREAK_MIN * 60,
}

# 模式中文名称
MODE_NAMES = {"work": "专注", "short": "短休息", "long": "长休息"}

# ═══════════════════════════════════════════════════════════════════════════════
#  通知音效
# ═══════════════════════════════════════════════════════════════════════════════

def play_notification():
    """
    播放计时结束提示音。
    3 声短促高音（880Hz） + 1 声较低长音（660Hz），模仿传统番茄钟的响铃效果。
    winsound.Beep(frequency, duration_ms) 是 Windows 自带的蜂鸣 API。
    """
    for _ in range(3):
        winsound.Beep(880, 200)   # 高音 880Hz，持续 200ms
        time.sleep(0.15)           # 间隔 150ms
    winsound.Beep(660, 300)        # 低音 660Hz，持续 300ms

# ═══════════════════════════════════════════════════════════════════════════════
#  主应用类 —— PomodoroTimer（番茄钟）
# ═══════════════════════════════════════════════════════════════════════════════

class PomodoroTimer:
    """
    番茄钟计时器应用。
    工作流程：
      专注 25 分钟 → 短休息 5 分钟 → 专注 25 分钟 → ... → 长休息 15 分钟 → 循环
    每完成 4 个番茄钟触发一次长休息。
    """

    def __init__(self):
        """
        初始化主窗口、状态变量、加载历史记录、构建 UI、启动主循环准备。
        """
        # ── 创建主窗口 ──
        self.root = tk.Tk()
        self.root.title("番茄钟")
        self.root.geometry("520x540+290+100")   # 窗口尺寸 + 屏幕位置（x=290, y=100）
        self.root.configure(bg=COLORS["bg"])
        self.root.resizable(False, False)        # 固定窗口大小，不允许缩放

        # ── 核心状态变量 ──
        self.mode = "work"           # 当前模式：work（专注）| short（短休息）| long（长休息）
        self.time_left = WORK_MIN * 60   # 剩余时间（秒），初始为 25 分钟
        self.running = False         # 计时器是否正在运行
        self.sessions_done = 0       # 今日已完成的番茄钟数量
        self._timer_id = None        # tkinter after() 定时器 ID，用于取消定时任务
        self._start_ts = None        # 当前计时段的开始时间戳（用于精确计算已用时间）
        # 每个模式独立保存剩余时间，切换模式时不丢失进度
        self._saved_times = MODE_DURATIONS.copy()

        # ── 加载历史记录 ──
        self.load_settings()

        # ── 构建界面 ──
        self._build_ui()
        self._update_display()       # 初始化显示

        # ── 绑定窗口关闭事件 ──
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  设置持久化 —— 将今日完成的番茄钟数量保存到 JSON 文件
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def load_settings(self):
        """
        从 JSON 文件加载历史记录。
        如果文件存在，读取已完成的番茄钟数量，使得关闭程序后重新打开仍能累加。
        """
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE) as f:
                    d = json.load(f)
                self.sessions_done = d.get("sessions", 0)
            except Exception:
                pass  # 文件损坏时静默忽略，使用默认值 0

    def save_settings(self):
        """
        将当前番茄钟数量保存到 JSON 文件。
        每次完成一个番茄钟时调用，以及程序退出时调用。
        """
        try:
            with open(SETTINGS_FILE, "w") as f:
                json.dump({
                    "sessions": self.sessions_done,
                    "last_update": datetime.now().isoformat()
                }, f)
        except Exception:
            pass

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  UI 构建
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _build_ui(self):
        """
        构建完整的用户界面，从上到下依次为：
          1. 头部（标题 + 当前番茄计数）
          2. 模式切换标签（专注 / 短休息 / 长休息）
          3. 画布（圆形计时器：圆弧进度条 + 时间数字 + 模式文字）
          4. 控制按钮（开始/暂停 + 重置）
          5. 统计面板（今日完成数 + 专注总时长）
        """

        # ── 1. 头部 ────────────────────────────────────────────────────────
        header = tk.Frame(self.root, bg=COLORS["bg"], height=40)
        header.pack(fill="x", padx=20, pady=(16, 0))

        # 标题（左侧）
        tk.Label(header, text="🍅  番茄钟", font=("Segoe UI", 16, "bold"),
                 bg=COLORS["bg"], fg=COLORS["fg"]).pack(side="left")

        # 今日番茄数（右侧）
        self.session_label = tk.Label(header, text="", font=("Segoe UI", 11),
                                      bg=COLORS["bg"], fg=COLORS["subtext"])
        self.session_label.pack(side="right")

        # ── 2. 模式切换标签 ───────────────────────────────────────────────
        tab_frame = tk.Frame(self.root, bg=COLORS["bg"])
        tab_frame.pack(pady=(16, 0))

        self.tabs = {}
        for key, label in MODE_NAMES.items():
            btn = tk.Label(tab_frame, text=label,
                           font=("Segoe UI", 11, "bold"),
                           bg=COLORS["dark_card"], fg=COLORS["subtext"],
                           padx=14, pady=6, cursor="hand2")  # hand2 = 手型光标
            btn.pack(side="left", padx=4)
            btn.bind("<Button-1>", lambda e, k=key: self._switch_mode(k))
            self.tabs[key] = btn

        # ── 3. 圆形计时器画布 ────────────────────────────────────────────
        self.canvas = tk.Canvas(self.root, width=280, height=280,
                                bg=COLORS["bg"], highlightthickness=0)
        self.canvas.pack(pady=(12, 0))

        cx, cy, r = 140, 140, 110  # 圆心坐标 (cx, cy)，半径 r

        # 底部圆环（背景边框）
        self.arc_bg = self.canvas.create_oval(
            cx - r, cy - r, cx + r, cy + r,
            outline=COLORS["border"], width=6
        )

        # 顶部圆弧（进度条，动态变化）
        self.arc_progress = self.canvas.create_arc(
            cx - r, cy - r, cx + r, cy + r,
            start=90, extent=0,       # 从 12 点钟方向开始，角度 0
            outline=COLORS["accent"], width=6,
            style="arc"
        )

        # 中央时间文字（例如 "25:00"）
        self.time_text = self.canvas.create_text(
            cx, cy - 12,
            text="25:00",
            font=("Segoe UI", 44, "bold"),
            fill=COLORS["fg"]
        )

        # 模式文字（例如 "专注"）
        self.mode_text = self.canvas.create_text(
            cx, cy + 34,
            text="专注",
            font=("Segoe UI", 12),
            fill=COLORS["subtext"]
        )

        # ── 4. 控制按钮 ──────────────────────────────────────────────────
        btn_frame = tk.Frame(self.root, bg=COLORS["bg"])
        btn_frame.pack(pady=(8, 0))

        self.start_btn = self._make_btn(btn_frame, "▶  开始", COLORS["success"],
                                        self._toggle, 0, 0)
        self.reset_btn = self._make_btn(btn_frame, "⟳  重置", COLORS["subtext"],
                                        self._reset, 0, 1)
        self.reset_all_btn = self._make_btn(btn_frame, "⟳  全部重置", COLORS["dark_card"],
                                            self._reset_all, 0, 2, fg=COLORS["fg"])

        # ── 5. 统计面板 ──────────────────────────────────────────────────
        stat_frame = tk.Frame(self.root, bg=COLORS["dark_card"],
                              highlightbackground=COLORS["border"],
                              highlightthickness=1, relief="flat")
        stat_frame.pack(fill="x", padx=20, pady=(16, 20))

        self.stat_session_val = self._stat_item(stat_frame, "今日完成", self.sessions_done, 0)
        self.stat_focus_val = self._stat_item(stat_frame, "专注时长", "0分", 1)

    def _make_btn(self, parent, text, color, cmd, row, col, colspan=1, fg=None):
        """
        创建统一样式的按钮（用 Label 模拟，避免 Windows 上 Button 自定义颜色后文字消失的 bug）。
        """
        if fg is None:
            fg = COLORS["bg"]
        btn = tk.Label(parent, text=text, font=("Segoe UI", 12, "bold"),
                       bg=color, fg=fg, padx=20, pady=10,
                       cursor="hand2")
        btn.grid(row=row, column=col, columnspan=colspan, padx=4)
        btn.bind("<Button-1>", lambda e: cmd())
        return btn

    def _stat_item(self, parent, label, value, col):
        """
        创建统计面板中的一个指标项。
        参数：
          parent - 父容器
          label  - 指标名称（如"今日完成"）
          value  - 指标数值（初始值）
          col    - grid 列位置
        返回：数值 Label 对象，方便后续更新
        """
        f = tk.Frame(parent, bg=COLORS["dark_card"])
        f.grid(row=0, column=col, padx=20, pady=12)

        # 大号数值（例如 "3" 或 "75分"）
        val = tk.Label(f, text=str(value), font=("Segoe UI", 20, "bold"),
                       bg=COLORS["dark_card"], fg=COLORS["fg"])
        val.pack()

        # 小号标签文字
        tk.Label(f, text=label, font=("Segoe UI", 9),
                 bg=COLORS["dark_card"], fg=COLORS["subtext"]).pack()
        return val

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  核心逻辑
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _switch_mode(self, mode):
        """
        手动切换模式（专注 / 短休息 / 长休息）。
        切换时会保存当前模式的剩余时间，恢复目标模式的已保存时间。
        运行时也可切换（自动暂停），来回切换不会丢失进度。
        """
        if mode == self.mode:
            return  # 同模式不处理

        # 保存当前模式的剩余时间
        self._saved_times[self.mode] = self.time_left

        # 如果正在运行，先暂停
        was_running = self.running
        if was_running:
            self._pause()

        self.mode = mode
        # 恢复目标模式上次保存的时间
        self.time_left = self._saved_times[mode]
        self._update_tab_style()
        self._update_display()

    def _update_tab_style(self):
        """
        更新模式标签的样式：当前选中的模式高亮显示，其他模式变灰。
        专注模式用红色高亮，休息模式用绿色高亮。
        """
        active_color = COLORS["work"] if self.mode == "work" else COLORS["break"]
        for key, lbl in self.tabs.items():
            is_active = key == self.mode
            lbl.configure(
                fg=active_color if is_active else COLORS["subtext"],
                bg=COLORS["bg"] if is_active else COLORS["dark_card"]
            )

    def _toggle(self):
        """
        切换开始/暂停状态。
        运行时 → 暂停；停止时 → 开始。
        """
        if self.running:
            self._pause()
        else:
            self._start()

    def _stop_timer(self):
        """停止计时器，取消 after 定时任务。"""
        self.running = False
        if self._timer_id:
            self.root.after_cancel(self._timer_id)
            self._timer_id = None

    def _start(self):
        """
        开始计时。
        记录开始时间戳，启动定时器循环 _tick()。
        按钮文字变为"暂停"。
        """
        self.running = True
        total = MODE_DURATIONS[self.mode]
        # 计算开始时间戳：如果之前暂停过，保证从剩余时间继续
        self._start_ts = time.time() - (total - self.time_left)
        self.start_btn.configure(text="⏸  暂停", fg=COLORS["work"])
        self._tick()

    def _pause(self):
        """
        暂停计时。
        取消 after 定时器，按钮文字变为"继续"。
        """
        self._stop_timer()
        self.start_btn.configure(text="▶  继续", fg=COLORS["bg"])

    def _reset(self):
        """
        重置计时器。
        停止计时，只重置当前模式的保存时间（其他模式不受影响）。
        """
        self._stop_timer()
        self._saved_times[self.mode] = MODE_DURATIONS[self.mode]
        self.time_left = self._saved_times[self.mode]
        self.start_btn.configure(text="▶  开始", fg=COLORS["bg"])
        self._update_display()

    def _reset_all(self):
        """
        全部重置：停止计时，将三个模式的时间全部归零重置。
        """
        self._stop_timer()
        for k, v in MODE_DURATIONS.items():
            self._saved_times[k] = v
        self.time_left = self._saved_times[self.mode]
        self.start_btn.configure(text="▶  开始", fg=COLORS["bg"])
        self._update_display()

    def _tick(self):
        """
        定时器核心循环（每 200ms 执行一次）。
        根据开始时间戳和当前时间计算已用时间，更新剩余时间。
        当剩余时间为 0 时，调用 _timer_done() 处理结束逻辑。
        """
        if not self.running:
            return

        now = time.time()
        elapsed = now - self._start_ts
        total = MODE_DURATIONS[self.mode]
        self.time_left = max(0, total - int(elapsed))  # 防止负数

        self._update_display()

        if self.time_left <= 0:
            self._timer_done()    # 计时结束
            return

        # 每 200ms 调用一次自身，形成持续循环
        self._timer_id = self.root.after(200, self._tick)

    def _timer_done(self):
        """
        计时结束处理。
          1. 停止计时器
          2. 播放提示音
          3. 如果是专注结束：
               - 番茄钟计数 +1
               - 保存设置
               - 判断进入短休息还是长休息（每 LONG_BREAK_INTERVAL 次进入长休息）
          4. 如果是休息结束：自动切回专注模式
          5. 闪烁窗口吸引用户注意
        """
        self.running = False
        self._timer_id = None
        self.start_btn.configure(text="▶  开始", fg=COLORS["bg"])
        play_notification()

        # 重置当前模式的保存时间（下次切回来时从头开始）
        self._saved_times[self.mode] = MODE_DURATIONS[self.mode]

        # 根据当前模式决定下一阶段
        if self.mode == "work":
            self.sessions_done += 1
            self.save_settings()
            self.mode = "long" if self.sessions_done % LONG_BREAK_INTERVAL == 0 else "short"
        else:
            self.mode = "work"

        # 同时重置目标模式的保存时间，避免手动切过模式导致残留部分时间
        self._saved_times[self.mode] = MODE_DURATIONS[self.mode]
        self.time_left = self._saved_times[self.mode]
        self._update_tab_style()
        self._update_display()

        # 窗口置顶闪烁：短暂将窗口置于最前，引起用户注意
        self.root.attributes("-topmost", True)
        self.root.after(500, lambda: self.root.attributes("-topmost", False))

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  显示更新
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _update_display(self):
        """
        更新界面上的所有显示元素：
          - 中央时间文本（MM:SS 格式）
          - 模式文字（专注/短休息/长休息）
          - 圆弧进度条（角度 = 360 × 已完成比例）
          - 圆弧颜色（红色=专注，绿色=休息）
          - 头部番茄计数
          - 底部统计面板
        """
        # 格式化时间显示
        minutes = self.time_left // 60
        seconds = self.time_left % 60
        self.canvas.itemconfig(self.time_text, text=f"{minutes:02d}:{seconds:02d}")

        # 模式文字
        self.canvas.itemconfig(self.mode_text, text=MODE_NAMES[self.mode])

        # 圆弧进度：已完成角度 = 360° × (1 - 剩余/总时长)
        total = MODE_DURATIONS[self.mode]
        progress = 1 - (self.time_left / total)
        arc_color = COLORS["work"] if self.mode == "work" else COLORS["break"]
        self.canvas.itemconfig(self.arc_progress,
                               extent=360 * progress,
                               outline=arc_color)

        # 头部番茄计数
        self.session_label.configure(text=f"今日: {self.sessions_done} 个番茄")
        self._update_stats()

    def _update_stats(self):
        """
        更新底部统计面板：
          - 今日完成的番茄钟数量
          - 累计专注时长（sessions_done × 25 分钟，超过 60 分钟显示"X时 Y分"）
        """
        total_focus = self.sessions_done * WORK_MIN
        h, m = total_focus // 60, total_focus % 60
        time_str = f"{h}时 {m}分" if h else f"{m}分"   # 超过 1 小时才显示"X时"
        self.stat_session_val.configure(text=str(self.sessions_done))
        self.stat_focus_val.configure(text=time_str)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  退出处理
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _on_close(self):
        """
        窗口关闭事件处理。
        停止计时器、取消定时任务、保存当前状态、销毁窗口。
        """
        self._stop_timer()
        self.save_settings()
        self.root.destroy()

    def run(self):
        """
        启动应用程序，进入 tkinter 主事件循环。
        """
        self.root.mainloop()


# ═══════════════════════════════════════════════════════════════════════════════
#  程序入口
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    PomodoroTimer().run()