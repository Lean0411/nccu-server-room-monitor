#!/usr/bin/env python3
from picamera2 import Picamera2
from datetime import datetime
import time

# 初始化攝影機
picam = Picamera2()
picam.configure(picam.create_preview_configuration())
picam.start()

print("開始攝影機測試，每隔 2 秒拍一張，共 5 張。")

for i in range(5):
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"camera_test_{i+1}_{ts}.jpg"
    picam.capture_file(filename)
    print(f"已儲存：{filename}")
    time.sleep(2)

picam.stop()
print("攝影機測試完成。")
