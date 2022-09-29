#as_http_servos.py
#MicroPython v1.19.1 on 2022-06-18; Raspberry Pi Pico with RP2040
""" set servos through WiFi
    - asyncio cooperative multi-tasking
    - see:
    1. https://github.com/peterhinch/micropython-async/
                  blob/master/v3/README.md
          for coding recommendations
    2. R Pi Foundation documentation for Pico W
    - optionally set multiple servos per switch
    - virtual switches set through web-server input
    - initial development by David Jones
    - V_1.0 2022-09-25
"""
from machine import Pin, PWM
import uasyncio as asyncio
from time import sleep_ms
import gc
from as_servo import ServoSG90
from as_http import wifi_connect
from as_sw_input import HttpSwitches, board_is_W, heartbeat
 
def get_objects():
    """ read and parse user/system parameters
        to construct system objects """
    
    """
        commercial servo-driver board pins:
        Waveshare servo pins: 0 - 15
        Waveshare GPIO pins: 16 - 22, 26 - 29
        Kitronik servo pins: 2 - 9
        Kitronik GPIO pins: 0, 1, 26, 27, 28)
    """
    #=== parameters
    
    # connect servos in order of servo_pins
    servo_pins = (2, 3, 4, 5, 6, 7, 8, 9) # index: 0 - 7
    
    # servo parameters: off_degrees, on_degrees, (transition_time s)
    # - integer or floating point, transition_time optional, default 1s
    servo_params =  (           # index:
                     (59, 103), # 0
                     (77, 103), # 1
                     (45, 135), # 2
                     (45, 135), # 3
                     (45, 135)  # 4
                    )

    # controlled-servos by index, in switch-pin order
    controlled_servos = ((0, 1), 2, 3, 4)
    
    #=== end of parameters
    
    n_switches = len(controlled_servos)
    v_switches = HttpSwitches(n_switches)

    # build tuple of ServoSG90 objects
    servos = []
    for i, params in enumerate(servo_params):
        servo_ = ServoSG90(servo_pins[i], *params)
        servos.append(servo_)
    servos = tuple(servos)
    
    # build switch_servos dictionary
    switch_servos = {}
    for i in range(n_switches):
        servos_ = controlled_servos[i]
        # code expects tuples, so convert all int intances
        if isinstance(servos_, int):
            servos_ = (servos_,)
        switch_servos[i] = servos_
    return v_switches, servos, switch_servos

def startup(v_switches, servos):
    """ set all servos to off """
    
    def startup_feedback(switches_, servos_):
        """ print out key startup data """
        for i, state in enumerate(switches_.switch_states):
            print(f'virtual switch {i} state: {state}')
        for servo in servos_:
            print(f'servo pin: {servo.pin} set state: {servo.saved_state}')
        print()
        
    print('Initialising servos')
    # virtual switches are instantiated at OFF
    for servo in servos:
        servo.set_off()
        # allow transit time
        sleep_ms(500)
        servo.deinit()
    startup_feedback(v_switches, servos)

async def main(blink=False):
    """ loop indefinitely to:
        - scan http virtual switch settings when data_event is set,
          and set servos through sw_servos dictionary
        - all virtual switches are instantiated at 0
    """
    if not board_is_W(): # check for Pico W
        raise Exception('Pico W required for HTTP imput')
    # connect to WiFi, 10s timeout
    wlan = wifi_connect(10)
    print(f'WiFi LAN: {wlan}')
    switches, servos, switch_servos = get_objects()
    startup(switches, servos)
    # start web server, following Pico W documentation example
    asyncio.create_task(asyncio.start_server(switches.serve_client, "0.0.0.0", 80))
    print('Server running')
    
    if blink:
        task_blink = asyncio.create_task(heartbeat()) # optional
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
    asyncio.new_event_loop() # clear retained state
