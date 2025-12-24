import pyautogui
import time

print("鼠标自动点击脚本已启动，每2秒点击两下，间隔0.1秒。按 Ctrl+C 停止。")

try:
    while True:
        # 获取当前鼠标位置
        x, y = pyautogui.position()

        # 点击两下，间隔0.1秒
        pyautogui.click(x, y)
        time.sleep(0.1)
        pyautogui.click(x, y)

        # 等待2秒
        time.sleep(2)
except KeyboardInterrupt:
    print("\n脚本已停止。")