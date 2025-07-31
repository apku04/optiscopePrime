from core.mode_manager import switch_mode
from core.event_bus import event_bus
from hardware.ads1115 import read_azimuth, read_altitude
import asyncio

pot_sub = None  # We'll keep track so we can unsubscribe

# Store the last pot value for each axis (for deadband logic)
last_pot_az = None
last_pot_alt = None
POT_DEADBAND = 20  # Change this as needed for your pots


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
    global last_pot_az, last_pot_alt
    axis, value = data
    import core.homing
    stepper_ctrl = core.homing.stepper_ctrl

    # Map pot value to step range
    pot_steps = int(value * stepper_ctrl.max_steps / 65535)
    if axis == "az":
        # Only update if user really turned the pot (deadband)
        if last_pot_az is None or abs(value - last_pot_az) > POT_DEADBAND:
            target = pot_steps + getattr(stepper_ctrl, 'az_manual_offset', 0)
            target = max(0, min(target, stepper_ctrl.max_steps))
            stepper_ctrl.az_target = target
            last_pot_az = value
    elif axis == "alt":
        if last_pot_alt is None or abs(value - last_pot_alt) > POT_DEADBAND:
            target = pot_steps + getattr(stepper_ctrl, 'alt_manual_offset', 0)
            target = max(0, min(target, stepper_ctrl.max_steps))
            stepper_ctrl.alt_target = target
            last_pot_alt = value


def start_manual_mode(_=None):
    global pot_sub, last_pot_az, last_pot_alt
    # Reset deadband memory when entering manual mode
    last_pot_az = None
    last_pot_alt = None
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
# Optionally: event_bus.subscribe("manual_mode_exited", stop_manual_mode)
