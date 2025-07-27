import asyncio
from gpiozero import OutputDevice, DigitalInputDevice, DigitalOutputDevice

class StepperMotor:
    def __init__(self, step_pin, dir_pin, enable_pin, invert_dir=False):
        self.step = OutputDevice(step_pin)
        self.dir = OutputDevice(dir_pin)
        self.enable = OutputDevice(enable_pin)
        self.invert_dir = invert_dir
        self._enabled = False

    def enable_motor(self, enable=True):
        self.enable.value = not enable
        self._enabled = enable

    def set_direction(self, forward):
        self.dir.value = forward ^ self.invert_dir

    def pulse(self):
        self.step.on()
        self.step.off()

class StepperController:
    STEPS_PER_DEGREE = 106.4
    MAX_STEPS = 20000

    def __init__(
        self,
        event_bus,
        *,
        azimuth_pins=(25, 4, 24),
        altitude_pins=(6, 12, 5),
        azimuth_invert=False,
        altitude_invert=False,
        az_ms_pins=(16, 26),
        alt_ms_pins=(20, 21),
        ms_mode=(0, 1),
        az_endstop_pin=17,
        alt_endstop_pin=18,
        deadband=200,
    ):
        self.event_bus = event_bus
        self.az_motor = StepperMotor(*azimuth_pins, invert_dir=azimuth_invert)
        self.alt_motor = StepperMotor(*altitude_pins, invert_dir=altitude_invert)
        self.az_position = 0
        self.alt_position = 0
        self.az_target = 0
        self.alt_target = 0
        self.max_steps = self.MAX_STEPS
        self.deadband = deadband
        self.running = True
        self.tasks_started = False

        # Microstepping pins
        self.az_ms1 = DigitalOutputDevice(az_ms_pins[0])
        self.az_ms2 = DigitalOutputDevice(az_ms_pins[1])
        self.alt_ms1 = DigitalOutputDevice(alt_ms_pins[0])
        self.alt_ms2 = DigitalOutputDevice(alt_ms_pins[1])

        self.az_ms1.value = bool(ms_mode[0])
        self.az_ms2.value = bool(ms_mode[1])
        self.alt_ms1.value = bool(ms_mode[0])
        self.alt_ms2.value = bool(ms_mode[1])

        # Endstop inputs (active-low)
        self.az_endstop = DigitalInputDevice(az_endstop_pin, pull_up=True) if az_endstop_pin else None
        self.alt_endstop = DigitalInputDevice(alt_endstop_pin, pull_up=True) if alt_endstop_pin else None

    def start_tasks(self):
        if not self.tasks_started:
            asyncio.create_task(self.track_axis_loop("az"))
            asyncio.create_task(self.track_axis_loop("alt"))
            self.tasks_started = True

    async def track_axis_loop(self, axis: str):
        motor = self.az_motor if axis == "az" else self.alt_motor
        get_target = lambda: self.az_target if axis == "az" else self.alt_target
        get_pos = lambda: self.az_position if axis == "az" else self.alt_position
        set_pos = lambda x: setattr(self, f"{axis}_position", x)
        endstop = self.az_endstop if axis == "az" else self.alt_endstop

        MIN_DELAY = 0.0015  # Use your SLOW_DELAY
        MAX_DELAY = 0.0008  # Use your FAST_DELAY
        RAMP_STEPS = 200

        while self.running:
            target = get_target()
            current = get_pos()
            delta = target - current

            if abs(delta) < self.deadband:
                motor.enable_motor(False)
                await asyncio.sleep(0.05)
                continue

            motor.enable_motor(True)
            direction = delta > 0
            motor.set_direction(direction)

            # BLOCK ALL MOTION if endstop is pressed (test mode)
            if endstop and not endstop.value:  # active-low: pressed = False
                print(f"[{axis.upper()}] Endstop pressed — BLOCKING ALL MOTION")
                motor.enable_motor(False)
                await asyncio.sleep(0.1)
                continue

            steps_remaining = abs(delta)
            ramp_factor = min(1.0, steps_remaining / RAMP_STEPS)
            delay = MIN_DELAY - (MIN_DELAY - MAX_DELAY) * ramp_factor
            delay = max(MAX_DELAY, min(MIN_DELAY, delay))

            motor.pulse()
            set_pos(current + (1 if direction else -1))
            await asyncio.sleep(delay)

    def degrees_to_steps(self, axis, deg):
        return int(deg * self.STEPS_PER_DEGREE)

    async def goto_degree_offset(self, axis, target_deg, min_delay=0.0015, max_delay=0.0008, ramp_steps=200):
        target_steps = self.degrees_to_steps(axis, target_deg)
        await self.goto_steps(axis, target_steps, min_delay, max_delay, ramp_steps)

    async def goto_steps(self, axis, target, min_delay=0.0015, max_delay=0.0008, ramp_steps=200):
        motor = self.az_motor if axis == "az" else self.alt_motor
        pos_attr = f"{axis}_position"
        cur = getattr(self, pos_attr)
        motor.enable_motor(True)
        while cur != target:
            steps_remaining = abs(target - cur)
            ramp_factor = min(1.0, steps_remaining / ramp_steps)
            delay = min_delay - (min_delay - max_delay) * ramp_factor
            delay = max(max_delay, min(min_delay, delay))
            direction = cur < target
            motor.set_direction(direction)
            cur += 1 if direction else -1
            motor.pulse()
            setattr(self, pos_attr, cur)

            await asyncio.sleep(delay)
        motor.enable_motor(False)

    async def home_axis(self, axis: str,
                        fast_delay=0.0008,
                        slow_delay=0.0015,
                        backoff_steps=100):
        motor = self.az_motor if axis == "az" else self.alt_motor
        endstop = self.az_endstop if axis == "az" else self.alt_endstop
        set_pos = lambda x: setattr(self, f"{axis}_position", x)

        print(f"[{axis.upper()}] Homing start")
        motor.enable_motor(True)
        motor.set_direction(False)  # Move toward endstop

        # Approach endstop
        while endstop.value:
            motor.pulse()
            await asyncio.sleep(fast_delay)
        print(f"[{axis.upper()}] Endstop contacted (fast)")

        # Back off
        motor.set_direction(True)
        for _ in range(backoff_steps):
            motor.pulse()
            await asyncio.sleep(fast_delay)

        # Slow approach
        motor.set_direction(False)
        while endstop.value:
            motor.pulse()
            await asyncio.sleep(slow_delay)

        # Final slow touch
        motor.set_direction(True)
        while not endstop.value:
            motor.pulse()
            await asyncio.sleep(slow_delay)

        print(f"[{axis.upper()}] Homing complete (slow approach)")
        set_pos(0)
        motor.enable_motor(False)

        # Move to center
        halfway = self.max_steps // 2
        print(f"[{axis.upper()}] Moving to center: {halfway} steps")
        await self.goto_steps(axis, halfway)
