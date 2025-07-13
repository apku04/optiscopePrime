from core.mode_manager import switch_mode
from core.event_bus import event_bus
import asyncio

async def auto_mode_loop(_=None):
    print("[AutoMode] Entered auto mode loop.")
    try:
        while True:
            print("[AutoMode] Running auto mode...")
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        print("[AutoMode] Auto mode cancelled.")

def start_auto_mode(_=None):
    switch_mode(auto_mode_loop())

event_bus.subscribe("auto_mode_entered", start_auto_mode)
