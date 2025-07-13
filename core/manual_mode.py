# core/manual_mode.py
from core.mode_manager import switch_mode
from core.event_bus import event_bus
import asyncio


async def manual_mode_loop(_=None):
    print("[ManualMode] Entered manual mode loop.")
    try:
        while True:
            event_bus.emit("pot_changed", 1234)
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        print("[ManualMode] Manual mode cancelled.")


def start_manual_mode(_=None):
    switch_mode(manual_mode_loop())


event_bus.subscribe("manual_mode_entered", start_manual_mode)
