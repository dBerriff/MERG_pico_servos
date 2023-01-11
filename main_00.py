# main_00.py
from servos import ServoGroup
from switches import HwSwitch
from time import sleep_ms


class SwitchGroup:
    """ create a group of HwSwitch objects for switch input """
    
    def __init__(self, pins):
        self.switches = {pin: HwSwitch(pin) for pin in pins}
        
    @property
    def state(self):
        """ return the group switch settings """
        return {pin: self.switches[pin].state for pin in self.switches}
    
    def diagnostics(self):
        """ print switch parameter values """
        for switch in self.switches.values():
            print(f'switch: {switch}')
        print()
        

def control_servos(servo_params_: dict, switch_servos_: dict):
    """ control servos from hardware switch inputs
        - demo code """

    # instantiate SwitchGroup object
    switch_pins = tuple(switch_servos_.keys())  # get from dict
    switch_group = SwitchGroup(switch_pins)
    switch_group.diagnostics()

    # instantiate ServoGroup object
    servo_group = ServoGroup(servo_params_)
    servo_group.diagnostics()
    
    polling_interval = 1_000  # ms
    prev_states = None
    while True:
        # read current switch states
        switch_states = switch_group.state
        # only process change in switch states
        if switch_states != prev_states:
            print(f'=== settings')
            print(f'switch states: {switch_states}')
            # build dict of required servo states
            servo_settings = {}
            for switch_pin in switch_states:
                for servo_pin in switch_servos_[switch_pin]:
                    servo_settings[servo_pin] = switch_states[switch_pin]
            print(f'servo settings: {servo_settings}')
            # set the servos to the demand positions
            servo_group.update(servo_settings)
            print()
        sleep_ms(polling_interval)
        prev_states = switch_states


def main():
    """ test polling of switch inputs """
    
    # === user parameters
    
    servo_params = {0: (70, 110),
                    1: (110, 70),
                    2: (45, 135, 2),
                    3: (45, 135)
                    }
    
    switch_servos = {16: (0, 1),
                     17: (2,),
                     18: (3,)
                     }

    # === end of user parameters

    control_servos(servo_params, switch_servos)
        

if __name__ == '__main__':
    main()
