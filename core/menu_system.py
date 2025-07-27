# core/menu_system.py
from config.menu import MENU_ITEMS
from config.fonts import load_fonts
from textwrap import wrap
import time

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

    def draw_status(self, msg, icon=None, animate=False, frame=None):
        """
        Draw a wrapped status message with optional icon and spinner.
        :param msg: str - status message to display
        :param icon: str - e.g. "✓", "⚠", None for no icon
        :param animate: bool - if True, shows a spinner in the corner
        :param frame: int - required for animate, cycles spinner
        """
        spinner_frames = ["-", "\\", "|", "/"]
        if animate and frame is None:
            # Use time-based frame if not supplied
            frame = int(time.time() * 4) % 4

        def draw(draw):
            draw.rectangle((0, 0, 128, 128), outline=0, fill=0)
            # Word-wrap for 18 chars per line, up to 5 lines
            lines = wrap(msg, width=18)
            y = 10
            for line in lines[:5]:
                draw.text((10, y), line, font=font_normal, fill=255)
                y += 12
            if icon:
                draw.text((110, 5), icon, font=font_bold, fill=255)
            if animate:
                spinner = spinner_frames[frame % len(spinner_frames)]
                draw.text((110, 110), spinner, font=font_bold, fill=255)

        self.status_oled.draw(draw)
