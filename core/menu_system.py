# core/menu_system.py
from config.menu import MENU_ITEMS
from config.fonts import load_fonts

font_normal, font_bold = load_fonts()


class MenuSystem:
    def __init__(self, menu_oled, status_oled, event_bus):
        self.menu_oled = menu_oled
        self.status_oled = status_oled
        self.event_bus = event_bus
        self.selected_index = 0
        self.menu_items = MENU_ITEMS
        self.num_items = len(self.menu_items)

        event_bus.subscribe("input.menu.rotary_changed", self.on_rotary)
        event_bus.subscribe("menu_ok_pressed", self.on_ok_pressed)

    def on_rotary(self, direction):
        if direction == "right":
            self.selected_index = (self.selected_index + 1) % self.num_items
        elif direction == "left":
            self.selected_index = (self.selected_index - 1) % self.num_items
        self.draw_menu()

    def on_ok_pressed(self, _=None):
        entry = self.menu_items[self.selected_index]
        self.draw_status(f"Selected: {entry['label']}")
        if "event" in entry:
            self.event_bus.emit(entry["event"])
        else:
            print(f"[Menu] '{entry['label']}' selected (no event attached)")

    def draw_menu(self):
        def draw(draw):
            item_height = 22
            x, y_start = 10, 10
            for i, entry in enumerate(self.menu_items):
                y = y_start + i * item_height
                if i == self.selected_index:
                    bar_height = item_height - 2
                    draw.rectangle((x - 5, y - 2, x + 110, y + bar_height), outline=255, fill=255)
                    draw.text((x, y), entry['label'], font=font_bold, fill=0)
                else:
                    draw.text((x, y), entry['label'], font=font_normal, fill=255)

        self.menu_oled.draw(draw)

    def draw_status(self, msg):
        def draw(draw):
            draw.rectangle((0, 0, 128, 128), outline=0, fill=0)
            draw.text((10, 60), msg, font=font_normal, fill=255)

        self.status_oled.draw(draw)
