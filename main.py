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

    # (Optional) Initial status message, just for boot:
    menu_system.draw_status("Starting up...")

    # 1. Home axes
    await stepper_ctrl.home_axis("az")
    await stepper_ctrl.home_axis("alt")

    # 2. Move to idle
    await stepper_ctrl.goto_steps('az', 11000)
    stepper_ctrl.az_position = 11000
    stepper_ctrl.az_target = 11000
    await stepper_ctrl.goto_steps('alt', 3000)
    stepper_ctrl.alt_position = 3000
    stepper_ctrl.alt_target = 3000

    # 3. Only now, show pot sync message. Do NOT call draw_menu() before sync!
    menu_system.draw_status("Set both pots to\nmatch position,\nthen press OK")

    # 4. Subscribe a one-time handler for OK
    def on_sync_ok(_):
        from hardware.ads1115 import read_azimuth, read_altitude
        az_pot_val = read_azimuth()
        alt_pot_val = read_altitude()
        pot_steps_az = int(az_pot_val * stepper_ctrl.max_steps / 65535)
        pot_steps_alt = int(alt_pot_val * stepper_ctrl.max_steps / 65535)
        stepper_ctrl.az_manual_offset = stepper_ctrl.az_position - pot_steps_az
        stepper_ctrl.alt_manual_offset = stepper_ctrl.alt_position - pot_steps_alt

        # Correct event for unsubscribe
        event_bus.subscribers["sync_ok_pressed"].remove(on_sync_ok)

        menu_system.draw_menu()

    event_bus.subscribe("sync_ok_pressed", on_sync_ok)

    event_bus.loop = asyncio.get_running_loop()
    event_bus.loop.call_soon(stepper_ctrl.start_tasks)

    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("Exiting menu...")


if __name__ == "__main__":
    asyncio.run(main())
