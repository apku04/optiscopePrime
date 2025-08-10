import asyncio
import time
from collections import deque
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

        # Motors
        self.az_motor = StepperMotor(*azimuth_pins, invert_dir=azimuth_invert)
        self.alt_motor = StepperMotor(*altitude_pins, invert_dir=altitude_invert)

        # Positions
        self.az_position = 0
        self.alt_position = 0

        # Parallel safety: per-axis locks
        self._axis_lock = {"az": asyncio.Lock(), "alt": asyncio.Lock()}

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

        # Limits / state
        self.max_steps = self.MAX_STEPS
        self.deadband = deadband
        self.running = True
        self.tasks_started = False

        # --- Global target input filter (applies to ALL modes) ---
        # Buffers for median-of-5 on raw target writes
        self._input_buf = {"az": deque(maxlen=5), "alt": deque(maxlen=5)}
        self._input_alpha = 0.18        # EMA on input (0..1). Lower = smoother
        self._input_hyst_steps = 8      # ignore input changes smaller than this (steps)
        self._input_filtered = {"az": 0.0, "alt": 0.0}  # EMA input state
        self._raw_target = {"az": 0, "alt": 0}          # latest raw written targets

        # Controller-side smoothing (after input filter)
        self._filtered_target = {"az": 0, "alt": 0}
        self._target_alpha = 0.15       # 0.0 to bypass controller EMA (input filter still active)

        # Motion / anti-jitter
        self.always_enable = True       # keep coils energized (best for telescopes)
        self.min_move_steps = 4         # dead zone around target (steps)
        self.idle_disable_timeout_s = 2.0
        self._last_move_time = {"az": 0.0, "alt": 0.0}

        # Manual offsets
        self.az_manual_offset = 0
        self.alt_manual_offset = 0

        # Initialize public targets via property setters (so filter sees them)
        self.az_target = 0
        self.alt_target = 0

    # -------- Target properties: intercept ALL writes from any mode --------
    def _set_target_internal(self, axis: str, value: int):
        v = max(0, min(int(value), self.max_steps))
        self._raw_target[axis] = v
        self._input_buf[axis].append(v)

    @property
    def az_target(self) -> int:
        return self._raw_target["az"]

    @az_target.setter
    def az_target(self, value: int):
        self._set_target_internal("az", value)

    @property
    def alt_target(self) -> int:
        return self._raw_target["alt"]

    @alt_target.setter
    def alt_target(self, value: int):
        self._set_target_internal("alt", value)

    # ---------------- Parallel-safe wrappers ----------------
    async def phome_axis(self, axis: str):
        async with self._axis_lock[axis]:
            await self.home_axis(axis)

    async def pgoto_steps(self, axis: str, steps: int):
        async with self._axis_lock[axis]:
            await self.goto_steps(axis, steps)

    # ---------------- Background tracker ----------------
    def start_tasks(self):
        if not self.tasks_started:
            asyncio.create_task(self.track_axis_loop("az"))
            asyncio.create_task(self.track_axis_loop("alt"))
            self.tasks_started = True

    async def track_axis_loop(self, axis: str):
        motor = self.az_motor if axis == "az" else self.alt_motor
        get_pos = (lambda: self.az_position) if axis == "az" else (lambda: self.alt_position)
        set_pos = (lambda x: setattr(self, f"{axis}_position", x))
        endstop = self.az_endstop if axis == "az" else self.alt_endstop

        MIN_DELAY = 0.0015  # slow
        MAX_DELAY = 0.0008  # fast
        RAMP_STEPS = 200

        HOLD_BAND = self.min_move_steps        # do not move inside this
        SNAP_BAND = max(1, HOLD_BAND // 2)     # pin filter even tighter

        # Initialize controller filtered target
        self._filtered_target[axis] = int(self._raw_target[axis])

        while self.running:
            # ---- Global input filter (median + hysteresis + EMA) ----
            raw_target = self._raw_target[axis]

            buf = self._input_buf[axis]
            med = raw_target if not buf else sorted(buf)[len(buf)//2]

            f_in = self._input_filtered[axis]
            if abs(med - f_in) >= self._input_hyst_steps:
                f_in = f_in + self._input_alpha * (med - f_in)
            f_in = float(int(round(f_in)))  # quantize to whole steps
            self._input_filtered[axis] = f_in

            # Optional controller EMA after input filter
            if self._target_alpha <= 0.0:
                target = int(f_in)
            else:
                ft = self._filtered_target[axis]
                ft = int(round(ft + self._target_alpha * (f_in - ft)))
                self._filtered_target[axis] = ft
                target = ft

            current = get_pos()
            delta = target - current
            adelta = abs(delta)

            # ---- Endstop hard block (active-low) ----
            if endstop and not endstop.value:
                if not motor._enabled:
                    motor.enable_motor(True)
                await asyncio.sleep(0.05)
                continue

            now = time.monotonic()

            # ---- SNAP near target: kill creeping drift ----
            if adelta <= SNAP_BAND:
                if self._filtered_target[axis] != current:
                    self._filtered_target[axis] = current
                delta = 0
                adelta = 0

            # ---- HOLD band: don't move; hold torque (or timed disable) ----
            if adelta < HOLD_BAND:
                if self.always_enable:
                    if not motor._enabled:
                        motor.enable_motor(True)
                else:
                    if (now - self._last_move_time[axis]) > self.idle_disable_timeout_s:
                        if motor._enabled:
                            motor.enable_motor(False)
                    else:
                        if not motor._enabled:
                            motor.enable_motor(True)
                await asyncio.sleep(0.05)
                continue

            # ---- Move one step with simple accel profile ----
            if not motor._enabled:
                motor.enable_motor(True)
            motor.set_direction(delta > 0)

            steps_remaining = adelta
            ramp_factor = min(1.0, steps_remaining / RAMP_STEPS)
            delay = MIN_DELAY - (MIN_DELAY - MAX_DELAY) * ramp_factor
            delay = max(MAX_DELAY, min(MIN_DELAY, delay))

            motor.pulse()
            set_pos(current + (1 if delta > 0 else -1))
            self._last_move_time[axis] = now

            await asyncio.sleep(delay)

    # ---------------- Direct moves ----------------
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

    # ---------------- Homing ----------------
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
            await asyncio.sleep(slow_delay)

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
