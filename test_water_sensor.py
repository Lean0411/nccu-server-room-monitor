#!/usr/bin/env python3
import board
import digitalio
import time

print("水位感測器接線檢測程式")
print("=" * 40)

# 測試常用的GPIO腳位
test_pins = [
    (board.D4, "GPIO 4"),
    (board.D5, "GPIO 5"), 
    (board.D6, "GPIO 6"),
    (board.D22, "GPIO 22"),
    (board.D23, "GPIO 23"),
    (board.D24, "GPIO 24"),
    (board.D25, "GPIO 25"),
]

print("正在檢查可能的水位感測器接腳...")
print("如果水位感測器已正確接線，當感測器接觸到水時應該會顯示變化")
print()

# 初始化所有測試腳位
sensors = []
for pin, name in test_pins:
    try:
        sensor = digitalio.DigitalInOut(pin)
        sensor.direction = digitalio.Direction.INPUT
        sensor.pull = digitalio.Pull.UP  # 使用內部上拉電阻
        sensors.append((sensor, name))
        print(f"✓ {name} 初始化成功")
    except Exception as e:
        print(f"✗ {name} 初始化失敗: {e}")

print("\n開始監測... (按 Ctrl+C 結束)")
print("-" * 40)

try:
    while True:
        output = []
        for sensor, name in sensors:
            # 一般水位感測器：低電位(0)表示偵測到水
            value = sensor.value
            status = "無水" if value else "偵測到水！"
            output.append(f"{name}: {status} (值={int(value)})")
        
        # 清除並更新顯示
        print("\033[{}A".format(len(sensors)), end="")  # 移動游標上移
        for line in output:
            print(f"\r{line:<40}")
        
        time.sleep(0.1)
        
except KeyboardInterrupt:
    print("\n\n程式結束")
finally:
    # 清理資源
    for sensor, _ in sensors:
        sensor.deinit()