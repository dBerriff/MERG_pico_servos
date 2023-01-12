# main_01.py
import uasyncio as asyncio
from servos_as import ServoGroup
from switches_as import HwSwitchGroup

# === test / demo code


async def consume_switch_data(switch_group_, servo_group_, switch_servos_):
    """ set servos from switch polling result
        - switch_group_.ev_data_ready flags new data
        - data is not checked for changes """
    while True:
        # wait for switch data
        switch_group_.ev_consumer_ready.set()  # flag consumer ready for data
        await switch_group_.ev_data_ready.wait()  # await data available
        switch_group_.ev_data_ready.clear()  # clear event ready for next setting
        switch_group_.ev_consumer_ready.clear()  # flag consumer as busy

        # build dictionary of servo setting demands
        servo_settings = {}
        for switch_pin in switch_group_.states:
            for servo_pin in switch_servos_[switch_pin]:
                servo_settings[servo_pin] = switch_group_.states[switch_pin]
        # update the servo positions
        print(servo_settings)
        await servo_group_.update(servo_settings)


def main():
    """ test polling of switch inputs """

    # === user parameters

    servo_params = {0: (70, 110),
                    1: (110, 70),
                    2: (45, 135, 2.0),
                    3: (45, 135)
                    }

    switch_servos = {16: (0, 1),
                     17: (2,),
                     18: (3,)
                     }

    # === end of user parameters
    # derive switch GPIO pins
    switch_pins = tuple(switch_servos.keys())

    # create HwSwitchGroup object
    switch_group = HwSwitchGroup(switch_pins)
    # create and initialise ServoGroup object
    servo_group = ServoGroup(servo_params)
    print('initialising servos')
    await servo_group.initialise()

    # create the task to consume the switch data
    print('create task to consume switch data')
    asyncio.create_task(consume_switch_data(switch_group, servo_group, switch_servos))
    
    # start the switch polling - runs forever
    print('start switch polling')
    await switch_group.poll_switches()  # await forever!


if __name__ == '__main__':
    try:
        asyncio.run(main())
    finally:
        asyncio.new_event_loop()  # clear retained state
        print('test complete')
