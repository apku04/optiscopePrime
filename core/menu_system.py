# core/menu_system.py
import asyncio

from PIL import ImageFont

MENU_ITEMS = [
    "Manual Mode",
    "Auto Mode",
    "Go to Calibration",
    "Auto Homing"
]

try:
    font_normal = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
    font_bold = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 11)
except IOError:
    # fallback if font is not available
    font_normal = ImageFont.load_default()
    font_bold = ImageFont.load_default()


class MenuSystem:
    def __init__(self, menu_oled, status_oled, event_bus, pot_min=0, pot_max=65535):
        self.menu_oled = menu_oled
        self.status_oled = status_oled
        self.event_bus = event_bus
        self.pot_min = pot_min
        self.pot_max = pot_max
        self.selected_index = 0
        self.last_index = -1

        event_bus.subscribe("menu_pot_changed", self.on_pot_change)
        event_bus.subscribe("menu_ok_pressed", self.on_ok_pressed)

    def on_pot_change(self, pot_value):
        num_items = len(MENU_ITEMS)
        idx = int((pot_value - self.pot_min) / (self.pot_max - self.pot_min + 1) * num_items)
        idx = max(0, min(idx, num_items - 1))
        if idx != self.selected_index:
            self.selected_index = idx
            self.draw_menu()

    def on_ok_pressed(self, _=None):
        selected = MENU_ITEMS[self.selected_index]
        self.draw_status(f"Selected: {selected}")
        if selected == "Manual Mode":
            self.event_bus.emit("manual_mode_entered")
        elif selected == "Auto Mode":
            self.event_bus.emit("auto_mode_entered")
        elif selected == "Go to Calibration":
            self.event_bus.emit("goto_calibration_entered")
        elif selected == "Auto Homing":
            self.event_bus.emit("auto_homing_entered")
        else:
            print(f"[Menu] '{selected}' selected (stub endpoint)")

    def draw_menu(self):
        def draw(draw):
            item_height = 22
            x, y_start = 10, 10

            for i, item in enumerate(MENU_ITEMS):
                y = y_start + i * item_height
                if i == self.selected_index:
                    # Highlight bar
                    bar_height = item_height - 2
                    draw.rectangle((x - 5, y - 2, x + 110, y + bar_height), outline=255, fill=255)
                    # Bold font for selection
                    draw.text((x, y), item, font=font_bold, fill=0)
                else:
                    draw.text((x, y), item, font=font_normal, fill=255)

        self.menu_oled.draw(draw)

    def draw_status(self, msg):
        def draw(draw):
            font = ImageFont.load_default()
            draw.rectangle((0, 0, 128, 128), outline=0, fill=0)
            draw.text((10, 60), msg, font=font, fill=255)

        self.status_oled.draw(draw)
