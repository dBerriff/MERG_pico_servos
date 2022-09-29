#as_sw_servos.py
#MicroPython v1.19.1 on 2022-06-18; Raspberry Pi Pico with RP2040
""" set servos from switches by linear step motion
    - asyncio cooperative multi-tasking for 
    - supports multiple servos per switch
    - structure prepares for http-server virtual switches
    - initial development by David Jones
    - see:
    1.https://github.com/peterhinch/
                  micropython-async/blob/master/v3/README.md
      for coding recommendations
    2.R Pi Foundation documentation for Pico W
    - V_1.0 2022-09-25 """

from machine import Pin, PWM
import uasyncio as asyncio
from time import sleep_ms
import gc # garbage collection
from as_servo import ServoSG90
from as_sw_input import SwitchPin, HwSwitches, heartbeat

def build_system():
    """ read and parse user/system parameters
        to construct system objects
        - called for hardware and virtual switches """
    
    #=== parameters
    
    # hardware switches by GPIO pins
    switch_pins = (26, 27, 28) # indices: 0 - 2
   
    # servos by GPIO pins
    servo_pins = (2, 3, 4, 5) # indices: 0 - 3
    
    # servo parameters: off degrees, on degrees (, transition period s)
    # - integer or floating point
    # - transition_time is optional; default: 1s
    servo_params =  (           # indices:
                     [70, 110], # 0
                     [80, 100], # 1
                     [45, 135], # 2
                     [45, 135, 2.0]  # 3 (with transition period in s)
                    )

    # per switch by index, controlled-servos by index, 
    # switch 0 sets servos 0 and 1; switch 1 sets servo 2, ...
    controlled_servos = ([0, 1], 2, 3)
    
    #=== end of parameters
    
    n_switches = len(controlled_servos)
    # build tuple of switch-input-pin objects
    hw_switches = HwSwitches(tuple((SwitchPin(pin) for pin in switch_pins)))

    # build tuple of ServoSG90-output-pin objects
    servos = []
    for i, params in enumerate(servo_params):
        servos.append(ServoSG90(servo_pins[i], *params))
    servos = tuple(servos)
    
    # build switch_servos dictionary
    switch_servos = {}
    for i in range(n_switches):
        servos_ = controlled_servos[i]
        if isinstance(servos_, int):
            servos_ = [servos_] # convert to tuple
        switch_servos[i] = servos_
    return hw_switches, servos, switch_servos
        
def startup(switches, servos, sw_servos):
    """ poll all switches and set servos
        - set direct as start setting not known
    """
    
    def startup_feedback(switches_, servos_):
        """ print startup settings """
        for i, switch in enumerate(switches_):
            print(f'virtual switch {i} pin: {switch.pin} state: {switch.state}')
        for servo in servos_:
            print(f'servo pin: {servo.pin} set state: {servo.saved_state}')
        print()
        
    print('Scan switches and initialise servos')
    switches.scan_switches()
    # in switch order, set servos from sw_servos dictionary
    for i, sw_state in enumerate(switches.switch_states):
        for index in sw_servos[i]:
            servo = servos[index]
            if sw_state == 1:
                servo.set_on()
            elif sw_state == 0:
                servo.set_off()
            # allow transit time then turn PWM pulse off
            sleep_ms(500)
            servo.zero_pulse()
    startup_feedback(switches.hw_switches, servos)
       
async def main():
    """ loop indefinitely to:
        - poll all switches and set servos through
          sw_servos dictionary
        - optionally blink on-board LED as 'hearbeat' indicator
    """
    switches, servos, switch_servos = build_system()
    startup(switches, servos, switch_servos)
    sw_poll = asyncio.create_task(switches.poll_switches())
    print(f'Polling switches every {switches.POLL_ms}ms')
    
    # garbage collect before main loop
    gc.collect()
    while True:
        tasks_servo = []
        for i, sw_state in enumerate(switches.switch_states):
            for index in switch_servos[i]:
                servo = servos[index]
                if servo.saved_state != sw_state:
                    tasks_servo.append(servo.move_linear(sw_state))
        if tasks_servo:
            result = await asyncio.gather(*tasks_servo)
            print(f'servos set (pin, state): {result}')
        await switches.ev_input.wait()
        switches.ev_input.clear()

try:
    asyncio.run(main()) # loop forever!
finally:
    print('Clearing event loop...')
    asyncio.new_event_loop()
