# core/homing.py

from core.mode_manager import switch_mode
from core.event_bus import event_bus
import asyncio


async def homing(_=None):
    print("[Homing] Entered homing mode.")
    try:
        while True:
            event_bus.emit("pot_changed", 1234)
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        print("[Homing] Homing mode cancelled.")


def start_homing_mode(_=None):
    switch_mode(homing())


event_bus.subscribe("homing_mode_entered", start_homing_mode)