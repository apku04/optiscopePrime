# hardware/display_manager.py
from core.event_bus import event_bus


def show_manual_mode():
    print("Display: Manual mode ON")


event_bus.subscribe("manual_mode_entered", show_manual_mode)
