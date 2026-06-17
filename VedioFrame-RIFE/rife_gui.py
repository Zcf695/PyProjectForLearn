"""
RIFE Video Frame Interpolation Tool - Modern GUI
================================================
A beautifully designed GUI for RIFE-based video frame interpolation,
featuring real-time progress tracking, comparison metrics dashboard,
and a modern dark theme.
"""

import os
import sys
import time
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import threading
import subprocess
import re

from metrics_utils import compute_all_metrics, format_size, format_time


# ── Color Palette ──────────────────────────────────────────────
THEME = {
    'bg_root':       '#0d1117',   # GitHub-dark inspired root bg
    'bg_card':        '#161b22',   # card background
    'bg_input':       '#0d1117',   # input field bg
    'border':         '#30363d',   # subtle borders
    'accent':         '#1f6feb',   # primary blue
    'accent_hover':   '#388bfd',
    'highlight':      '#f78166',   # warm orange for emphasis
    'success':        '#3fb950',   # green
    'warning':        '#d29922',   # yellow
    'danger':         '#f85149',   # red
    'text_primary':   '#e6edf3',   # main text
    'text_secondary': '#8b949e',   # muted text
    'text_bright':    '#ffffff',
    'progress_bg':    '#21262d',
    'progress_fill':  '#1f6feb',
    'btn_start':      '#238636',   # green start button
    'btn_cancel':     '#da3633',   # red cancel button
}


class RIFEGUI:
    """Main GUI application class for the RIFE interpolation tool."""

    def __init__(self, root):
        self.root = root
        self.root.title("RIFE 视频插帧工具 - Real-time Intermediate Flow Estimation")
        self.root.geometry("920x780")
        self.root.minsize(820, 680)
        self.root.configure(bg=THEME['bg_root'])

        # State
        self.processing = False
        self.cancel_process = False
        self.start_time = None
        self.metrics = None  # stores comparison results

        self._setup_theme()
        self._build_ui()

    # ── Theme Setup ────────────────────────────────────────────
    def _setup_theme(self):
        style = ttk.Style(self.root)
        style.theme_use('clam')  # most configurable base theme

        # ── Global defaults ──
        style.configure('.',
            background=THEME['bg_root'],
            foreground=THEME['text_primary'],
            fieldbackground=THEME['bg_input'],
            bordercolor=THEME['border'],
            troughcolor=THEME['progress_bg'],
            selectbackground=THEME['accent'],
            selectforeground=THEME['text_bright'],
        )

        # ── Label ──
        style.configure('TLabel',
            background=THEME['bg_root'],
            foreground=THEME['text_primary'],
            font=('Microsoft YaHei UI', 10),
        )
        style.configure('CardLabel.TLabel',
            background=THEME['bg_card'],
            foreground=THEME['text_primary'],
            font=('Microsoft YaHei UI', 10),
        )
        style.configure('SectionTitle.TLabel',
            background=THEME['bg_card'],
            foreground=THEME['text_bright'],
            font=('Microsoft YaHei UI', 11, 'bold'),
        )
        style.configure('Title.TLabel',
            background=THEME['bg_root'],
            foreground=THEME['text_bright'],
            font=('Microsoft YaHei UI', 18, 'bold'),
        )
        style.configure('Subtitle.TLabel',
            background=THEME['bg_root'],
            foreground=THEME['text_secondary'],
            font=('Microsoft YaHei UI', 9),
        )

        # ── Button ──
        style.configure('TButton',
            background=THEME['accent'],
            foreground=THEME['text_bright'],
            borderwidth=0,
            font=('Microsoft YaHei UI', 9, 'bold'),
            padding=(14, 6),
            relief='flat',
        )
        style.map('TButton',
            background=[('active', THEME['accent_hover']),
                        ('disabled', THEME['progress_bg'])],
            foreground=[('disabled', THEME['text_secondary'])],
        )

        # Start button (green)
        style.configure('Start.TButton',
            background=THEME['btn_start'],
            font=('Microsoft YaHei UI', 10, 'bold'),
            padding=(24, 8),
        )
        style.map('Start.TButton',
            background=[('active', '#2ea043'), ('disabled', THEME['progress_bg'])],
        )

        # Cancel button (red)
        style.configure('Cancel.TButton',
            background=THEME['btn_cancel'],
            font=('Microsoft YaHei UI', 10, 'bold'),
            padding=(24, 8),
        )
        style.map('Cancel.TButton',
            background=[('active', '#e5534b'), ('disabled', THEME['progress_bg'])],
        )

        # ── Entry ──
        style.configure('TEntry',
            fieldbackground=THEME['bg_input'],
            foreground=THEME['text_primary'],
            borderwidth=1,
            relief='solid',
            padding=(8, 6),
            font=('Consolas', 10),
        )

        # ── Radiobutton ──
        style.configure('TRadiobutton',
            background=THEME['bg_card'],
            foreground=THEME['text_primary'],
            font=('Microsoft YaHei UI', 9),
        )
        style.map('TRadiobutton',
            background=[('active', THEME['bg_card']),
                        ('selected', THEME['bg_card'])],
        )

        # ── Frame ──
        style.configure('Card.TFrame',
            background=THEME['bg_card'],
            relief='solid',
            borderwidth=1,
        )

        # ── Progressbar ──
        style.configure('TProgressbar',
            background=THEME['progress_fill'],
            troughcolor=THEME['progress_bg'],
            borderwidth=0,
            thickness=10,
        )

        # ── Separator ──
        style.configure('TSeparator',
            background=THEME['border'],
        )

        # ── Scrollbar ──
        style.configure('Vertical.TScrollbar',
            background=THEME['bg_card'],
            troughcolor=THEME['bg_root'],
            arrowcolor=THEME['text_secondary'],
        )

    # ── UI Construction ────────────────────────────────────────
    def _build_ui(self):
        # Scrollable canvas for the full content
        self.canvas = tk.Canvas(self.root, bg=THEME['bg_root'],
                                 highlightthickness=0, bd=0)
        scrollbar = ttk.Scrollbar(self.root, orient='vertical',
                                   command=self.canvas.yview)
        self.scroll_frame = tk.Frame(self.canvas, bg=THEME['bg_root'])

        self.scroll_frame.bind('<Configure>',
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox('all')))

        self.canvas.create_window((0, 0), window=self.scroll_frame,
                                   anchor='nw', tags='inner')
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        # Bind mousewheel
        self._bind_scroll()

        # ── Build sections ──
        self._build_header(self.scroll_frame)
        self._build_input_card(self.scroll_frame)
        self._build_params_card(self.scroll_frame)
        self._build_process_card(self.scroll_frame)
        self._build_results_card(self.scroll_frame)
        self._build_log_card(self.scroll_frame)
        self._build_status_bar(self.scroll_frame)

    def _bind_scroll(self):
        def _on_mousewheel(event):
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')
        def _on_enter(event):
            self.canvas.bind_all('<MouseWheel>', _on_mousewheel)
        def _on_leave(event):
            self.canvas.unbind_all('<MouseWheel>')
        self.canvas.bind('<Enter>', _on_enter)
        self.canvas.bind('<Leave>', _on_leave)

    # ── Header ─────────────────────────────────────────────────
    def _build_header(self, parent):
        header = tk.Frame(parent, bg=THEME['bg_root'])
        header.pack(fill='x', padx=25, pady=(25, 5))

        # Logo row
        logo_row = tk.Frame(header, bg=THEME['bg_root'])
        logo_row.pack(fill='x')

        # Decorative bar
        bar = tk.Canvas(logo_row, width=4, height=38, bg=THEME['bg_root'],
                         highlightthickness=0, bd=0)
        bar.create_rectangle(0, 0, 4, 38, fill=THEME['accent'], outline='')
        bar.pack(side='left', padx=(0, 12))

        texts = tk.Frame(logo_row, bg=THEME['bg_root'])
        texts.pack(side='left')
        tk.Label(texts, text="🎬  RIFE 视频插帧工具",
                 font=('Microsoft YaHei UI', 20, 'bold'),
                 fg=THEME['text_bright'], bg=THEME['bg_root']).pack(anchor='w')
        tk.Label(texts, text="Real-time Intermediate Flow Estimation  ·  高帧率视频生成  ·  AI 运动补偿",
                 font=('Microsoft YaHei UI', 9),
                 fg=THEME['text_secondary'], bg=THEME['bg_root']).pack(anchor='w')

        ttk.Separator(parent, orient='horizontal').pack(fill='x', padx=25, pady=(12, 0))

    # ── Input Card ─────────────────────────────────────────────
    def _build_input_card(self, parent):
        card = self._create_card(parent, '📁  输入 / 输出设置')

        # Input video
        row1 = tk.Frame(card, bg=THEME['bg_card'])
        row1.pack(fill='x', pady=(0, 8))
        tk.Label(row1, text="输入视频", fg=THEME['text_primary'],
                 bg=THEME['bg_card'], font=('Microsoft YaHei UI', 10),
                 width=10, anchor='e').pack(side='left', padx=(0, 8))
        self.video_path = tk.StringVar()
        entry_in = tk.Entry(row1, textvariable=self.video_path,
                            font=('Consolas', 10),
                            bg=THEME['bg_input'], fg=THEME['text_primary'],
                            insertbackground=THEME['text_primary'],
                            relief='flat', bd=0,
                            highlightbackground=THEME['border'],
                            highlightthickness=1)
        entry_in.pack(side='left', fill='x', expand=True, ipady=4)
        tk.Button(row1, text="📂 浏览", command=self._browse_video,
                  bg=THEME['accent'], fg=THEME['text_bright'],
                  font=('Microsoft YaHei UI', 9, 'bold'),
                  relief='flat', bd=0, padx=12, pady=4,
                  activebackground=THEME['accent_hover'],
                  activeforeground=THEME['text_bright'],
                  cursor='hand2').pack(side='left', padx=(8, 0))

        # Output video
        row2 = tk.Frame(card, bg=THEME['bg_card'])
        row2.pack(fill='x')
        tk.Label(row2, text="输出视频", fg=THEME['text_primary'],
                 bg=THEME['bg_card'], font=('Microsoft YaHei UI', 10),
                 width=10, anchor='e').pack(side='left', padx=(0, 8))
        self.output_path = tk.StringVar()
        entry_out = tk.Entry(row2, textvariable=self.output_path,
                             font=('Consolas', 10),
                             bg=THEME['bg_input'], fg=THEME['text_primary'],
                             insertbackground=THEME['text_primary'],
                             relief='flat', bd=0,
                             highlightbackground=THEME['border'],
                             highlightthickness=1)
        entry_out.pack(side='left', fill='x', expand=True, ipady=4)
        tk.Button(row2, text="📂 浏览", command=self._browse_output,
                  bg=THEME['accent'], fg=THEME['text_bright'],
                  font=('Microsoft YaHei UI', 9, 'bold'),
                  relief='flat', bd=0, padx=12, pady=4,
                  activebackground=THEME['accent_hover'],
                  activeforeground=THEME['text_bright'],
                  cursor='hand2').pack(side='left', padx=(8, 0))

    # ── Parameters Card ────────────────────────────────────────
    def _build_params_card(self, parent):
        card = self._create_card(parent, '⚙️  参数设置')

        # --- Frame multiplier ---
        tk.Label(card, text="插帧倍数", fg=THEME['text_primary'],
                 bg=THEME['bg_card'], font=('Microsoft YaHei UI', 10, 'bold'),
                 ).pack(anchor='w', pady=(0, 6))

        exp_frame = tk.Frame(card, bg=THEME['bg_card'])
        exp_frame.pack(fill='x', pady=(0, 12))

        self.exp_var = tk.StringVar(value='1')
        exp_labels = ['2x', '4x', '8x', '16x', '32x']
        for i, label in enumerate(exp_labels):
            self._radio_pill(exp_frame, label, self.exp_var, str(i))

        # --- Scale factor ---
        tk.Label(card, text="缩放因子", fg=THEME['text_primary'],
                 bg=THEME['bg_card'], font=('Microsoft YaHei UI', 10, 'bold'),
                 ).pack(anchor='w', pady=(0, 6))

        scale_frame = tk.Frame(card, bg=THEME['bg_card'])
        scale_frame.pack(fill='x', pady=(0, 12))

        self.scale_var = tk.StringVar(value='0.25')
        for s in ['0.25', '0.5', '1.0', '2.0', '4.0']:
            self._radio_pill(scale_frame, s, self.scale_var, s)

        # --- Custom FPS ---
        tk.Label(card, text="自定义 FPS", fg=THEME['text_primary'],
                 bg=THEME['bg_card'], font=('Microsoft YaHei UI', 10, 'bold'),
                 ).pack(anchor='w', pady=(0, 6))

        fps_row = tk.Frame(card, bg=THEME['bg_card'])
        fps_row.pack(fill='x')

        self.fps_var = tk.StringVar()
        fps_entry = tk.Entry(fps_row, textvariable=self.fps_var,
                             font=('Consolas', 11), width=8,
                             bg=THEME['bg_input'], fg=THEME['text_primary'],
                             insertbackground=THEME['text_primary'],
                             relief='flat', bd=0,
                             highlightbackground=THEME['border'],
                             highlightthickness=1)
        fps_entry.pack(side='left', ipady=4)

        tk.Label(fps_row, text="  留空保持原始同步",
                 fg=THEME['text_secondary'], bg=THEME['bg_card'],
                 font=('Microsoft YaHei UI', 8)).pack(side='left', padx=(8, 0))

        for fps_val in ['30', '60', '120', '240']:
            tk.Button(fps_row, text=fps_val, width=5,
                      bg=THEME['progress_bg'], fg=THEME['text_primary'],
                      font=('Consolas', 9), relief='flat', bd=0, padx=8, pady=3,
                      activebackground=THEME['accent'],
                      activeforeground=THEME['text_bright'],
                      cursor='hand2',
                      command=lambda v=fps_val: self.fps_var.set(v)
                      ).pack(side='left', padx=3)

    # ── Process Card ───────────────────────────────────────────
    def _build_process_card(self, parent):
        card = self._create_card(parent, '🚀  处理控制')

        # Buttons row
        btn_row = tk.Frame(card, bg=THEME['bg_card'])
        btn_row.pack(fill='x', pady=(0, 10))

        self.process_btn = tk.Button(btn_row, text="▶  开始处理",
                                     command=self._start_processing,
                                     bg=THEME['btn_start'], fg=THEME['text_bright'],
                                     font=('Microsoft YaHei UI', 10, 'bold'),
                                     relief='flat', bd=0, padx=30, pady=8,
                                     activebackground='#2ea043',
                                     activeforeground=THEME['text_bright'],
                                     cursor='hand2')
        self.process_btn.pack(side='left', padx=(0, 10))

        self.cancel_btn = tk.Button(btn_row, text="⏹  取消",
                                    command=self._cancel_processing,
                                    bg=THEME['progress_bg'], fg=THEME['text_secondary'],
                                    font=('Microsoft YaHei UI', 10, 'bold'),
                                    relief='flat', bd=0, padx=30, pady=8,
                                    activebackground=THEME['btn_cancel'],
                                    activeforeground=THEME['text_bright'],
                                    cursor='hand2', state='disabled')
        self.cancel_btn.pack(side='left')

        # Progress bar
        prog_frame = tk.Frame(card, bg=THEME['bg_card'])
        prog_frame.pack(fill='x')

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(prog_frame, variable=self.progress_var,
                                             length=200, mode='determinate')
        self.progress_bar.pack(side='left', fill='x', expand=True, padx=(0, 10))

        self.progress_label = tk.Label(prog_frame, text='0%',
                                        fg=THEME['text_secondary'],
                                        bg=THEME['bg_card'],
                                        font=('Consolas', 10, 'bold'), width=6)
        self.progress_label.pack(side='right')

    # ── Results Card ───────────────────────────────────────────
    def _build_results_card(self, parent):
        card = self._create_card(parent, '📊  处理结果对比')

        self.results_container = tk.Frame(card, bg=THEME['bg_card'])
        self.results_container.pack(fill='x')

        # Placeholder
        self.results_placeholder = tk.Label(
            self.results_container,
            text="处理完成后将在此显示对比数据\n—  帧数 · FPS · SSIM · PSNR · 平滑度 · 文件大小  —",
            fg=THEME['text_secondary'], bg=THEME['bg_card'],
            font=('Microsoft YaHei UI', 9), justify='center')
        self.results_placeholder.pack(pady=20)

        # Hidden results frame (shown after processing)
        self.results_frame = tk.Frame(self.results_container, bg=THEME['bg_card'])

    def _show_results(self, metrics):
        """Populate and display the comparison results dashboard."""
        self.results_placeholder.pack_forget()
        self.metrics = metrics

        # Clear previous
        for w in self.results_frame.winfo_children():
            w.destroy()

        self.results_frame.pack(fill='x', pady=(5, 0))

        # ── Quality grade badge ──
        grade = metrics.get('grade', 'N/A')
        grade_colors = {'A+': '#3fb950', 'A': '#3fb950', 'B': '#1f6feb',
                        'C': '#d29922', 'D': '#f85149'}
        grade_bg = grade_colors.get(grade, THEME['progress_bg'])

        grade_row = tk.Frame(self.results_frame, bg=THEME['bg_card'])
        grade_row.pack(fill='x', pady=(0, 12))

        badge = tk.Canvas(grade_row, width=48, height=48, bg=THEME['bg_card'],
                           highlightthickness=0, bd=0)
        badge.create_oval(4, 4, 44, 44, fill=grade_bg, outline='')
        badge.create_text(24, 24, text=grade, fill='#fff',
                          font=('Consolas', 18, 'bold'))
        badge.pack(side='left', padx=(0, 12))

        tk.Label(grade_row, text="综合质量评级",
                 fg=THEME['text_bright'], bg=THEME['bg_card'],
                 font=('Microsoft YaHei UI', 12, 'bold')).pack(side='left', anchor='w')
        tk.Label(grade_row, text=f"  ·  插帧处理完成",
                 fg=THEME['text_secondary'], bg=THEME['bg_card'],
                 font=('Microsoft YaHei UI', 9)).pack(side='left', anchor='w')

        # ── Comparison grid ──
        grid = tk.Frame(self.results_frame, bg=THEME['bg_card'])
        grid.pack(fill='x', pady=(0, 10))

        # Column headers
        for col, (text, color) in enumerate([
            ('', THEME['text_secondary']),
            ('📼 原始视频', THEME['text_secondary']),
            ('✨ 处理后视频', THEME['accent']),
            ('📈 提升', THEME['success']),
        ]):
            tk.Label(grid, text=text, fg=color, bg=THEME['bg_card'],
                     font=('Microsoft YaHei UI', 9, 'bold'),
                     width=18, anchor='w').grid(row=0, column=col, padx=(0 if col == 0 else 8, 0), pady=(0, 4))

        # Build comparison data rows
        rows_data = self._build_comparison_rows(metrics)
        for r, (label, orig, proc, improvement) in enumerate(rows_data):
            row_num = r + 1
            tk.Label(grid, text=label, fg=THEME['text_secondary'],
                     bg=THEME['bg_card'], font=('Microsoft YaHei UI', 9),
                     width=18, anchor='w').grid(
                row=row_num, column=0, sticky='w', pady=1, padx=(0, 8))
            tk.Label(grid, text=orig, fg=THEME['text_primary'],
                     bg=THEME['bg_card'], font=('Consolas', 10),
                     width=18, anchor='w').grid(
                row=row_num, column=1, sticky='w', pady=1, padx=(0, 8))
            tk.Label(grid, text=proc, fg=THEME['text_bright'],
                     bg=THEME['bg_card'], font=('Consolas', 10, 'bold'),
                     width=18, anchor='w').grid(
                row=row_num, column=2, sticky='w', pady=1, padx=(0, 8))
            tk.Label(grid, text=improvement, fg=THEME['success'],
                     bg=THEME['bg_card'], font=('Consolas', 10, 'bold'),
                     width=18, anchor='w').grid(
                row=row_num, column=3, sticky='w', pady=1)

        # ── Summary bar ──
        summary = tk.Frame(self.results_frame, bg=THEME['progress_bg'])
        summary.pack(fill='x', pady=(6, 0))

        summary_parts = []
        summary_parts.append(f"⏱ 处理耗时: {format_time(metrics.get('processing_time'))}")

        orig_fps = metrics.get('orig_fps', 0)
        proc_fps = metrics.get('proc_fps', 0)
        summary_parts.append(f"🎯 FPS: {orig_fps:.0f} → {proc_fps:.0f}")

        psnr = metrics.get('avg_psnr', 0)
        summary_parts.append(f"📡 PSNR: {psnr:.1f} dB")

        tk.Label(summary,
                 text='   ·   '.join(summary_parts),
                 fg=THEME['text_secondary'], bg=THEME['progress_bg'],
                 font=('Microsoft YaHei UI', 9),
                 padx=12, pady=8).pack()

    def _build_comparison_rows(self, m):
        """Build comparison data rows from metrics dict."""
        rows = []

        # Frame count
        orig_frames = m.get('orig_frame_count', 0)
        proc_frames = m.get('proc_frame_count', 0)
        ratio = m.get('frame_increase_ratio', 0)
        rows.append(('📋 总帧数', f'{orig_frames:,}', f'{proc_frames:,}',
                     f'↑ {ratio:.1f}x'))

        # FPS
        orig_fps = m.get('orig_fps', 0)
        proc_fps = m.get('proc_fps', 0)
        fps_ratio = m.get('fps_increase_ratio', 0)
        rows.append(('🎬 帧率 (FPS)', f'{orig_fps:.1f}', f'{proc_fps:.1f}',
                     f'↑ {fps_ratio:.1f}x'))

        # SSIM (consecutive frame similarity)
        orig_ssim = m.get('orig_avg_ssim', 0)
        proc_ssim = m.get('proc_avg_ssim', 0)
        ssim_diff = proc_ssim - orig_ssim
        if ssim_diff > 0.02:
            ssim_note = '↑ 更平滑'
        elif ssim_diff < -0.15:
            ssim_note = '↓ 更多动态'
        else:
            ssim_note = '→ 保持'
        rows.append(('🔍 帧间 SSIM', f'{orig_ssim:.4f}', f'{proc_ssim:.4f}',
                     ssim_note))

        # Smoothness score
        orig_smooth = m.get('orig_smoothness', 0)
        proc_smooth = m.get('proc_smoothness', 0)
        smooth_diff = proc_smooth - orig_smooth
        if smooth_diff > 5:
            smooth_note = f'↑ +{smooth_diff:.0f} 显著提升'
        elif smooth_diff > 0:
            smooth_note = f'↑ +{smooth_diff:.0f} 提升'
        elif smooth_diff > -5:
            smooth_note = '→ 持平'
        else:
            smooth_note = f'↓ {smooth_diff:.0f}'
        rows.append(('🌊 平滑度指数', f'{orig_smooth:.1f}', f'{proc_smooth:.1f}',
                     smooth_note))

        # PSNR
        psnr = m.get('avg_psnr', 0)
        if psnr >= 40:
            psnr_label = '🏆 优秀'
        elif psnr >= 30:
            psnr_label = '✅ 良好'
        elif psnr >= 20:
            psnr_label = '⚠️ 一般'
        else:
            psnr_label = '❌ 较差'
        rows.append(('📡 平均 PSNR', '—', f'{psnr:.1f} dB', psnr_label))

        # File size
        orig_size = m.get('orig_file_size', 0)
        proc_size = m.get('proc_file_size', 0)
        size_ratio = m.get('size_ratio', 0)
        rows.append(('💾 文件大小', format_size(orig_size), format_size(proc_size),
                     f'{size_ratio:.1f}x'))

        return rows

    # ── Log Card ───────────────────────────────────────────────
    def _build_log_card(self, parent):
        card = self._create_card(parent, '📝  处理日志')

        log_frame = tk.Frame(card, bg=THEME['bg_card'])
        log_frame.pack(fill='x')

        # Scrollbar for log (pack first so it stays right)
        log_scroll = ttk.Scrollbar(log_frame)
        log_scroll.pack(side='right', fill='y')

        self.log_text = tk.Text(log_frame, height=5, wrap='word',
                                 font=('Consolas', 9),
                                 bg=THEME['bg_input'], fg=THEME['text_secondary'],
                                 insertbackground=THEME['text_primary'],
                                 relief='flat', bd=0,
                                 highlightbackground=THEME['border'],
                                 highlightthickness=1,
                                 state='disabled',
                                 yscrollcommand=log_scroll.set)
        self.log_text.pack(side='left', fill='both', expand=True)
        log_scroll.config(command=self.log_text.yview)

    # ── Status Bar ─────────────────────────────────────────────
    def _build_status_bar(self, parent):
        bar = tk.Frame(parent, bg=THEME['progress_bg'], height=28)
        bar.pack(fill='x', side='bottom', pady=(10, 0))

        self.status_label = tk.Label(bar, text='🟢  就绪  —  请选择输入视频开始处理',
                                      fg=THEME['text_secondary'],
                                      bg=THEME['progress_bg'],
                                      font=('Microsoft YaHei UI', 9),
                                      padx=14, pady=4)
        self.status_label.pack(anchor='w')

    # ── Helpers ────────────────────────────────────────────────
    def _create_card(self, parent, title):
        """Create a styled card container with a title."""
        outer = tk.Frame(parent, bg=THEME['bg_root'], padx=25)
        outer.pack(fill='x', pady=(8, 0))

        card = tk.Frame(outer, bg=THEME['bg_card'],
                        highlightbackground=THEME['border'],
                        highlightthickness=1, bd=0)
        card.pack(fill='x')

        # Card header
        header = tk.Frame(card, bg=THEME['bg_card'])
        header.pack(fill='x', padx=16, pady=(12, 10))
        tk.Label(header, text=title,
                 fg=THEME['text_bright'], bg=THEME['bg_card'],
                 font=('Microsoft YaHei UI', 11, 'bold')).pack(anchor='w')

        # Divider
        ttk.Separator(card, orient='horizontal').pack(fill='x', padx=16)

        # Content area
        content = tk.Frame(card, bg=THEME['bg_card'], padx=16, pady=12)
        content.pack(fill='x')

        return content

    def _radio_pill(self, parent, label, var, value):
        """Create a styled radio button that looks like a pill/chip."""
        frame = tk.Frame(parent, bg=THEME['bg_card'])
        frame.pack(side='left', padx=(0, 4))

        rb = tk.Radiobutton(frame, text=label, variable=var, value=value,
                            bg=THEME['progress_bg'], fg=THEME['text_primary'],
                            font=('Consolas', 9, 'bold'),
                            selectcolor=THEME['accent'],
                            indicatoron=False,
                            relief='flat', bd=0, padx=14, pady=5,
                            activebackground=THEME['accent'],
                            activeforeground=THEME['text_bright'],
                            cursor='hand2',
                            width=5 if len(label) <= 4 else 6)
        rb.pack()

    # ── File Dialogs ───────────────────────────────────────────
    def _browse_video(self):
        filename = filedialog.askopenfilename(
            title="选择视频文件",
            filetypes=[("视频文件", "*.mp4 *.avi *.mov *.mkv *.flv *.wmv"),
                       ("所有文件", "*.*")]
        )
        if filename:
            self.video_path.set(filename)
            # Auto-fill output path
            dir_path = os.path.dirname(filename)
            base_name = os.path.basename(filename)
            name, ext = os.path.splitext(base_name)
            exp_val = int(self.exp_var.get())
            multiplier = 2 ** exp_val
            output_name = f"{name}_RIFE_{multiplier}x{ext}"
            self.output_path.set(os.path.join(dir_path, output_name))
            self._set_status('info', '已选择视频文件，请设置参数后开始处理')

    def _browse_output(self):
        filename = filedialog.asksaveasfilename(
            title="保存输出视频",
            defaultextension=".mp4",
            filetypes=[("MP4 文件", "*.mp4"), ("所有文件", "*.*")]
        )
        if filename:
            self.output_path.set(filename)

    # ── Status helpers ─────────────────────────────────────────
    def _set_status(self, level, text):
        icons = {'info': '🟢', 'busy': '🔵', 'warn': '🟡', 'error': '🔴', 'done': '✅'}
        icon = icons.get(level, '')
        self.status_label.config(text=f'{icon}  {text}')

    def _log(self, text, level='info'):
        """Append text to the log widget."""
        self.log_text.config(state='normal')
        self.log_text.insert('end', text)
        self.log_text.see('end')
        self.log_text.config(state='disabled')

    def _clear_log(self):
        self.log_text.config(state='normal')
        self.log_text.delete('1.0', 'end')
        self.log_text.config(state='disabled')

    # ── Processing ─────────────────────────────────────────────
    def _start_processing(self):
        video = self.video_path.get()
        output = self.output_path.get()
        exp = self.exp_var.get()
        scale = self.scale_var.get()
        fps = self.fps_var.get().strip()

        if not video or not os.path.exists(video):
            messagebox.showerror("错误", "请选择有效的输入视频文件！")
            return
        if not output:
            messagebox.showerror("错误", "请设置输出视频路径！")
            return

        # Build command
        cmd = [sys.executable, 'inference_video.py',
               '--exp', exp,
               '--video', video,
               '--output', output,
               '--scale', scale]
        if fps:
            cmd.extend(['--fps', fps])

        # Reset UI state
        self.processing = True
        self.cancel_process = False
        self.start_time = time.time()
        self.process_btn.config(state='disabled', text='⏳  处理中...')
        self.cancel_btn.config(state='normal',
                               bg=THEME['btn_cancel'],
                               fg=THEME['text_bright'])
        self.progress_var.set(0)
        self.progress_label.config(text='0%')
        self._clear_log()
        self._log(f'▶ 开始处理: {os.path.basename(video)}\n')
        self._log(f'  参数: exp={exp}, scale={scale}, fps={fps or "自动"}\n')
        self._log('─' * 50 + '\n')
        self._set_status('busy', '正在处理视频...')

        # Hide previous results, show placeholder
        self.results_frame.pack_forget()
        self.results_placeholder.pack_forget()
        self.results_placeholder.pack(pady=20)
        self.results_placeholder.config(text="⏳  处理中，请稍候...")

        # Run in thread
        threading.Thread(target=self._run_process, args=(cmd, video, output),
                         daemon=True).start()

    def _cancel_processing(self):
        if messagebox.askyesno("确认取消", "确定要取消当前的处理任务吗？"):
            self.cancel_process = True
            self._log('\n⏹ 正在取消处理...\n')
            self._set_status('warn', '正在取消...')

    def _run_process(self, cmd, original_video, output_video):
        """Execute the interpolation process in a background thread."""
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1,
                encoding='utf-8',
                errors='replace',
            )

            frame_pattern = re.compile(r'(\d+)\s*/\s*(\d+)')

            for line in process.stdout:
                if self.cancel_process:
                    process.terminate()
                    self.root.after(0, self._log, '⏹ 处理已取消\n')
                    self.root.after(0, self._set_status, 'warn', '处理已取消')
                    break

                self.root.after(0, self._log, line)

                match = frame_pattern.search(line)
                if match:
                    current = int(match.group(1))
                    total = int(match.group(2))
                    if total > 0:
                        progress = (current / total) * 100
                        self.root.after(0, self._update_progress, progress)

            process.wait()
            elapsed = time.time() - self.start_time

            if process.returncode == 0 and not self.cancel_process:
                self.root.after(0, self._log, '\n' + '─' * 50 + '\n')
                self.root.after(0, self._log, f'✅ 视频处理完成！耗时: {format_time(elapsed)}\n')
                self.root.after(0, self._update_progress, 100)

                # Compute comparison metrics
                self.root.after(0, self._compute_and_show_metrics,
                                original_video, output_video, elapsed)

            elif process.returncode != 0 and not self.cancel_process:
                self.root.after(0, self._log, f'\n❌ 处理失败，返回代码: {process.returncode}\n')
                self.root.after(0, self._set_status, 'error',
                                f'处理失败 (exit code: {process.returncode})')
                self.root.after(0, self._update_progress, 0)
                self.root.after(0, lambda: self.results_placeholder.config(
                                text="❌  处理失败，请检查日志"))
        except Exception as e:
            self.root.after(0, self._log, f'\n❌ 发生错误: {str(e)}\n')
            self.root.after(0, self._set_status, 'error', f'错误: {str(e)}')
        finally:
            self.root.after(0, self._reset_ui)

    def _compute_and_show_metrics(self, original_video, output_video, elapsed):
        """Compute comparison metrics and display them."""
        self._log('\n📊 正在计算对比指标...\n')
        self._set_status('busy', '正在计算对比数据...')

        def _compute():
            try:
                metrics = compute_all_metrics(original_video, output_video,
                                              processing_time=elapsed)
                self.root.after(0, lambda: self._display_metrics(metrics))
            except Exception as e:
                self.root.after(0, self._log, f'⚠️ 指标计算警告: {str(e)}\n')
                self.root.after(0, self._set_status, 'done', '处理完成（指标计算部分失败）')
                self.root.after(0, lambda: self.results_placeholder.config(
                                text="⚠️  指标计算遇到问题，但视频已成功生成"))

        threading.Thread(target=_compute, daemon=True).start()

    def _display_metrics(self, metrics):
        """Show computed metrics in the results card."""
        self._show_results(metrics)
        self._set_status('done', '处理完成！对比数据已生成')
        self._log('📊 对比数据已生成\n')
        self._log(f'   质量评级: {metrics.get("grade", "N/A")}\n')
        self._log(f'   原始帧率: {metrics.get("orig_fps", 0):.1f} FPS  →  '
                  f'处理后: {metrics.get("proc_fps", 0):.1f} FPS\n')
        self._log(f'   帧间SSIM: {metrics.get("orig_avg_ssim", 0):.4f}  →  '
                  f'{metrics.get("proc_avg_ssim", 0):.4f}\n')

    def _update_progress(self, value):
        self.progress_var.set(value)
        self.progress_label.config(text=f'{int(value)}%')

    def _reset_ui(self):
        self.processing = False
        self.process_btn.config(state='normal', text='▶  开始处理')
        self.cancel_btn.config(state='disabled',
                               bg=THEME['progress_bg'],
                               fg=THEME['text_secondary'])


# ── Entry Point ────────────────────────────────────────────────
if __name__ == '__main__':
    # Ensure working directory is the script's directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    root = tk.Tk()
    app = RIFEGUI(root)
    root.mainloop()
