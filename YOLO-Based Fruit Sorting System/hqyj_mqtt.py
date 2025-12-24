import json
import paho.mqtt.client as mqtt
import queue
import logging
from typing import Dict, Any, Union, List, Optional, Callable


class MqttClient:
    """
    一个更加完善和实用的MQTT客户端类

    Features:
    - 支持多个订阅主题
    - 丰富的连接状态回调
    - 线程安全的队列实现
    - 完善的类型提示
    - 日志记录功能
    - 自动重连机制
    - QoS配置支持
    - 更灵活的消息处理
    """

    def __init__(
            self,
            broker_ip: str,
            broker_port: int = 1883,
            subscribe_topics: Optional[Union[str, List[str]]] = None,
            publish_topic: Optional[str] = None,
            timeout_secs: int = 60,
            client_id: Optional[str] = None,
            keepalive: int = 60,
            qos: int = 0,
            username: Optional[str] = None,
            password: Optional[str] = None,
            clean_session: Optional[bool] = None,
    ):
        """
        初始化MQTT客户端

        :param broker_ip: broker的IP地址
        :param broker_port: broker端口，默认1883
        :param subscribe_topics: 订阅话题，可以是字符串或字符串列表
        :param publish_topic: 发布话题
        :param timeout_secs: 连接超时时间(秒)
        :param client_id: 客户端ID，如果为None则自动生成
        :param keepalive: 心跳间隔(秒)
        :param qos: 服务质量等级(0,1,2)
        :param username: 用户名(如果需要认证)
        :param password: 密码(如果需要认证)
        :param clean_session: 是否清除会话
        """
        self.broker_ip = broker_ip
        self.broker_port = broker_port
        self.timeout_secs = timeout_secs
        self.qos = qos
        self.publish_topic = publish_topic

        # 转换订阅主题为列表
        self.subscribe_topics = [subscribe_topics] if isinstance(subscribe_topics, str) else subscribe_topics

        # 创建消息队列
        self.mqtt_queue = queue.Queue()

        # 设置日志
        self._setup_logging()

        # 创建客户端
        self.mqtt_clt = mqtt.Client(
            client_id=client_id,
            clean_session=clean_session
        )

        # 设置认证（如果有）
        if username and password:
            self.mqtt_clt.username_pw_set(username, password)

        # 设置回调
        self._setup_callbacks()

        # 连接broker
        self._connect()

        # 订阅主题
        if self.subscribe_topics:
            self._subscribe()

        # 开启接收循环
        self.mqtt_clt.loop_start()

    def disconnect(self):
        """
        主动断开MQTT连接

        :return: None
        """
        try:
            self.mqtt_clt.loop_stop()  # 停止网络循环
            self.mqtt_clt.disconnect()  # 断开连接
            self.logger.info("MQTT client disconnected successfully")
        except Exception as e:
            self.logger.error(f"Error during disconnection: {e}")
            raise
    def _setup_logging(self):
        """配置日志记录"""
        self.logger = logging.getLogger(__name__)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def _setup_callbacks(self):
        """设置MQTT回调函数"""
        self.mqtt_clt.on_connect = self._on_connect
        self.mqtt_clt.on_disconnect = self._on_disconnect
        self.mqtt_clt.on_message = self._on_message
        self.mqtt_clt.on_subscribe = self._on_subscribe
        self.mqtt_clt.on_publish = self._on_publish
        self.mqtt_clt.on_log = self._on_log

    def _connect(self):
        """连接broker"""
        try:
            self.logger.info(f"Connecting to broker at {self.broker_ip}:{self.broker_port}...")
            self.mqtt_clt.connect(self.broker_ip, self.broker_port, self.timeout_secs)
        except Exception as e:
            self.logger.error(f"Failed to connect to broker: {e}")
            raise

    def _subscribe(self):
        """订阅主题"""
        if not self.subscribe_topics:
            return

        for topic in self.subscribe_topics:
            try:
                self.logger.info(f"Subscribing to topic: {topic} with QoS {self.qos}")
                self.mqtt_clt.subscribe(topic, qos=self.qos)
            except Exception as e:
                self.logger.error(f"Failed to subscribe to topic {topic}: {e}")
                raise

    def add_subscription(self, topic: str, qos: Optional[int] = None):
        """动态添加订阅"""
        qos = qos if qos is not None else self.qos
        try:
            self.mqtt_clt.subscribe(topic, qos=qos)
            if self.subscribe_topics is None:
                self.subscribe_topics = [topic]
            else:
                self.subscribe_topics.append(topic)
            self.logger.info(f"Successfully added subscription to {topic}")
        except Exception as e:
            self.logger.error(f"Failed to add subscription to {topic}: {e}")
            raise

    def remove_subscription(self, topic: str):
        """取消订阅"""
        try:
            self.mqtt_clt.unsubscribe(topic)
            if topic in self.subscribe_topics:
                self.subscribe_topics.remove(topic)
            self.logger.info(f"Successfully unsubscribed from {topic}")
        except Exception as e:
            self.logger.error(f"Failed to unsubscribe from {topic}: {e}")
            raise

    def _on_connect(self, client, userdata, flags, rc):
        """连接回调"""
        if rc == 0:
            self.logger.info("Connected successfully to broker")
        else:
            self.logger.error(f"Connection failed with result code {rc}")

    def _on_disconnect(self, client, userdata, rc):
        """断开连接回调"""
        if rc != 0:
            self.logger.warning(f"Unexpected disconnection (rc={rc}), will attempt to reconnect")
            # 实现自动重连
            try:
                self.mqtt_clt.reconnect()
            except Exception as e:
                self.logger.error(f"Reconnection failed: {e}")

    def _on_message(self, client, userdata, message):
        """消息接收回调"""
        try:
            payload = message.payload.decode('utf-8')
            try:
                msg = json.loads(payload)
            except json.JSONDecodeError:
                msg = payload

            msg_data = {
                "topic": message.topic,
                "payload": msg,
                "qos": message.qos,
                "retain": message.retain
            }
            self.mqtt_queue.put(msg_data)
            self.logger.debug(f"Received message from {message.topic}: {payload}")
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")

    def _on_subscribe(self, client, userdata, mid, granted_qos):
        """订阅成功回调"""
        self.logger.info(f"Subscription confirmed (mid: {mid}, QoS: {granted_qos})")

    def _on_publish(self, client, userdata, mid):
        """发布成功回调"""
        self.logger.debug(f"Message published (mid: {mid})")

    def _on_log(self, client, userdata, level, buf):
        """日志回调"""
        if level == mqtt.MQTT_LOG_ERR:
            self.logger.error(f"MQTT Error: {buf}")
        elif level == mqtt.MQTT_LOG_WARNING:
            self.logger.warning(f"MQTT Warning: {buf}")
        elif level == mqtt.MQTT_LOG_INFO:
            self.logger.info(f"MQTT Info: {buf}")
        else:
            self.logger.debug(f"MQTT Debug: {buf}")

    def publish(self, payload: Union[str, bytes, Dict], topic: Optional[str] = None, qos: Optional[int] = None,
                retain: bool = False):
        """
        发布消息

        :param payload: 消息内容，可以是字符串、字节或字典
        :param topic: 目标主题，如果None则使用初始化时设置的publish_topic
        :param qos: 服务质量等级，如果None则使用初始化时设置的qos
        :param retain: 是否保留消息
        """
        topic = topic if topic is not None else self.publish_topic
        if topic is None:
            self.logger.error("No topic specified for publishing")
            raise ValueError("No topic specified")

        qos = qos if qos is not None else self.qos

        try:
            if isinstance(payload, dict):
                payload = json.dumps(payload)

            self.mqtt_clt.publish(topic, payload=payload, qos=qos, retain=retain)
            self.logger.debug(f"Published message to {topic}: {payload}")
        except Exception as e:
            self.logger.error(f"Failed to publish message to {topic}: {e}")
            raise

    def send_json_msg(self, msg: Dict[str, Any]):
        """
        发送JSON格式的消息(兼容旧代码)

        :param msg: JSON可序列化的字典
        """
        self.publish(msg)

    def control_device(self, key: str, value: Any):
        """
        控制设备(发送键值对消息)

        :param key: 控制键
        :param value: 控制值
        """
        self.send_json_msg({key: value})

    def get_message(self, block: bool = True, timeout: Optional[float] = None) -> Optional[Dict]:
        """
        从队列中获取消息

        :param block: 是否阻塞等待
        :param timeout: 超时时间(秒)
        :return: 消息字典或None
        """
        try:
            return self.mqtt_queue.get(block=block, timeout=timeout)
        except queue.Empty:
            return None

    def clear_message_queue(self):
        """清空消息队列"""
        while not self.mqtt_queue.empty():
            try:
                self.mqtt_queue.get_nowait()
            except queue.Empty:
                break

    def __del__(self):
        """析构函数"""
        try:
            self.mqtt_clt.loop_stop()
            self.mqtt_clt.disconnect()
            self.logger.info("MQTT client disconnected successfully")
        except Exception as e:
            self.logger.error(f"Error during disconnection: {e}")
