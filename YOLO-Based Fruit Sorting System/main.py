"""通过yolo实现成熟类型的水果分拣"""
import base64
import cv2
import numpy as np
from ultralytics import YOLO
from hqyj_mqtt import MqttClient
import threading
import time
import queue
from collections import deque


# 推杆状态管理器
class RodController:
    def __init__(self, mqtt_client):
        self.client = mqtt_client
        self.first_rod_busy = False
        self.second_rod_busy = False
        self.third_rod_busy = False
        self.fourth_rod_busy = False
        self.rod_queue = queue.Queue()
        self.running = True

        # 启动推杆控制线程
        self.control_thread = threading.Thread(target=self._process_rod_commands, daemon=True)
        self.control_thread.start()

    def _process_rod_commands(self):
        """处理推杆命令的专用线程"""
        while self.running:
            try:
                # 从队列获取命令，最多等待1秒
                command = self.rod_queue.get(timeout=1)
                rod_type, action = command

                if rod_type == "first":
                    if action == "push":
                        if not self.first_rod_busy:
                            self.first_rod_busy = True
                            print("控制一号推杆推出")
                            self.client.control_device("rod_control", "first_push")
                            # 等待2秒后自动收回
                            threading.Timer(2.0, self._retract_first_rod).start()
                    elif action == "pull":
                        self.first_rod_busy = False
                        print("控制一号推杆收回")
                        self.client.control_device("rod_control", "first_pull")

                elif rod_type == "second":
                    if action == "push":
                        if not self.second_rod_busy:
                            self.second_rod_busy = True
                            print("控制二号推杆推出")
                            self.client.control_device("rod_control", "second_push")
                            # 等待0.5秒后自动收回
                            threading.Timer(0.5, self._retract_second_rod).start()
                    elif action == "pull":
                        self.second_rod_busy = False
                        print("控制二号推杆收回")
                        self.client.control_device("rod_control", "second_pull")

                elif rod_type == "third":
                    if action == "push":
                        if not self.third_rod_busy:
                            self.third_rod_busy = True
                            print("控制三号推杆推出")
                            self.client.control_device("rod_control", "third_push")
                            # 等待0.5秒后自动收回
                            threading.Timer(0.5, self._retract_third_rod).start()
                    elif action == "pull":
                        self.third_rod_busy = False
                        print("控制三号推杆收回")
                        self.client.control_device("rod_control", "third_pull")

                elif rod_type == "fourth":
                    if action == "push":
                        if not self.fourth_rod_busy:
                            self.fourth_rod_busy = True
                            print("控制四号推杆推出")
                            self.client.control_device("rod_control", "fourth_push")
                            # 等待0.5秒后自动收回
                            threading.Timer(0.5, self._retract_fourth_rod).start()
                    elif action == "pull":
                        self.fourth_rod_busy = False
                        print("控制四号推杆收回")
                        self.client.control_device("rod_control", "fourth_pull")

                self.rod_queue.task_done()

            except queue.Empty:
                continue
            except Exception as e:
                print(f"推杆控制错误: {e}")

    def _retract_first_rod(self):
        """自动收回一号推杆"""
        self.control_first_rod("pull")

    def _retract_second_rod(self):
        """自动收回二号推杆"""
        self.control_second_rod("pull")

    def _retract_third_rod(self):
        """自动收回三号推杆"""
        self.control_third_rod("pull")

    def _retract_fourth_rod(self):
        """自动收回四号推杆"""
        self.control_fourth_rod("pull")

    def control_first_rod(self, action):
        """控制一号推杆"""
        if self.running:
            self.rod_queue.put(("first", action))

    def control_second_rod(self, action):
        """控制二号推杆"""
        if self.running:
            self.rod_queue.put(("second", action))

    def control_third_rod(self, action):
        """控制三号推杆"""
        if self.running:
            self.rod_queue.put(("third", action))

    def control_fourth_rod(self, action):
        """控制四号推杆"""
        if self.running:
            self.rod_queue.put(("fourth", action))

    def stop(self):
        """停止推杆控制器"""
        self.running = False
        self.control_thread.join(timeout=2)


# 持续控制一号推杆的推出和收回
def control_fruit_cycle(rod_controller):
    """循环控制一号推杆"""
    while True:
        # 推出一号推杆
        rod_controller.control_first_rod("push")
        # 等待完整周期（2秒推出 + 0.5秒收回 + 0.5秒间隔 = 3秒）
        time.sleep(3)


# 2 成熟水果 1 半成熟水果  0 不成熟水果。

# 实例化mqtt客户端
client = MqttClient('127.0.0.1', 21883, 'bb', 'aa', 60)

# 创建推杆控制器
rod_controller = RodController(client)

# 传送带运行
client.control_device("conveyor", "run")
time.sleep(2)

# 创建线程函数并启动
threading.Thread(target=control_fruit_cycle, args=(rod_controller,), daemon=True).start()

# 加载水果成熟度识别模型
model = YOLO(r"C:/Users/15142/Desktop/fj/runs/detect/train5/weights/best.pt")

# 使用三个缓冲区分别对应三个红外传感器
# firstSwitch_dat: 1号红外传感器后的缓冲区，对应2号推杆
# secondSwitch_dat: 2号红外传感器后的缓冲区，对应3号推杆  
# thirdSwitch_dat: 3号红外传感器后的缓冲区，对应4号推杆
firstSwitch_dat = deque(maxlen=20)  # 限制最大长度防止内存泄漏
secondSwitch_dat = deque(maxlen=20)
thirdSwitch_dat = deque(maxlen=20)

# 检测结果验证机制
detection_confidence_threshold = 0.5  # 置信度阈值

print("系统启动完成，开始水果分拣...")
print("分类规则: 2=成熟水果(二号推杆), 1=半成熟水果(三号推杆), 0=不成熟水果(四号推杆)")
print("红外传感器与推杆对应关系: 1号红外→2号推杆, 2号红外→3号推杆, 3号红外→4号推杆")

# 状态报告计数器
status_counter = 0

# 无限循环的逻辑：
try:
    while True:
        # 获取智能分拣系统的传感器反馈数据
        json_msg = client.mqtt_queue.get()
        print(f"收到原始消息类型: {type(json_msg)}")
        print(f"消息内容: {json_msg}")

        # 分析json数据流
        topic = json_msg.get('topic', '')
        payload = json_msg.get('payload', {})

        print(f"topic: {topic}")
        print(f"payload: {payload}")

        # 处理摄像头数据
        if 'image' in payload:
            imageDat = payload['image']
            try:
                # 将Base64编码解码为原始的二进制数据
                image_data = base64.b64decode(imageDat)
                # 将二进制数据转换为一个np.uint8类型的numpy数组
                image_array = np.frombuffer(image_data, np.uint8)
                # 将numpy数组转换为opencv图像对象
                image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

                if image is not None:
                    # 显示出图像
                    cv2.imshow('Base64 Image', image)
                    cv2.waitKey(1)

                    # yolo模型预测
                    results = model.predict(image, verbose=False, conf=detection_confidence_threshold)
                    if results and len(results) > 0:
                        result = results[0]

                        # 获取预测结果中的类别信息
                        if result.boxes is not None and len(result.boxes) > 0:
                            cls = result.boxes.cls
                            conf = result.boxes.conf  # 获取置信度
                            # 将张量转换为Python数值
                            if len(cls) > 0:
                                # 取第一个检测到的目标的类别
                                cls_value = float(cls[0].item())  # 明确转换为float
                                conf_value = float(conf[0].item())  # 获取置信度

                                # 只存储置信度高于阈值的结果
                                if conf_value >= detection_confidence_threshold:
                                    print(f"检测到类别: {cls_value}, 置信度: {conf_value:.2f}")
                                    # 存储检测结果到第一个缓冲区（对应1号红外传感器）
                                    firstSwitch_dat.append(cls_value)
                                else:
                                    print(f"检测到类别但置信度过低: {cls_value}, 置信度: {conf_value:.2f}")
                            else:
                                print("未检测到任何目标")
                        else:
                            print("未检测到任何目标")
                    else:
                        print("预测失败或没有结果")
            except Exception as e:
                print(f"图像处理错误: {e}")

        # 处理1号红外传感器数据（对应2号推杆）
        if 'first_switch' in payload:
            dat = payload['first_switch']
            # 当传感器检测到物体离开时（dat为False）
            if not dat:
                if firstSwitch_dat:  # 检查缓冲区是否非空
                    dat_true = firstSwitch_dat.popleft()  # 使用popleft获取最早的数据
                    print(f"1号红外传感器触发，检测结果: {dat_true}")

                    # 根据成熟度进行分类
                    if dat_true == 2:  # 成熟水果 - 直接由2号推杆推出
                        print("检测到成熟水果，准备推出二号推杆")
                        rod_controller.control_second_rod("push")
                    elif dat_true == 1:  # 半成熟水果 - 放入2号缓冲区，等待2号红外传感器触发
                        print("检测到半成熟水果，放入2号缓冲区")
                        secondSwitch_dat.append(dat_true)
                    elif dat_true == 0:  # 不成熟水果 - 放入3号缓冲区，等待3号红外传感器触发
                        print("检测到不成熟水果，放入3号缓冲区")
                        thirdSwitch_dat.append(dat_true)
                    else:
                        print(f"未知类别: {dat_true}，跳过处理")
                else:
                    print("1号缓冲区为空，跳过处理")

        # 处理2号红外传感器数据（对应3号推杆）
        if 'second_switch' in payload:
            dat = payload['second_switch']
            # 当传感器检测到物体离开时（dat为False）
            if not dat:
                if secondSwitch_dat:  # 检查缓冲区是否非空
                    dat_true = secondSwitch_dat.popleft()  # 使用popleft获取最早的数据
                    print(f"2号红外传感器触发，检测结果: {dat_true}")

                    # 2号红外传感器只处理半成熟水果
                    if dat_true == 1:  # 半成熟水果 - 由3号推杆推出
                        print("检测到半成熟水果，准备推出三号推杆")
                        rod_controller.control_third_rod("push")
                    else:
                        print(f"2号缓冲区中出现异常类别: {dat_true}，跳过处理")
                else:
                    print("2号缓冲区为空，跳过处理")

        # 处理3号红外传感器数据（对应4号推杆）
        if 'third_switch' in payload:
            dat = payload['third_switch']
            # 当传感器检测到物体离开时（dat为False）
            if not dat:
                if thirdSwitch_dat:  # 检查缓冲区是否非空
                    dat_true = thirdSwitch_dat.popleft()  # 使用popleft获取最早的数据
                    print(f"3号红外传感器触发，检测结果: {dat_true}")

                    # 3号红外传感器只处理不成熟水果
                    if dat_true == 0:  # 不成熟水果 - 由4号推杆推出
                        print("检测到不成熟水果，准备推出四号推杆")
                        rod_controller.control_fourth_rod("push")
                    else:
                        print(f"3号缓冲区中出现异常类别: {dat_true}，跳过处理")
                else:
                    print("3号缓冲区为空，跳过处理")

        # 定期报告状态
        status_counter += 1
        if status_counter >= 20:  # 每20次循环报告一次状态
            print(f"缓冲区状态: 1号={len(firstSwitch_dat)}, 2号={len(secondSwitch_dat)}, 3号={len(thirdSwitch_dat)}")
            status_counter = 0

        # 可选：添加退出条件
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break

        # 添加小延迟，避免过于频繁的处理
        time.sleep(0.05)

except KeyboardInterrupt:
    print("程序被用户中断")

finally:
    # 清理资源
    rod_controller.stop()
    cv2.destroyAllWindows()
    # 停止传送带
    client.control_device("conveyor", "stop")
    print("系统已停止")
