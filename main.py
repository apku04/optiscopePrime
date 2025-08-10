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

# ---- Optional config for idle positions (falls back to your current numbers) ----
try:
    from config.settings import IDLE_POS
except Exception:
    IDLE_POS = {"az": 11000, "alt": 3000}


def pot_to_steps(pot_value: int, max_steps: int) -> int:
    return int(pot_value * max_steps / 65535)


async def main():
    menu_oled = OLEDDisplay(i2c_addr=0x3C)
    status_oled = OLEDDisplay(i2c_addr=0x3D)
    menu_system = MenuSystem(menu_oled, status_oled, event_bus)
    input_manager = InputManager(event_bus)
    stepper_ctrl = StepperController(event_bus, azimuth_invert=True, altitude_invert=False, ms_mode=(1, 1))
    core.homing.stepper_ctrl = stepper_ctrl

    menu_system.draw_status("Starting up...")

    # 1) Home axes IN PARALLEL (note: phome_axis)
    await asyncio.gather(
        stepper_ctrl.phome_axis("az"),
        stepper_ctrl.phome_axis("alt"),
    )

    # 2) Move to idle IN PARALLEL (note: pgoto_steps)
    await asyncio.gather(
        stepper_ctrl.pgoto_steps("az", IDLE_POS["az"]),
        stepper_ctrl.pgoto_steps("alt", IDLE_POS["alt"]),
    )

    # Sync internal positions/targets
    stepper_ctrl.az_position = IDLE_POS["az"]
    stepper_ctrl.az_target = IDLE_POS["az"]
    stepper_ctrl.alt_position = IDLE_POS["alt"]
    stepper_ctrl.alt_target = IDLE_POS["alt"]

    # 3) Pot sync
    menu_system.draw_status("Set both pots to\nmatch position,\nthen press OK")

    def on_sync_ok(_):
        from hardware.ads1115 import read_azimuth, read_altitude
        az_pot_val = read_azimuth()
        alt_pot_val = read_altitude()

        pot_steps_az = pot_to_steps(az_pot_val, stepper_ctrl.max_steps)
        pot_steps_alt = pot_to_steps(alt_pot_val, stepper_ctrl.max_steps)

        stepper_ctrl.az_manual_offset = stepper_ctrl.az_position - pot_steps_az
        stepper_ctrl.alt_manual_offset = stepper_ctrl.alt_position - pot_steps_alt

        # Unsubscribe (your original approach)
        try:
            event_bus.subscribers["sync_ok_pressed"].remove(on_sync_ok)
        except Exception:
            pass

        menu_system.draw_menu()

    event_bus.subscribe("sync_ok_pressed", on_sync_ok)

    event_bus.loop = asyncio.get_running_loop()
    event_bus.loop.call_soon(stepper_ctrl.start_tasks)

    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("Exiting menu...")
    finally:
        try:
            stepper_ctrl.disable_all()
        except Exception:
            pass
        try:
            getattr(input_manager, "cleanup", lambda: None)()
        except Exception:
            pass
        for dev in (menu_oled, status_oled):
            for meth in ("close", "deinit"):
                try:
                    getattr(dev, meth)()
                except Exception:
                    pass


if __name__ == "__main__":
    asyncio.run(main())
