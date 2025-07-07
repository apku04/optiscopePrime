# core/manual_mode.py
from core.event_bus import event_bus


async def manual_mode_loop():
    # ... your main manual mode logic ...
    await event_bus.emit("manual_mode_entered")
    # When pot value changes:
    await event_bus.emit("pot_changed", 1234)
