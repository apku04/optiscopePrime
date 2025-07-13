# hardware/ads1115.py

import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

i2c = busio.I2C(board.SCL, board.SDA)
ads = ADS.ADS1115(i2c, address=0x48)


def read_pot_menu():
    chan_menu = AnalogIn(ads, ADS.P0)  # <--- Create a new AnalogIn object each time!
    raw = chan_menu.value
    scaled = int(raw * 65535 / 32767)
    return max(0, min(scaled, 65535))
