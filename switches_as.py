# switches_as.py
from machine import Pin
import uasyncio as asyncio


class HwSwIn(Pin):
    """ on/off switch (latching) input
        - extends machine.Pin class """
    # class constants
    # PULL_UP logic: pin connected to ground for ON
    _OFF = 1
    _ON = 0
 
    def __init__(self, pin):
        self.pin = pin
        pin_ = int(pin)
        super().__init__(pin_, Pin.IN, Pin.PULL_UP)
        self._state = None

    @property
    def state(self):
        """ return physical switch state  """
        self._state = 1 if self.value() == HwSwIn._ON else 0
        return self._state


def pin_switch(pins):
    """ return dictionary of pin: switch-objects """
    pin_sw = {pin: HwSwIn(pin) for pin in pins}
    return pin_sw


def pin_state(switches):
    """ return dictionary of pin: switch-states """
    pin_state_ = {pin: switches[pin].state for pin in switches}
    return pin_state_
    

def main():
    """ test polling of switch inputs """
    
    from util_as import heartbeat
    asyncio.create_task(heartbeat())
    # test data
    switch_pins = (16, 17, 18)
    switches = pin_switch(switch_pins)
    
    poll_interval = 1000  # ms
    while True:
        states = pin_state(switches)
        print(states)
        await asyncio.sleep_ms(poll_interval)
        

if __name__ == '__main__':
    try:
        asyncio.run(main())
    finally:
        asyncio.new_event_loop()  # clear retained state
        print('test complete')
        