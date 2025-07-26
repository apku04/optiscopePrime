"""
Refactor Plan to support Manual Mode with position-following logic:

- Potentiometers represent target positions.
- Steppers move to reach the target at fixed speed.
- Uses event-driven updates when pot values change.
"""

import asyncio
from typing import Optional, Tuple, Dict
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
    def __init__(
        self,
        event_bus,
        *,
        azimuth_pins=(25, 4, 24),
        altitude_pins=(6, 12, 5),
        azimuth_invert=False,
        altitude_invert=False,
        max_steps=10000,
        az_ms_pins=(16, 26),
        alt_ms_pins=(20, 21),
        ms_mode=(0, 1),  # Default to 1/4 step (MS1=LOW, MS2=HIGH)
    ):
        self.event_bus = event_bus
        self.az_motor = StepperMotor(*azimuth_pins, invert_dir=azimuth_invert)
        self.alt_motor = StepperMotor(*altitude_pins, invert_dir=altitude_invert)
        self.az_position = 0
        self.alt_position = 0
        self.az_target = 0
        self.alt_target = 0
        self.max_steps = max_steps
        self.running = True
        self.tasks_started = False
        self.event_bus.subscribe("pot_changed", self.on_pot_changed)

        # Configure microstepping pins
        self.az_ms1 = DigitalOutputDevice(az_ms_pins[0])
        self.az_ms2 = DigitalOutputDevice(az_ms_pins[1])
        self.alt_ms1 = DigitalOutputDevice(alt_ms_pins[0])
        self.alt_ms2 = DigitalOutputDevice(alt_ms_pins[1])

        # Apply mode
        self.az_ms1.value = bool(ms_mode[0])
        self.az_ms2.value = bool(ms_mode[1])
        self.alt_ms1.value = bool(ms_mode[0])
        self.alt_ms2.value = bool(ms_mode[1])

    def start_tasks(self):
        if not self.tasks_started:
            asyncio.create_task(self.track_axis_loop("az"))
            asyncio.create_task(self.track_axis_loop("alt"))
            self.tasks_started = True

    def on_pot_changed(self, data: Tuple[str, int]):
        axis, value = data
        target = int(value * self.max_steps / 65535)
        if axis == "az":
            self.az_target = target
        elif axis == "alt":
            self.alt_target = target

    async def track_axis_loop(self, axis: str):
        motor = self.az_motor if axis == "az" else self.alt_motor
        get_target = lambda: self.az_target if axis == "az" else self.alt_target
        get_pos = lambda: self.az_position if axis == "az" else self.alt_position
        set_pos = lambda x: setattr(self, f"{axis}_position", x)

        MIN_DELAY = 0.015  # slowest (66 steps/sec)
        MAX_DELAY = 0.002  # fastest (500 steps/sec)
        RAMP_STEPS = 200  # how many steps it takes to ramp fully

        while self.running:
            target = get_target()
            current = get_pos()
            delta = target - current

            if abs(delta) < 50:
                motor.enable_motor(False)  # disable when idle
                await asyncio.sleep(0.05)
                continue

            motor.enable_motor(True)
            direction = delta > 0
            motor.set_direction(direction)

            # Compute how close we are to target → adjust step delay
            steps_remaining = abs(delta)
            ramp_factor = min(1.0, steps_remaining / RAMP_STEPS)
            delay = MIN_DELAY - (MIN_DELAY - MAX_DELAY) * ramp_factor
            delay = max(MAX_DELAY, min(MIN_DELAY, delay))

            motor.pulse()
            set_pos(current + (1 if direction else -1))
            await asyncio.sleep(delay)
