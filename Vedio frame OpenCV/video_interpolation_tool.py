import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import cv2
import numpy as np
import os
from PIL import Image, ImageTk
import threading
import time
import subprocess
import tempfile


class VideoFrameInterpolationApp:
    def __init__(self, root):
        self.root = root
        self.root.title("视频插帧工具")
        self.root.geometry("800x600")
        self.root.resizable(True, True)

        # 初始化变量
        self.video_path = None
        self.output_path = None
        self.cap = None
        self.total_frames = 0
        self.fps = 0
        self.width = 0
        self.height = 0
        self.is_processing = False
        self.current_frame = None

        # 创建GUI
        self.create_widgets()

    def create_widgets(self):
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)

        # 标题
        title_label = ttk.Label(main_frame, text="视频插帧工具", font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))

        # 视频选择部分
        video_frame = ttk.LabelFrame(main_frame, text="视频文件", padding="10")
        video_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        video_frame.columnconfigure(1, weight=1)

        ttk.Label(video_frame, text="输入视频:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.video_path_entry = ttk.Entry(video_frame, state="readonly")
        self.video_path_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        ttk.Button(video_frame, text="浏览", command=self.browse_video).grid(row=0, column=2)

        ttk.Label(video_frame, text="输出路径:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10))
        self.output_path_entry = ttk.Entry(video_frame, state="readonly")
        self.output_path_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        ttk.Button(video_frame, text="浏览", command=self.browse_output).grid(row=1, column=2)

        # 视频信息部分
        info_frame = ttk.LabelFrame(main_frame, text="视频信息", padding="10")
        info_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))

        self.info_text = tk.Text(info_frame, height=4, width=80, state="disabled")
        self.info_text.grid(row=0, column=0, sticky=(tk.W, tk.E))

        # 参数设置部分
        params_frame = ttk.LabelFrame(main_frame, text="插帧参数", padding="10")
        params_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))

        ttk.Label(params_frame, text="插帧倍数:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.interpolation_factor = tk.StringVar(value="2")
        interpolation_spinbox = ttk.Spinbox(params_frame, from_=2, to=10, textvariable=self.interpolation_factor,
                                            width=10)
        interpolation_spinbox.grid(row=0, column=1, sticky=tk.W, padx=(0, 20))

        ttk.Label(params_frame, text="插帧方法:").grid(row=0, column=2, sticky=tk.W, padx=(0, 10))
        self.interpolation_method = tk.StringVar(value="linear")
        method_combo = ttk.Combobox(params_frame, textvariable=self.interpolation_method,
                                    values=["linear", "motion_estimated"], state="readonly", width=15)
        method_combo.grid(row=0, column=3, sticky=tk.W)

        # 预览部分 - 使用Canvas实现居中预览
        preview_frame = ttk.LabelFrame(main_frame, text="视频预览", padding="10")
        preview_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(4, weight=1)

        # 使用Canvas来居中显示预览图像
        self.preview_canvas = tk.Canvas(preview_frame, bg="white", highlightthickness=1, highlightbackground="gray")
        self.preview_canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 在Canvas上添加提示文本
        self.preview_text = self.preview_canvas.create_text(
            200, 150,
            text="请选择视频文件以预览",
            font=("Arial", 12),
            fill="gray"
        )

        # 控制按钮部分
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=5, column=0, columnspan=3, pady=(10, 0))

        self.process_button = ttk.Button(button_frame, text="开始插帧", command=self.start_interpolation)
        self.process_button.grid(row=0, column=0, padx=(0, 10))

        self.cancel_button = ttk.Button(button_frame, text="取消", command=self.cancel_processing, state="disabled")
        self.cancel_button.grid(row=0, column=1, padx=(0, 10))

        # 进度条
        self.progress = ttk.Progressbar(main_frame, mode='determinate')
        self.progress.grid(row=6, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))

        # 状态标签
        self.status_label = ttk.Label(main_frame, text="就绪")
        self.status_label.grid(row=7, column=0, columnspan=3, sticky=tk.W, pady=(5, 0))

        # 绑定Canvas大小变化事件
        self.preview_canvas.bind("<Configure>", self.on_canvas_resize)

    def on_canvas_resize(self, event):
        """当Canvas大小变化时，重新调整预览图像位置"""
        if hasattr(self, 'current_image_id'):
            self.center_image_on_canvas()

    def center_image_on_canvas(self):
        """将图像居中显示在Canvas上"""
        if not hasattr(self, 'current_photo_image'):
            return

        # 获取Canvas尺寸
        canvas_width = self.preview_canvas.winfo_width()
        canvas_height = self.preview_canvas.winfo_height()

        # 获取图像尺寸
        img_width = self.current_photo_image.width()
        img_height = self.current_photo_image.height()

        # 计算居中位置
        x = (canvas_width - img_width) // 2
        y = (canvas_height - img_height) // 2

        # 更新图像位置
        self.preview_canvas.coords(self.current_image_id, x, y)

    def browse_video(self):
        file_path = filedialog.askopenfilename(
            title="选择视频文件",
            filetypes=[("视频文件", "*.mp4 *.avi *.mov *.mkv *.wmv"), ("所有文件", "*.*")]
        )
        if file_path:
            self.video_path = file_path
            self.video_path_entry.config(state="normal")
            self.video_path_entry.delete(0, tk.END)
            self.video_path_entry.insert(0, file_path)
            self.video_path_entry.config(state="readonly")
            self.load_video_info()

    def browse_output(self):
        file_path = filedialog.asksaveasfilename(
            title="保存插帧视频",
            defaultextension=".mp4",
            filetypes=[("MP4文件", "*.mp4"), ("AVI文件", "*.avi"), ("所有文件", "*.*")]
        )
        if file_path:
            self.output_path = file_path
            self.output_path_entry.config(state="normal")
            self.output_path_entry.delete(0, tk.END)
            self.output_path_entry.insert(0, file_path)
            self.output_path_entry.config(state="readonly")

    def load_video_info(self):
        if not self.video_path:
            return

        self.cap = cv2.VideoCapture(self.video_path)
        if not self.cap.isOpened():
            messagebox.showerror("错误", "无法打开视频文件")
            return

        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # 显示视频信息
        self.info_text.config(state="normal")
        self.info_text.delete(1.0, tk.END)
        info = f"文件: {os.path.basename(self.video_path)}\n"
        info += f"分辨率: {self.width} x {self.height}\n"
        info += f"帧率: {self.fps:.2f} FPS\n"
        info += f"总帧数: {self.total_frames}"
        self.info_text.insert(1.0, info)
        self.info_text.config(state="disabled")

        # 显示第一帧作为预览
        self.show_frame_preview(0)

    def show_frame_preview(self, frame_num):
        if not self.cap:
            return

        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
        ret, frame = self.cap.read()
        if ret:
            # 隐藏提示文本
            self.preview_canvas.itemconfig(self.preview_text, state="hidden")

            # 获取Canvas尺寸
            canvas_width = self.preview_canvas.winfo_width()
            canvas_height = self.preview_canvas.winfo_height()

            # 计算适应Canvas大小的图像尺寸，保持宽高比
            img_ratio = self.width / self.height
            canvas_ratio = canvas_width / canvas_height if canvas_height > 0 else 1

            if canvas_ratio > img_ratio:
                # 以高度为基准
                display_height = min(canvas_height, self.height)
                display_width = int(display_height * img_ratio)
            else:
                # 以宽度为基准
                display_width = min(canvas_width, self.width)
                display_height = int(display_width / img_ratio)

            # 调整图像大小
            frame_resized = cv2.resize(frame, (display_width, display_height))

            # 转换颜色空间 BGR -> RGB
            frame_rgb = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)

            # 转换为PIL图像
            img = Image.fromarray(frame_rgb)
            self.current_photo_image = ImageTk.PhotoImage(image=img)

            # 清除Canvas上的旧图像
            if hasattr(self, 'current_image_id'):
                self.preview_canvas.delete(self.current_image_id)

            # 计算居中位置
            x = (canvas_width - display_width) // 2
            y = (canvas_height - display_height) // 2

            # 在Canvas上显示图像
            self.current_image_id = self.preview_canvas.create_image(
                x, y,
                anchor=tk.NW,
                image=self.current_photo_image
            )

            self.current_frame = frame

    def linear_interpolation(self, frame1, frame2, alpha):
        """线性插值方法"""
        return cv2.addWeighted(frame1, 1 - alpha, frame2, alpha, 0)

    def motion_estimated_interpolation(self, frame1, frame2):
        """基于运动估计的插值方法"""
        # 转换为灰度图像
        gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)

        # 计算光流
        flow = cv2.calcOpticalFlowFarneback(gray1, gray2, None, 0.5, 3, 15, 3, 5, 1.2, 0)

        # 创建中间帧
        h, w = flow.shape[:2]
        flow_map = flow.copy()
        flow_map[:, :, 0] += np.arange(w)
        flow_map[:, :, 1] += np.arange(h)[:, np.newaxis]

        # 使用重映射生成中间帧
        interpolated_frame = cv2.remap(frame1, flow_map, None, cv2.INTER_LINEAR)

        return interpolated_frame

    def interpolate_frames(self, frame1, frame2, factor, method):
        """在两个帧之间生成插值帧"""
        interpolated_frames = []

        if method == "linear":
            for i in range(1, factor):
                alpha = i / factor
                interpolated_frame = self.linear_interpolation(frame1, frame2, alpha)
                interpolated_frames.append(interpolated_frame)
        elif method == "motion_estimated":
            # 对于运动估计，我们只生成一帧中间帧
            if factor == 2:
                interpolated_frame = self.motion_estimated_interpolation(frame1, frame2)
                interpolated_frames.append(interpolated_frame)
            else:
                # 对于更高的倍数，使用线性插值作为备选
                for i in range(1, factor):
                    alpha = i / factor
                    interpolated_frame = self.linear_interpolation(frame1, frame2, alpha)
                    interpolated_frames.append(interpolated_frame)

        return interpolated_frames

    def add_audio_to_video(self, video_without_audio, original_video, output_video):
        """使用FFmpeg将原始视频的音频添加到处理后的视频中"""
        try:
            # 检查FFmpeg是否可用
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True, encoding='utf-8', errors='ignore')

            # 构建FFmpeg命令
            cmd = [
                "ffmpeg",
                "-y",  # 覆盖输出文件
                "-i", video_without_audio,  # 输入无音频视频
                "-i", original_video,  # 输入原始视频（用于提取音频）
                "-c:v", "copy",  # 复制视频流
                "-c:a", "aac",  # 使用AAC编码音频
                "-map", "0:v:0",  # 使用第一个输入文件的视频流
                "-map", "1:a:0?",  # 使用第二个输入文件的音频流（如果存在）
                "-shortest",  # 以最短的流为准
                output_video
            ]

            # 执行命令，指定编码为UTF-8
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, encoding='utf-8', errors='ignore')
            return True
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print(f"添加音频失败: {e}")
            return False

    def process_video(self):
        """处理视频的主函数"""
        try:
            if not self.video_path or not self.output_path:
                messagebox.showerror("错误", "请选择输入和输出文件")
                return

            # 打开视频
            cap = cv2.VideoCapture(self.video_path)
            if not cap.isOpened():
                messagebox.showerror("错误", "无法打开输入视频")
                return

            # 获取视频参数
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            # 计算插帧后的参数
            factor = int(self.interpolation_factor.get())
            new_fps = fps * factor
            new_total_frames = (total_frames - 1) * factor + 1

            # 创建临时文件用于存储无音频的视频
            temp_dir = tempfile.gettempdir()
            temp_video_path = os.path.join(temp_dir, f"temp_interpolated_{int(time.time())}.mp4")

            # 设置输出视频（临时文件）
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(temp_video_path, fourcc, new_fps, (width, height))

            # 读取第一帧
            ret, prev_frame = cap.read()
            if not ret:
                messagebox.showerror("错误", "无法读取视频帧")
                return

            # 写入第一帧
            out.write(prev_frame)

            # 处理进度
            processed_frames = 0

            # 处理每一帧
            while self.is_processing:
                ret, curr_frame = cap.read()
                if not ret:
                    break

                # 生成插值帧
                interpolated_frames = self.interpolate_frames(
                    prev_frame, curr_frame, factor, self.interpolation_method.get()
                )

                # 写入插值帧
                for frame in interpolated_frames:
                    out.write(frame)

                # 写入当前帧
                out.write(curr_frame)

                # 更新进度
                processed_frames += 1
                progress = (processed_frames / (total_frames - 1)) * 100
                self.progress['value'] = progress
                self.status_label.config(text=f"处理中: {processed_frames}/{total_frames - 1} 帧")

                # 更新预览
                if processed_frames % 10 == 0:  # 每10帧更新一次预览
                    self.show_processing_preview(curr_frame)

                prev_frame = curr_frame

                # 检查是否取消
                if not self.is_processing:
                    break

            # 释放资源
            cap.release()
            out.release()

            if self.is_processing:
                # 添加音频到处理后的视频
                self.status_label.config(text="正在添加音频...")
                if self.add_audio_to_video(temp_video_path, self.video_path, self.output_path):
                    self.status_label.config(text=f"完成! 输出文件: {self.output_path}")
                    messagebox.showinfo("完成", f"视频插帧完成!\n输出文件: {self.output_path}")
                else:
                    # 如果添加音频失败，直接使用无音频视频
                    import shutil
                    shutil.copy2(temp_video_path, self.output_path)
                    self.status_label.config(text=f"完成! 输出文件: {self.output_path} (无音频)")
                    messagebox.showwarning("完成", f"视频插帧完成但无法添加音频!\n输出文件: {self.output_path}")

                # 删除临时文件
                if os.path.exists(temp_video_path):
                    os.remove(temp_video_path)
            else:
                self.status_label.config(text="已取消")
                # 删除临时文件
                if os.path.exists(temp_video_path):
                    os.remove(temp_video_path)

        except Exception as e:
            messagebox.showerror("错误", f"处理过程中发生错误: {str(e)}")
            self.status_label.config(text="错误")
        finally:
            self.is_processing = False
            self.process_button.config(state="normal")
            self.cancel_button.config(state="disabled")
            self.progress['value'] = 0

    def show_processing_preview(self, frame):
        """在预览中显示处理中的帧"""
        # 获取Canvas尺寸
        canvas_width = self.preview_canvas.winfo_width()
        canvas_height = self.preview_canvas.winfo_height()

        # 计算适应Canvas大小的图像尺寸，保持宽高比
        img_ratio = frame.shape[1] / frame.shape[0]
        canvas_ratio = canvas_width / canvas_height if canvas_height > 0 else 1

        if canvas_ratio > img_ratio:
            # 以高度为基准
            display_height = min(canvas_height, frame.shape[0])
            display_width = int(display_height * img_ratio)
        else:
            # 以宽度为基准
            display_width = min(canvas_width, frame.shape[1])
            display_height = int(display_width / img_ratio)

        # 调整图像大小
        frame_resized = cv2.resize(frame, (display_width, display_height))

        # 转换颜色空间 BGR -> RGB
        frame_rgb = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)

        # 转换为PIL图像
        img = Image.fromarray(frame_rgb)
        photo_image = ImageTk.PhotoImage(image=img)

        # 清除Canvas上的旧图像
        if hasattr(self, 'current_image_id'):
            self.preview_canvas.delete(self.current_image_id)

        # 计算居中位置
        x = (canvas_width - display_width) // 2
        y = (canvas_height - display_height) // 2

        # 在Canvas上显示图像
        self.current_image_id = self.preview_canvas.create_image(
            x, y,
            anchor=tk.NW,
            image=photo_image
        )

        # 保存引用防止垃圾回收
        self.current_photo_image = photo_image

    def start_interpolation(self):
        """开始插帧处理"""
        if not self.video_path:
            messagebox.showerror("错误", "请先选择输入视频")
            return

        if not self.output_path:
            messagebox.showerror("错误", "请先选择输出路径")
            return

        self.is_processing = True
        self.process_button.config(state="disabled")
        self.cancel_button.config(state="normal")

        # 在新线程中处理视频
        thread = threading.Thread(target=self.process_video)
        thread.daemon = True
        thread.start()

    def cancel_processing(self):
        """取消处理"""
        self.is_processing = False
        self.cancel_button.config(state="disabled")


if __name__ == "__main__":
    root = tk.Tk()
    app = VideoFrameInterpolationApp(root)
    root.mainloop()
