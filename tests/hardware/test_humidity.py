import time
import board
import RPi.GPIO as GPIO
import src.core.sensors as sensors
from adafruit_ahtx0 import AHTx0

# Create sensor object, communicating over the board's default I2C bus
i2c = board.I2C()  # uses board.SCL and board.SDA
sensor = sensors.AHTSensor()

print("開始測試：AHT 溫濕度感測器（Ctrl+C 結束）")
try:
    while True:
        (temperature, relative_humidity) =(sensor.read_temperature(), sensor.read_humidity())
        print("\nTemperature: %0.1f C" % temperature)
        print("Humidity: %0.1f %%" % relative_humidity)
        time.sleep(2)
except KeyboardInterrupt:
    print("\n測試結束")
finally:
    i2c.deinit()
    GPIO.cleanup()