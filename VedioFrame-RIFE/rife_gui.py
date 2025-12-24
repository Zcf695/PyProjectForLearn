import os
import sys
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import threading
import subprocess
import re

class RIFE_GUI:
    def __init__(self, root):
        self.root = root
        self.root.title("RIFE视频插帧工具")
        self.root.geometry("650x450")
        self.root.resizable(False, False)  # 固定窗口大小
        
        # 设置样式
        self.style = ttk.Style()
        self.style.configure("TLabel", font=("SimHei", 10))
        self.style.configure("TButton", font=("SimHei", 10), padding=5)
        self.style.configure("TRadiobutton", font=("SimHei", 10))
        self.style.configure("TEntry", font=("SimHei", 10), padding=3)
        
        # 确保中文显示正常
        self.setup_ui()
        
        # 进度条状态
        self.processing = False
        self.cancel_process = False
    
    def setup_ui(self):
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 视频输入选择
        input_frame = ttk.Frame(main_frame)
        input_frame.grid(row=0, column=0, columnspan=2, sticky=tk.W+tk.E, pady=8)
        ttk.Label(input_frame, text="输入视频:").pack(side=tk.LEFT, padx=(0, 5))
        self.video_path = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.video_path, width=40).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(input_frame, text="浏览", command=self.browse_video, width=8).pack(side=tk.LEFT, padx=(5, 0))
        
        # 输出视频选择
        output_frame = ttk.Frame(main_frame)
        output_frame.grid(row=1, column=0, columnspan=2, sticky=tk.W+tk.E, pady=8)
        ttk.Label(output_frame, text="输出视频:").pack(side=tk.LEFT, padx=(0, 5))
        self.output_path = tk.StringVar()
        ttk.Entry(output_frame, textvariable=self.output_path, width=40).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(output_frame, text="浏览", command=self.browse_output, width=8).pack(side=tk.LEFT, padx=(5, 0))
        
        # 帧率倍数选择
        ttk.Label(main_frame, text="帧率倍数:", font=("SimHei", 10)).grid(row=2, column=0, sticky=tk.W, pady=5)
        self.exp_var = tk.StringVar(value="1")
        exp_frame = ttk.Frame(main_frame)
        exp_frame.grid(row=2, column=1, sticky=tk.W, pady=5)
        
        for i in range(1, 6):  # 支持1到5倍
            ttk.Radiobutton(exp_frame, text=f"{2**i}倍", variable=self.exp_var, value=str(i)).pack(side=tk.LEFT, padx=5)
        
        # 缩放因子选择
        ttk.Label(main_frame, text="缩放因子:", font=("SimHei", 10)).grid(row=3, column=0, sticky=tk.W, pady=5)
        self.scale_var = tk.StringVar(value="0.25")
        scale_frame = ttk.Frame(main_frame)
        scale_frame.grid(row=3, column=1, sticky=tk.W, pady=5)
        
        for scale in ["0.25", "0.5", "1.0", "2.0", "4.0"]:
            ttk.Radiobutton(scale_frame, text=scale, variable=self.scale_var, value=scale).pack(side=tk.LEFT, padx=5)
        
        # 自定义FPS (可选)
        fps_frame = ttk.Frame(main_frame)
        fps_frame.grid(row=4, column=0, columnspan=2, sticky=tk.W, pady=8)
        ttk.Label(fps_frame, text="自定义FPS:").pack(side=tk.LEFT, padx=(0, 5))
        self.fps_var = tk.StringVar()
        ttk.Entry(fps_frame, textvariable=self.fps_var, width=10).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Label(fps_frame, text="(留空则保持原始音频)", font=("SimHei", 9)).pack(side=tk.LEFT, padx=(0, 10))
        
        # 常用FPS选项
        ttk.Label(fps_frame, text="常用选项:", font=("SimHei", 9)).pack(side=tk.LEFT, padx=(0, 5))
        for fps_val in ["30", "60", "120", "240"]:
            ttk.Button(fps_frame, text=fps_val, width=4, 
                      command=lambda val=fps_val: self.fps_var.set(val)).pack(side=tk.LEFT, padx=2)
        
        # 处理按钮
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=5, column=0, columnspan=2, pady=15)
        
        self.process_button = ttk.Button(button_frame, text="开始处理", command=self.start_processing, width=15)
        self.process_button.pack(side=tk.LEFT, padx=15)
        
        self.cancel_button = ttk.Button(button_frame, text="取消", command=self.cancel_processing, state=tk.DISABLED, width=15)
        self.cancel_button.pack(side=tk.LEFT, padx=15)
        
        # 进度条
        progress_frame = ttk.Frame(main_frame)
        progress_frame.grid(row=6, column=0, columnspan=2, sticky=tk.W+tk.E, pady=8)
        ttk.Label(progress_frame, text="处理进度:").pack(side=tk.LEFT, padx=(0, 10))
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, length=450, mode='determinate')
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # 状态文本框
        status_frame = ttk.Frame(main_frame)
        status_frame.grid(row=7, column=0, columnspan=2, sticky=tk.W+tk.E+tk.N+tk.S, pady=8)
        ttk.Label(status_frame, text="处理状态:").pack(side=tk.TOP, anchor=tk.W, pady=(0, 5))
        text_frame = ttk.Frame(status_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)
        self.status_text = tk.Text(text_frame, width=60, height=6, wrap=tk.WORD, font=("SimHei", 9))
        self.status_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(text_frame, command=self.status_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.status_text.config(yscrollcommand=scrollbar.set)
    
    def browse_video(self):
        filename = filedialog.askopenfilename(
            title="选择视频文件",
            filetypes=[("视频文件", "*.mp4 *.avi *.mov *.mkv *.flv *.wmv")]
        )
        if filename:
            self.video_path.set(filename)
            # 自动设置输出路径
            dir_path = os.path.dirname(filename)
            base_name = os.path.basename(filename)
            name, ext = os.path.splitext(base_name)
            exp = self.exp_var.get()
            output_name = f"{name}_2X_{exp}fps{ext}"
            self.output_path.set(os.path.join(dir_path, output_name))
    
    def browse_output(self):
        filename = filedialog.asksaveasfilename(
            title="保存视频文件",
            defaultextension=".mp4",
            filetypes=[("MP4文件", "*.mp4"), ("所有文件", "*.*")]
        )
        if filename:
            self.output_path.set(filename)
    
    def start_processing(self):
        # 检查输入参数
        video = self.video_path.get()
        output = self.output_path.get()
        exp = self.exp_var.get()
        scale = self.scale_var.get()
        fps = self.fps_var.get()
        
        if not video or not os.path.exists(video):
            messagebox.showerror("错误", "请选择有效的输入视频文件")
            return
        
        if not output:
            messagebox.showerror("错误", "请设置输出视频路径")
            return
        
        # 构建命令
        cmd = [sys.executable, "inference_video.py", "--exp", exp, "--video", video, "--output", output, "--scale", scale]
        
        if fps:
            cmd.extend(["--fps", fps])
        
        # 开始处理
        self.processing = True
        self.cancel_process = False
        self.process_button.config(state=tk.DISABLED)
        self.cancel_button.config(state=tk.NORMAL)
        self.progress_var.set(0)
        self.status_text.delete(1.0, tk.END)
        self.status_text.insert(tk.END, f"开始处理视频: {video}\n")
        
        # 在新线程中运行命令
        threading.Thread(target=self.run_command, args=(cmd,)).start()
    
    def cancel_processing(self):
        if messagebox.askyesno("确认", "确定要取消处理吗？"):
            self.cancel_process = True
            self.status_text.insert(tk.END, "正在取消处理...\n")
    
    def run_command(self, cmd):
        try:
            # 启动进程
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            # 处理输出
            frame_pattern = re.compile(r'(\d+)\s*/\s*(\d+)')
            
            for line in process.stdout:
                if self.cancel_process:
                    process.terminate()
                    self.root.after(0, self.update_status, "处理已取消\n")
                    break
                
                # 更新状态文本
                self.root.after(0, self.update_status, line)
                
                # 尝试提取进度信息
                match = frame_pattern.search(line)
                if match:
                    current = int(match.group(1))
                    total = int(match.group(2))
                    progress = (current / total) * 100
                    self.root.after(0, self.update_progress, progress)
            
            # 等待进程结束
            process.wait()
            
            if process.returncode == 0 and not self.cancel_process:
                self.root.after(0, self.update_status, "视频处理完成！\n")
                self.root.after(0, self.update_progress, 100)
                self.root.after(0, messagebox.showinfo, "成功", "视频处理完成！")
            elif process.returncode != 0 and not self.cancel_process:
                self.root.after(0, self.update_status, f"处理失败，返回代码: {process.returncode}\n")
                self.root.after(0, messagebox.showerror, "错误", "视频处理失败！")
        except Exception as e:
            self.root.after(0, self.update_status, f"发生错误: {str(e)}\n")
            self.root.after(0, messagebox.showerror, "错误", f"发生错误: {str(e)}")
        finally:
            self.root.after(0, self.reset_ui)
    
    def update_status(self, text):
        self.status_text.insert(tk.END, text)
        self.status_text.see(tk.END)
    
    def update_progress(self, value):
        self.progress_var.set(value)
    
    def reset_ui(self):
        self.processing = False
        self.process_button.config(state=tk.NORMAL)
        self.cancel_button.config(state=tk.DISABLED)

if __name__ == "__main__":
    # 确保在正确的目录中运行
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    root = tk.Tk()
    app = RIFE_GUI(root)
    root.mainloop()