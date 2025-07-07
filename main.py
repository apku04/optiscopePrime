import asyncio
# Correct way:
from core.event_bus import event_bus


def show_manual_mode():
    print("Display: Manual mode ON")


async def main_loop():
    # 1. Subscribe before emitting!
    event_bus.subscribe("manual_mode_entered", show_manual_mode)
    # 2. Emit event
    await event_bus.emit("manual_mode_entered")


if __name__ == "__main__":
    asyncio.run(main_loop())
