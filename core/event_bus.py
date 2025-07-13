import asyncio
import threading

class EventBus:
    def __init__(self):
        self.subscribers = {}
        self.loop = None  # Set in main

    def subscribe(self, event, callback):
        if event not in self.subscribers:
            self.subscribers[event] = []
        self.subscribers[event].append(callback)

    def emit(self, event, data=None):
        # Always run handlers on the main thread's asyncio loop
        if self.loop and threading.current_thread() is not threading.main_thread():
            self.loop.call_soon_threadsafe(self._emit_handlers, event, data)
        else:
            self._emit_handlers(event, data)

    def _emit_handlers(self, event, data=None):
        for cb in self.subscribers.get(event, []):
            if asyncio.iscoroutinefunction(cb):
                asyncio.create_task(cb(data))
            else:
                cb(data)

event_bus = EventBus()
