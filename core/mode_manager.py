# core/mode_manager.py
import asyncio

current_mode_task = None


def switch_mode(new_mode_coro):
    global current_mode_task
    if current_mode_task is not None:
        current_mode_task.cancel()
    current_mode_task = asyncio.create_task(new_mode_coro)
