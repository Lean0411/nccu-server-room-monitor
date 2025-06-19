#!/usr/bin/env python3
import board
import digitalio
import time

print("全GPIO腳位檢測程式")
print("=" * 40)

# 測試所有可用的GPIO腳位（排除已知使用的）
all_pins = [
    (board.D2, "GPIO 2 (I2C SDA)"),
    (board.D3, "GPIO 3 (I2C SCL)"),
    (board.D4, "GPIO 4"),
    (board.D5, "GPIO 5"),
    (board.D6, "GPIO 6"),
    (board.D7, "GPIO 7"),
    (board.D8, "GPIO 8"),
    (board.D9, "GPIO 9"),
    (board.D10, "GPIO 10"),
    (board.D11, "GPIO 11"),
    (board.D12, "GPIO 12"),
    (board.D13, "GPIO 13"),
    (board.D14, "GPIO 14"),
    (board.D15, "GPIO 15"),
    (board.D16, "GPIO 16"),
    # GPIO 17 - 煙霧感測器（跳過）
    (board.D18, "GPIO 18"),
    (board.D19, "GPIO 19"),
    (board.D20, "GPIO 20"),
    (board.D21, "GPIO 21"),
    (board.D22, "GPIO 22"),
    (board.D23, "GPIO 23"),
    (board.D24, "GPIO 24"),
    (board.D25, "GPIO 25"),
    (board.D26, "GPIO 26"),
    # GPIO 27 - 火焰感測器（跳過）
]

print(f"準備測試 {len(all_pins)} 個GPIO腳位...")
print("注意：GPIO 17（煙霧）和 GPIO 27（火焰）已被使用，跳過測試")
print()

# 測試每個腳位
low_pins = []
high_pins = []
error_pins = []

for pin, name in all_pins:
    try:
        sensor = digitalio.DigitalInOut(pin)
        sensor.direction = digitalio.Direction.INPUT
        sensor.pull = digitalio.Pull.UP
        
        # 讀取值
        value = sensor.value
        
        if value:
            high_pins.append(name)
        else:
            low_pins.append(name)
            
        sensor.deinit()
        
    except Exception as e:
        error_pins.append((name, str(e)))

print("\n檢測結果：")
print("-" * 40)

if low_pins:
    print(f"\n低電位腳位（可能接了感測器）：")
    for pin in low_pins:
        print(f"  ✓ {pin} - 低電位（可能是水位感測器！）")
else:
    print("\n沒有發現低電位腳位")

print(f"\n高電位腳位（共 {len(high_pins)} 個）：")
if len(high_pins) > 10:
    print("  " + ", ".join(high_pins[:10]) + "...")
    print(f"  還有 {len(high_pins)-10} 個腳位...")
else:
    for pin in high_pins:
        print(f"  • {pin}")

if error_pins:
    print(f"\n無法測試的腳位：")
    for pin, error in error_pins:
        print(f"  ✗ {pin}: {error}")

print("\n推理結果：")
if low_pins:
    print("發現低電位腳位！水位感測器很可能接在這些腳位上。")
else:
    print("所有腳位都是高電位，可能原因：")
    print("1. 水位感測器尚未接觸到水")
    print("2. 感測器可能需要下拉電阻而非上拉電阻")
    print("3. 感測器可能沒有正確供電")