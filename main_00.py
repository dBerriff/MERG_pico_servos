# main_00.py
from switches import pin_switches, pin_states
from servos import ServoGroup
from time import sleep_ms


def control_servos(servo_params_: dict, switch_servos_: dict):
    """ control servos from hardware switch inputs """

    # derive switch_pins tuple and dict of switch objects
    switch_pins = tuple(switch_servos_.keys())
    switches = pin_switches(switch_pins)

    # instantiate ServoGroup object
    servo_group = ServoGroup(servo_params_)
    servo_group.diagnostics()
    
    polling_interval = 1_000  # ms
    prev_states = None
    while True:
        switch_states = pin_states(switches)
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
