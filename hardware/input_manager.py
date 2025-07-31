from gpiozero import Button
import asyncio

CLK = 13  # BCM numbering
DT = 15
SW = 14
SYNC_OK_PIN = 7  # SPI_CE1



class InputManager:
    def __init__(self, event_bus):
        self.event_bus = event_bus
        self.position = 0

        self.clk = Button(CLK, pull_up=True)
        self.dt = Button(DT, pull_up=True)
        self.sw = Button(SW, pull_up=True)
        self.sync_ok_button = Button(SYNC_OK_PIN, pull_up=True)

        self.last_clk = self.clk.value

        self.clk.when_pressed = self.rotary_changed
        self.clk.when_released = self.rotary_changed

        self.sync_ok_button.when_pressed = self.sync_ok_pressed

        self.sw.when_pressed = self.ok_pressed

    def ok_pressed(self):
        self.event_bus.emit("menu_ok_pressed")

    def sync_ok_pressed(self):
        self.event_bus.emit("sync_ok_pressed")

    def rotary_changed(self):
        clk_state = self.clk.value
        dt_state = self.dt.value
        if clk_state != self.last_clk:
            if dt_state != clk_state:
                direction = "right"
                self.position += 1
            else:
                direction = "left"
                self.position -= 1
            self.event_bus.emit("input.menu.rotary_changed", direction)
            self.last_clk = clk_state

    def ok_pressed(self):
        self.event_bus.emit("menu_ok_pressed")

    async def poll_inputs(self):
        # No need for fast polling; events are interrupt-driven
        while True:
            await asyncio.sleep(0.05)  # Keep alive for consistency
