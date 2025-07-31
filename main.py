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


async def main():
    menu_oled = OLEDDisplay(i2c_addr=0x3C)
    status_oled = OLEDDisplay(i2c_addr=0x3D)
    menu_system = MenuSystem(menu_oled, status_oled, event_bus)
    input_manager = InputManager(event_bus)
    stepper_ctrl = StepperController(event_bus, azimuth_invert=True, altitude_invert=False, ms_mode=(1, 1))
    core.homing.stepper_ctrl = stepper_ctrl

    # Run homing routines BEFORE enabling menu/motion

    print("Telescope menu: Rotate encoder to select, press button to confirm.")
    menu_system.draw_status("Telescope menu:\nRotate encoder to select,\npress button to confirm.")
    menu_system.draw_menu()

    await stepper_ctrl.home_axis("az")
    stepper_ctrl.az_target = 11000
    await stepper_ctrl.home_axis("alt")
    stepper_ctrl.alt_target = 3000

    event_bus.loop = asyncio.get_running_loop()
    event_bus.loop.call_soon(stepper_ctrl.start_tasks)

    # Main loop
    try:
        while True:
            await asyncio.sleep(1)  # keeps the main coroutine alive
    except KeyboardInterrupt:
        print("Exiting menu...")


if __name__ == "__main__":
    asyncio.run(main())
