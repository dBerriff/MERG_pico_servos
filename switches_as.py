# switches_as.py
from machine import Pin
import uasyncio as asyncio


class HwSwitch(Pin):
    """ on/off switch (latching) input
        - extends machine.Pin class """
    # class constants
    # pull-up logic
    _OFF = 1
    _ON = 0
 
    def __init__(self, pin: int):
        # initialise Pin parent object
        super().__init__(pin, Pin.IN, Pin.PULL_UP)
        self.pin = pin
        self._state = None

    @property
    def state(self):
        """ return physical switch state  """
        self._state = 1 if self.value() == HwSwitch._ON else 0
        return self._state
    

class SwitchSet:
    """ poll and return switch settings """

    def __init__(self, switch_pins_: tuple, poll_interval: int = 200):
        self.switches = {pin: HwSwitch(pin) for pin in switch_pins_}
        self.poll_interval = poll_interval
        self.ev_input = asyncio.Event()
        self._pin_states = None
        self._previous_states = None
    
    @property
    def pin_states(self):
        """ return dictionary of pin states """
        return self._pin_states

    async def poll_switches(self):
        """ poll switch states and respond to change """
        while True:
            self._pin_states = {
                pin: self.switches[pin].state for pin in self.switches}
            if self._pin_states != self._previous_states:
                self.ev_input.set()
            await asyncio.sleep_ms(self.poll_interval)
            self._previous_states = self._pin_states


def main():
    """ test polling of switch inputs """
    # === user parameters
    
    switch_pins = (16, 17, 18)
    
    # ===
    
    switches = SwitchSet(switch_pins)
    asyncio.create_task(switches.poll_switches())
    while True:
        print(f'pin: switch state {switches.pin_states}')
        await switches.ev_input.wait()
        switches.ev_input.clear()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    finally:
        asyncio.new_event_loop()  # clear retained state
        print('test complete')
        