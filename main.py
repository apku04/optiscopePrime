import asyncio
import time
import threading

from core.event_bus import event_bus
from hardware.oled_display import OLEDDisplay
from hardware.input_manager import InputManager
from core.menu_system import MenuSystem
import core.manual_mode
import core.auto_mode


def blocking_input_poll(input_manager):
    while True:
        input_manager.poll()
        time.sleep(0.1)


def main():
    menu_oled = OLEDDisplay(i2c_addr=0x3C)
    status_oled = OLEDDisplay(i2c_addr=0x3D)
    menu_system = MenuSystem(menu_oled, status_oled, event_bus, pot_min=0, pot_max=12000)
    input_manager = InputManager(event_bus)

    print("Telescope menu: Rotate pot to select, press button to confirm.")
    menu_system.draw_menu()
    menu_system.draw_status("Welcome!")

    loop = asyncio.get_event_loop()
    event_bus.loop = loop

    poll_thread = threading.Thread(target=blocking_input_poll, args=(input_manager,), daemon=True)
    poll_thread.start()
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        print("Exiting menu...")


if __name__ == "__main__":
    main()
