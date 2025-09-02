#!/usr/bin/env python3
import board
import digitalio
import time

print("水位感測器檢測（下拉電阻模式）")
print("=" * 40)

# 測試常用腳位，使用下拉電阻
test_pins = [
    (board.D4, "GPIO 4"),
    (board.D5, "GPIO 5"),
    (board.D6, "GPIO 6"),
    (board.D22, "GPIO 22"),
    (board.D23, "GPIO 23"),
    (board.D24, "GPIO 24"),
    (board.D25, "GPIO 25"),
]

sensors_up = []
sensors_down = []

print("測試上拉與下拉電阻模式...")
print()

for pin, name in test_pins:
    try:
        # 測試上拉電阻
        sensor = digitalio.DigitalInOut(pin)
        sensor.direction = digitalio.Direction.INPUT
        sensor.pull = digitalio.Pull.UP
        value_up = sensor.value
        sensor.deinit()
        
        # 測試下拉電阻
        sensor = digitalio.DigitalInOut(pin)
        sensor.direction = digitalio.Direction.INPUT
        sensor.pull = digitalio.Pull.DOWN
        value_down = sensor.value
        sensors_down.append((sensor, name, value_down))
        
        print(f"{name}:")
        print(f"  上拉模式: {'高' if value_up else '低'}電位")
        print(f"  下拉模式: {'高' if value_down else '低'}電位")
        
        # 如果下拉時是高電位，可能有外部信號
        if value_down:
            print(f"  → 可能有感測器連接！")
        print()
        
    except Exception as e:
        print(f"{name}: 錯誤 - {e}\n")

print("\n持續監測（下拉模式）... 按 Ctrl+C 結束")
print("-" * 40)

try:
    while True:
        has_signal = False
        for sensor, name, _ in sensors_down:
            if sensor.value:
                print(f"\r{name}: 偵測到高電位信號！（可能是水位感測器）", end="")
                has_signal = True
                break
        
        if not has_signal:
            print("\r等待信號中...                                    ", end="")
        
        time.sleep(0.1)
        
except KeyboardInterrupt:
    print("\n\n程式結束")
finally:
    for sensor, _, _ in sensors_down:
        sensor.deinit()