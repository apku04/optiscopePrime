from core.mode_manager import switch_mode
from core.event_bus import event_bus
import asyncio


async def stop_mode_loop(_=None):
    print("[AutoMode] Entered stop mode loop.")
    try:
        print("[AutoMode] in stop mode...")
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        print("[AutoMode] Stop mode cancelled.")


def start_stop_mode(_=None):
    switch_mode(stop_mode_loop())


event_bus.subscribe("stop_mode_entered", start_stop_mode)
