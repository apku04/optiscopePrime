import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

i2c = busio.I2C(board.SCL, board.SDA)
ads = ADS.ADS1115(i2c, address=0x48)

# Persistent channel objects
chan_az = AnalogIn(ads, ADS.P2)
chan_alt = AnalogIn(ads, ADS.P3)


def read_azimuth():
    return chan_az.value


def read_altitude():
    return chan_alt.value
