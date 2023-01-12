# switches_as.py
from machine import Pin
import uasyncio as asyncio
from time import sleep_ms


class HwSwitch(Pin):
    """ on/off switch (latching) input
        - extends machine.Pin class
        - extends Switch class """
    
    # class constants
    # pull-up logic
    _OFF = 1
    _ON = 0

 
    def __init__(self, pin: int):
        # initialise Pin parent object
        super().__init__(pin, Pin.IN, Pin.PULL_UP)
        self.id = pin
        self._state = None

    @property
    def state(self):
        """ return hardware switch state  """
        self._state = 1 if self.value() == HwSwitch._ON else 0
        return self._state


class HwSwitchGroup:
    """ create a group of HwSwitch objects
        to handle system inputs """

    def __init__(self, switch_pins_: tuple, poll_interval: int = 1_000):
        self.switches = {pin: HwSwitch(pin) for pin in switch_pins_}
        self.poll_interval = poll_interval
        self.ev_input = asyncio.Event()  # set when input data received
        self.ev_consumer_ready = asyncio.Event()  # set when data consumer is ready
        self._switch_states = None
        self._previous_states = None
    
    @property
    def switch_states(self):
        """ return dictionary of switch states """
        return self._switch_states

    async def poll_switches(self):
        """ poll switch states;
            set Event ev_input when data is available """
        while True:
            # poll switches at regular intervals
            await asyncio.sleep_ms(self.poll_interval)
            self._switch_states = {
                pin: self.switches[pin].state for pin in self.switches}
            await self.ev_consumer_ready.wait()
            # flag the consumer: data is available
            self.ev_input.set()
    
    def __str__(self):
        """ string of switch states """
        return f'switch states: {self._switch_states}'


# === test / demo code

async def consume_switch_data(switches_):
    """ print switch status when changed """
    print(switches_)
    for _ in range(10):
        switches_.ev_consumer_ready.set()  # flag consumer ready for data
        await switches_.ev_input.wait()  # await ev_input is set
        switches_.ev_input.clear()  # clear event ready for next set
        switches_.ev_consumer_ready.clear()  # flag consumer as busy
        print(switches_)
        sleep_ms(2_000)  # simulate servo setting


def main():
    """ test polling of switch inputs """
    
    # === user parameters
    
    switch_pins = (16, 17, 18)
    
    # === end user parameters
    
    switches = HwSwitchGroup(switch_pins)
    asyncio.create_task(switches.poll_switches())
    await consume_switch_data(switches)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    finally:
        asyncio.new_event_loop()  # clear retained state
        print('test complete')
