# -*- coding: utf-8 -*-
#!/usr/bin/env python3
import time
import RPi.GPIO as GPIO
from datetime import datetime

GPIO.setmode(GPIO.BCM)
GPIO.setup(17, GPIO.IN)  # MQ-2 DO
GPIO.setup(27, GPIO.IN)  # Flame DO

print("開始測試：MQ-2 與火焰感測器（Ctrl+C 結束）")
try:
    while True:
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        smoke = not GPIO.input(17)  # LOW→有煙霧
        fire  = not GPIO.input(27)  # LOW→有火焰
        print(f"[{ts}] 煙霧={'YES' if smoke else 'NO '}  火焰={'YES' if fire else 'NO '}")
        time.sleep(1)
finally:
    GPIO.cleanup()
