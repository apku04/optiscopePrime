# hardware/display_manager.py
from core.event_bus import event_bus


def show_auto_mode():
    print("Display: Auto mode ON")


def show_calibration():
    print("Display: Calibration Mode")


def show_auto_homing():
    print("Display: Auto Homing...")


def show_manual_mode():
    print("Display: Manual mode ON")



event_bus.subscribe("manual_mode_entered", show_manual_mode)
event_bus.subscribe("auto_mode_entered", show_auto_mode)
event_bus.subscribe("goto_calibration_entered", show_calibration)
event_bus.subscribe("auto_homing_entered", show_auto_homing)
