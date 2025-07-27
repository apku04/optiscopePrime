from core.mode_manager import switch_mode
from core.event_bus import event_bus
from hardware.ads1115 import read_azimuth, read_altitude
import asyncio

pot_sub = None  # We'll keep track so we can unsubscribe


async def manual_mode_loop(_=None):
    print("[ManualMode] Entered manual mode loop.")
    try:
        while True:
            az = read_azimuth()
            alt = read_altitude()
            event_bus.emit("pot_changed", ("az", az))
            event_bus.emit("pot_changed", ("alt", alt))
            await asyncio.sleep(0.1)
    except asyncio.CancelledError:
        print("[ManualMode] Manual mode cancelled.")


def on_pot_changed(data):
    axis, value = data
    # Access global stepper_ctrl
    import core.homing
    stepper_ctrl = core.homing.stepper_ctrl
    target = int(value * stepper_ctrl.max_steps / 65535)
    if axis == "az":
        stepper_ctrl.az_target = target
    elif axis == "alt":
        stepper_ctrl.alt_target = target


def start_manual_mode(_=None):
    global pot_sub
    pot_sub = on_pot_changed
    event_bus.subscribe("pot_changed", pot_sub)
    switch_mode(manual_mode_loop())


def stop_manual_mode(_=None):
    global pot_sub
    if pot_sub:
        # Best hygiene: remove listener to avoid conflict in other modes
        if "pot_changed" in event_bus.subscribers and pot_sub in event_bus.subscribers["pot_changed"]:
            event_bus.subscribers["pot_changed"].remove(pot_sub)
        pot_sub = None


event_bus.subscribe("manual_mode_entered", start_manual_mode)
# (Optional) You could subscribe stop_manual_mode to some event like "manual_mode_exited"
