# core/homing.py
from core.event_bus import event_bus
from core.mode_manager import switch_mode
import asyncio

stepper_ctrl = None  # Set by main.py


async def home_all_axes_and_center():
    # Parallel homing for both axes
    await asyncio.gather(
        stepper_ctrl.home_axis("az"),
        stepper_ctrl.home_axis("alt")
    )
    print("[Homing] Both axes homed.")


async def homing(_=None):
    try:
        await home_all_axes_and_center()
    except asyncio.CancelledError:
        print("[Homing] Homing mode cancelled.")


def start_homing_mode(_=None):
    switch_mode(homing())


# Align the event name with the menu item ("Auto Homing")
event_bus.subscribe("auto_homing_entered", start_homing_mode)
