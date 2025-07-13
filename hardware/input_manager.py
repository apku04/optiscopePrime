from gpiozero import Button
from hardware.ads1115 import read_pot_menu
import time

OK_BUTTON_PIN = 7


class InputManager:
    def __init__(self, event_bus):
        self.event_bus = event_bus
        self.button = Button(OK_BUTTON_PIN, pull_up=True, bounce_time=0.15)
        self.button.when_pressed = self.on_ok
        self.last_pot_value = None
        self.pot_deadzone = 5000
        self.pot_history = []

    def poll(self):
        pot_value = read_pot_menu()
        self.pot_history.append(pot_value)
        if len(self.pot_history) > 10:   # adjust smoothing here
            self.pot_history.pop(0)
        avg_pot = sum(self.pot_history) // len(self.pot_history)
        self.event_bus.emit("menu_pot_changed", avg_pot)

    def on_ok(self):
        self.event_bus.emit("menu_ok_pressed")


