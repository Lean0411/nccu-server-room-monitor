#!/usr/bin/env python3
from picamera import PiCamera
from time import sleep

camera = PiCamera()
sleep(2)  # 給相機暖機
camera.capture('legacy_test.jpg')
camera.close()
print("已儲存 legacy_test.jpg")
