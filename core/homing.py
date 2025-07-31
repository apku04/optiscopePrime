# core/homing.py

from core.event_bus import event_bus
import asyncio

stepper_ctrl = None  # Set this in main.py after creation


async def home_all_axes_and_center():
    print("[Homing] Homing AZIMUTH axis...")
    await stepper_ctrl.home_axis("az")
    print("[Homing] Homing ALTITUDE axis...")
    await stepper_ctrl.home_axis("alt")
    print("[Homing] Both axes centered.")


async def homing(_=None):
    event_bus.emit("auto_homing_entered")
    try:
        await home_all_axes_and_center()
    except asyncio.CancelledError:
        print("[Homing] Homing mode cancelled.")


def start_homing_mode(_=None):
    from core.mode_manager import switch_mode
    switch_mode(homing())


event_bus.subscribe("homing_mode_entered", start_homing_mode)
