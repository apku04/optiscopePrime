# core/event_bus.py
import asyncio
from collections import defaultdict


class EventBus:
    def __init__(self):
        self._subscribers = defaultdict(list)

    def subscribe(self, event_name, handler):
        self._subscribers[event_name].append(handler)

    async def emit(self, event_name, *args, **kwargs):
        tasks = []
        for handler in self._subscribers[event_name]:
            if asyncio.iscoroutinefunction(handler):
                tasks.append(handler(*args, **kwargs))
            else:
                handler(*args, **kwargs)
        if tasks:
            await asyncio.gather(*tasks)


# THIS IS THE IMPORTANT PART!
event_bus = EventBus()
