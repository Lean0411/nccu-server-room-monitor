#!/usr/bin/env python3
"""
測試火焰感測器敏感度調整
"""

import time
import board
import digitalio
from datetime import datetime

# 初始化火焰感測器
flame = digitalio.DigitalInOut(board.D27)
flame.direction = digitalio.Direction.INPUT

fire_count = 0
fire_threshold = 3
detection_log = []

print("火焰感測器敏感度測試")
print(f"需要連續 {fire_threshold} 次偵測到火焰才會觸發警報")
print("按 Ctrl+C 結束測試\n")

try:
    while True:
        # 讀取感測器
        fire_detected = not flame.value
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        if fire_detected:
            fire_count += 1
            print(f"[{timestamp}] 🔥 偵測到火焰信號 ({fire_count}/{fire_threshold})")
            detection_log.append(f"{timestamp} - 火焰信號")
            
            if fire_count >= fire_threshold:
                print(f"[{timestamp}] 🚨 警報觸發！連續偵測到 {fire_threshold} 次火焰")
                fire_count = 0  # 重置計數器
        else:
            if fire_count > 0:
                print(f"[{timestamp}] ✓ 無火焰信號，計數器重置")
                fire_count = 0
        
        time.sleep(1)
        
except KeyboardInterrupt:
    print("\n\n測試結束")
    print(f"總共記錄了 {len(detection_log)} 次火焰偵測信號")
    if detection_log:
        print("\n偵測記錄：")
        for log in detection_log[-10:]:  # 顯示最後10筆
            print(f"  {log}")