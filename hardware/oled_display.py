# hardware/oled_display.py
from luma.core.interface.serial import i2c
from luma.oled.device import sh1107


class OLEDDisplay:
    def __init__(self, i2c_addr, width=128, height=128):
        self.device = sh1107(i2c(port=1, address=i2c_addr), width=width, height=height)

    def draw(self, draw_fn):
        from luma.core.render import canvas
        with canvas(self.device) as draw:
            draw_fn(draw)
