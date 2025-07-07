# hardware/input_manager.py
from core.event_bus import event_bus


async def handle_pot_change(value):
    # e.g., move motor to new position
    print(f"Pot changed: {value}")


# Subscribe when module initializes
event_bus.subscribe("pot_changed", handle_pot_change)
