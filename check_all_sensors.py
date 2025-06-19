#!/usr/bin/env python3
import board
import digitalio
import time

print("綜合感測器檢測報告")
print("=" * 50)

# 已知的感測器
known_sensors = {
    "GPIO 17": "MQ-2 煙霧感測器",
    "GPIO 27": "火焰感測器"
}

# 測試所有GPIO
results = {}

print("\n1. 檢測所有 GPIO 腳位狀態...")
print("-" * 50)

all_gpio = [
    (board.D2, 2), (board.D3, 3), (board.D4, 4), (board.D5, 5),
    (board.D6, 6), (board.D7, 7), (board.D8, 8), (board.D9, 9),
    (board.D10, 10), (board.D11, 11), (board.D12, 12), (board.D13, 13),
    (board.D14, 14), (board.D15, 15), (board.D16, 16), (board.D17, 17),
    (board.D18, 18), (board.D19, 19), (board.D20, 20), (board.D21, 21),
    (board.D22, 22), (board.D23, 23), (board.D24, 24), (board.D25, 25),
    (board.D26, 26), (board.D27, 27)
]

for pin, num in all_gpio:
    try:
        # 測試上拉
        sensor = digitalio.DigitalInOut(pin)
        sensor.direction = digitalio.Direction.INPUT
        sensor.pull = digitalio.Pull.UP
        up_value = sensor.value
        sensor.deinit()
        
        # 測試下拉
        sensor = digitalio.DigitalInOut(pin)
        sensor.direction = digitalio.Direction.INPUT
        sensor.pull = digitalio.Pull.DOWN
        down_value = sensor.value
        sensor.deinit()
        
        # 判斷狀態
        if num in [17, 27]:
            status = f"已使用 - {known_sensors[f'GPIO {num}']}"
        elif not up_value and not down_value:
            status = "強制低電位（可能接地或有強下拉）"
        elif up_value and down_value:
            status = "外部拉高（可能有感測器！）"
        elif up_value and not down_value:
            status = "浮動（未連接）"
        else:
            status = "異常狀態"
            
        results[num] = (up_value, down_value, status)
        
        # 顯示特殊狀態
        if "可能有感測器" in status or "強制低電位" in status:
            print(f"GPIO {num:2d}: {status}")
            
    except Exception as e:
        results[num] = (None, None, f"錯誤: {e}")

print("\n2. 可能的感測器配置推理...")
print("-" * 50)

# GPIO 4 分析
if 4 in results:
    up, down, status = results[4]
    print(f"\nGPIO 4 (Pin 7) - 您說 DHT22 接在這裡：")
    print(f"  上拉: {'高' if up else '低'}, 下拉: {'高' if down else '低'}")
    print(f"  狀態: {status}")
    
    if "強制低電位" in status:
        print("  ⚠️ 問題：腳位被拉低，可能原因：")
        print("     1. DHT22 沒有正確供電")
        print("     2. 接線錯誤（可能接到 GND）")
        print("     3. 感測器故障")
        print("     4. 沒有上拉電阻")

# 找出可能的水位感測器
print("\n可能的水位感測器位置：")
water_candidates = []
for num, (up, down, status) in results.items():
    if num not in [17, 27, 4] and "可能有感測器" in status:
        water_candidates.append(num)
        print(f"  → GPIO {num}")

if not water_candidates:
    print("  未發現明顯的水位感測器信號")

print("\n3. 建議...")
print("-" * 50)
print("• DHT22：請檢查 GPIO 4 的接線，確保：")
print("  - VCC 接到 3.3V")
print("  - GND 接到地線")
print("  - DATA 接到 GPIO 4 + 4.7kΩ 電阻到 VCC")
print("\n• 水位感測器：如果已接線，可能在以下位置：")
for gpio in water_candidates[:3]:
    print(f"  - GPIO {gpio}")
if not water_candidates:
    print("  - 尚未偵測到水位感測器信號")