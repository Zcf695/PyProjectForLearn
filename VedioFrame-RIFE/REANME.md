# VedioFrame-RIFE

基于hzwer的ECCV2022-RIFE项目的视频帧插值工具，包含训练结果和代码，并提供了GUI界面。

## 项目介绍

VedioFrame-RIFE是一个实时视频帧插值工具，它能够在现有视频帧之间生成高质量的中间帧，从而提高视频的帧率和流畅度。本项目基于hzwer的ECCV2022-RIFE项目(https://github.com/hzwer/ECCV2022-RIFE)，并添加了友好的GUI界面，方便用户使用。

## 功能特点

- 支持视频和图像的帧插值
- 提供命令行工具和GUI界面
- 支持多种插值倍数(2x, 4x, 8x, 16x, 32x)
- 支持自定义帧率
- 保留原始视频的音频
- 支持多种模型版本(HD, HDv2, HDv3)

## 安装说明

### 环境要求

- Python 3.6+
- PyTorch 1.6+
- CUDA支持(推荐)

### 安装步骤

1. 克隆或下载项目文件

2. 安装依赖包

```bash
pip install -r requirements.txt
```

依赖包包括：
- numpy>=1.16, <=1.23.5
- tqdm>=4.35.0
- sk-video>=1.1.10
- torch>=1.6.0
- opencv-python>=4.1.2
- moviepy>=1.0.3
- torchvision>=0.7.0

## 使用方法

### GUI界面

运行GUI界面非常简单，只需执行以下命令：

```bash
python rife_gui.py
```

GUI界面提供了以下功能：
- 选择输入和输出视频文件
- 设置插值倍数(2x, 4x, 8x, 16x, 32x)
- 设置缩放因子(0.25, 0.5, 1.0, 2.0, 4.0)
- 自定义输出帧率
- 显示处理进度

### 命令行工具

#### 视频插值

```bash
python inference_video.py --input input.mp4 --output output.mp4 --exp 4
```

参数说明：
- --input: 输入视频文件路径
- --output: 输出视频文件路径
- --exp: 插值倍数，2^exp (默认值: 4，即16x)
- --scale: 缩放因子 (默认值: 1.0)
- --fps: 自定义帧率 (可选)

#### 图像插值

```bash
python inference_img.py --img img1.png img2.png --exp 4
```

参数说明：
- --img: 输入的两张图像文件路径
- --exp: 插值倍数，2^exp (默认值: 4，即16x)
- --ratio: 插值比例 (0-1之间，默认值: 0)
- --model: 模型文件目录 (默认值: train_log)

## 项目结构

```
VedioFrame-RIFE/
├── dataset.py          # 数据集处理
├── inference_img.py    # 图像插值脚本
├── inference_video.py  # 视频插值脚本
├── model/              # 模型定义
│   ├── IFNet.py        # 图像特征网络
│   ├── RIFE.py         # 主要模型
│   ├── loss.py         # 损失函数
│   └── warplayer.py    # 光流战争层
├── rife_gui.py         # GUI界面
├── train.py            # 训练脚本
├── train_log/          # 训练日志和模型文件
│   ├── IFNet_HDv3.py   # HDv3模型
│   ├── RIFE_HDv3.py    # HDv3模型封装
│   └── flownet.pkl     # 预训练模型
└── requirements.txt    # 依赖文件
```

## 模型说明

项目支持多种模型版本：
- RIFE: 基础版本
- RIFE_HD: HD版本
- RIFE_HDv2: HDv2版本
- RIFE_HDv3: HDv3版本(默认使用)

程序会自动检测并加载最新版本的模型。

## 注意事项

1. 视频处理需要较大的显存，建议使用GPU加速
2. 处理高分辨率视频时，可以适当降低缩放因子以提高处理速度
3. 处理时间取决于视频长度、分辨率和插值倍数
4. 确保安装了FFmpeg以支持音频处理

## 示例

### 视频插值示例

```bash
# 将视频插值为16x帧率
python inference_video.py --input input.mp4 --output output.mp4 --exp 4

# 将视频插值为60fps
python inference_video.py --input input.mp4 --output output.mp4 --fps 60
```

### 图像插值示例

```bash
# 在两张图像之间生成16张中间帧
python inference_img.py --img img1.png img2.png --exp 4
```

## 许可证

本项目基于MIT许可证。

## 致谢

感谢hzwer及其团队开发的ECCV2022-RIFE项目，为本项目提供了核心算法支持。
