from core.mode_manager import switch_mode
from core.event_bus import event_bus
from hardware.ads1115 import read_azimuth, read_altitude
import asyncio


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


def start_manual_mode(_=None):
    switch_mode(manual_mode_loop())


event_bus.subscribe("manual_mode_entered", start_manual_mode)
