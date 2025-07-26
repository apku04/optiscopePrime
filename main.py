import asyncio
from core.event_bus import event_bus
from hardware.oled_display import OLEDDisplay
from hardware.input_manager import InputManager
from core.menu_system import MenuSystem
from hardware.stepper_controller import StepperController
import core.manual_mode
import core.auto_mode
import core.homing
import core.stop_mode


def main():
    menu_oled = OLEDDisplay(i2c_addr=0x3C)
    status_oled = OLEDDisplay(i2c_addr=0x3D)
    menu_system = MenuSystem(menu_oled, status_oled, event_bus)
    input_manager = InputManager(event_bus)
    stepper_ctrl = StepperController(event_bus, azimuth_invert=True, altitude_invert=False, ms_mode=(1, 1))

    print("Telescope menu: Rotate encoder to select, press button to confirm.")
    menu_system.draw_menu()
    menu_system.draw_status("Welcome!")

    loop = asyncio.get_event_loop()
    event_bus.loop = loop

    # 👇 Schedule motor tracking tasks AFTER the event loop starts
    loop.call_soon(stepper_ctrl.start_tasks)

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        print("Exiting menu...")


if __name__ == "__main__":
    main()
