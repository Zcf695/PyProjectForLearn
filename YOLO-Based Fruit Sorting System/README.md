# YOLO-Based Fruit Sorting System

基于YOLO的水果分类系统，用于自动识别和分类不同成熟度的水果。

## 项目简介

本项目使用YOLO（You Only Look Once）目标检测算法，实现水果成熟度的自动识别和分类。系统可以识别三种成熟度状态：未成熟（raw）、半成熟（half-ripe）和成熟（ripe）。

## 技术栈

- **编程语言**: Python
- **深度学习框架**: Ultralytics YOLO
- **通信协议**: MQTT
- **模型**: YOLOv8n, YOLO11n

## 项目结构

```
YOLO-Based Fruit Sorting System/
├── Pictures/           # 原始图片数据集（包含标签文件）
├── dataset/            # 训练数据集
│   ├── images/         # 图片文件夹
│   └── labels/         # 标签文件夹
├── runs/               # 训练和检测结果
├── venv/               # Python虚拟环境
├── dataset.yaml        # 数据集配置文件
├── hqyj_mqtt.py        # MQTT通信客户端
├── main.py             # 主程序脚本
├── yolo11n.pt          # YOLO11n模型权重
├── yolov8n.pt          # YOLOv8n模型权重
└── README.md           # 项目说明文档
```

## 数据集说明

数据集包含多种水果的图片，每种水果标注了三种成熟度：

- **0: raw** - 未成熟
- **1: half-ripe** - 半成熟
- **2: ripe** - 成熟

数据集配置文件 `dataset.yaml` 定义了数据集的路径和类别信息。

## 模型说明

项目使用两种YOLO模型：

- **yolov8n.pt** - YOLOv8 nano模型，轻量级，适合实时检测
- **yolo11n.pt** - YOLO11 nano模型，最新版本，提供更好的检测性能

## 通信模块

`hqyj_mqtt.py` 实现了MQTT通信功能，可以：

- 连接到MQTT broker
- 订阅和发布主题
- 处理接收到的消息
- 支持认证、QoS配置、自动重连等功能

## 安装和使用

### 安装依赖

```bash
# 安装Ultralytics YOLO
pip install ultralytics

# 安装MQTT客户端
pip install paho-mqtt

# 安装其他依赖
pip install pyautogui
```

### 训练模型

```bash
# 使用yolov8n训练
yolo detect train data=dataset.yaml model=yolov8n.pt epochs=100 imgsz=640

# 或使用yolo11n训练
yolo detect train data=dataset.yaml model=yolo11n.pt epochs=100 imgsz=640
```

### 运行检测

```bash
# 使用训练好的模型进行检测
yolo detect predict model=runs/detect/train/weights/best.pt source=Pictures/
```

## 主程序说明

当前 `main.py` 是一个鼠标自动点击脚本，用于测试。实际使用时，可以修改为水果分类系统的主程序，包括：

1. 从摄像头或图片源获取图像
2. 使用YOLO模型进行检测和分类
3. 通过MQTT发送分类结果
4. 控制执行机构进行水果分拣

## 注意事项

1. 确保已正确配置 `dataset.yaml` 中的数据集路径
2. 训练前确保数据集格式正确（YOLO格式）
3. 根据实际硬件性能选择合适的模型（nano, small, medium等）
4. MQTT通信需要正确配置broker地址和端口

## 扩展建议

1. 添加实时摄像头检测功能
2. 实现与硬件控制系统的集成
3. 优化模型以提高检测精度和速度
4. 添加Web界面用于监控和配置

## 许可证

本项目仅供学习和研究使用。
