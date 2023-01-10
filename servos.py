# servos.py
""" set PWM duty cycle to position servos
    - uses Pi RP2040 PWM hardware to set pulse width
"""
from machine import Pin, PWM
from time import sleep_ms


class ServoSG90(PWM):
    """ control servo from a Pi Pico.
        - extends the machine.PWM class
        - PWM set by 16-bit counter: 0 to 65535 (u16)
    """
    # Servo constants; us is symbol for microseconds
    # data sheets typically specify pulse widths in us

    FREQ = 50  # Hz
    PERIOD = 1_000_000_000 // FREQ  # ns

    # absolute servo motion from nominal 0 to 180 degrees
    # corresponding pulse widths: 500_000 to 2_500_000 ns
    # degrees-linear: assume run from 45 to 135 degrees
    # absolute min and max pulse widths
    DEGREES_ABS_MIN = 0
    DEGREES_ABS_MAX = 180

    PW_MIN = 500_000  # ns    0 degrees
    PW_LOW = 1_000_000  # ns   45 degrees
    PW_HIGH = 2_000_000  # ns  135 degrees
    PW_MAX = 2_500_000  # ns  180 degrees
    
    RANGE_NS_ABS = PW_MAX - PW_MIN
    RANGE_DEGREES_ABS = DEGREES_ABS_MAX - DEGREES_ABS_MIN   
    # pw (nanoseconds) conversion factor per degree (computed value: 11111)
    NS_PER_DEGREE = RANGE_NS_ABS // RANGE_DEGREES_ABS
    
    # demand states
    OFF = 0
    ON = 1
    
    MIN_SLEEP = 200  # ms

    def __init__(self, pin, off_deg, on_deg, transit_time=1.0):
        # initialise PWM with Pin(number), then frequency
        super().__init__(Pin(pin))
        self.freq(self.FREQ)
        
        self.pin = pin  # for diagnostics
        self.off_deg = off_deg
        self.on_deg = on_deg
        self.transit_time = transit_time

        # incremental parameters for transit x (time)
        self.x_steps = 50 if transit_time < 2.0 else 100
        self.x_inc = 100 // self.x_steps
        
        self.off_ns = self.degrees_to_ns(self.off_deg)
        self.on_ns = self.degrees_to_ns(self.on_deg)
        
        self.state = None  # normally OFF or ON

    def degrees_to_ns(self, degrees: float):
        """ convert degrees to U16 duty cycle """
        return round(self.PW_MIN + degrees * self.NS_PER_DEGREE)

    def set_dc_ns(self, demand_ns: int):
        """ servo machine.PWM setting method
            - set demand duty cycle within set limits """
        demand_ns = max(demand_ns, self.PW_MIN)
        demand_ns = min(demand_ns, self.PW_MAX)
        self.duty_ns(demand_ns)

    def set_off(self):
        """ set servo direct to off position """
        self.set_dc_ns(self.off_ns)
        self.state = self.OFF
    
    def set_on(self):
        """ set servo direct to on position """
        self.set_dc_ns(self.on_ns)
        self.state = self.ON
    
    def activate_pulse(self):
        """ turn on PWM output """
        if self.state == self.ON:
            self.set_dc_ns(self.on_ns)
        else:
            self.set_dc_ns(self.off_ns)

    def zero_pulse(self):
        """ turn off PWM output """
        self.duty_ns(0)

    def move_linear(self, demand_state):
        """ move servo in equal steps over time period """
        if demand_state == self.state:
            return
        if demand_state == self.ON:
            start_pw = self.off_ns
            end_pw = self.on_ns
            set_demand = self.set_on  # method
        elif demand_state == self.OFF:
            start_pw = self.on_ns
            end_pw = self.off_ns
            set_demand = self.set_off  # method
        else:
            return

        pw_inc = round((end_pw - start_pw) / self.x_steps, 2)        
        step_pause_ms = int(1000 // self.x_steps * self.transit_time)
        
        self.activate_pulse()
        x = 0
        y = start_pw
        while x < 100:
            x += self.x_inc
            y += pw_inc
            self.set_dc_ns(int(y))
            sleep_ms(step_pause_ms)
        # set and save demand state
        set_demand()
        sleep_ms(self.MIN_SLEEP)
        self.zero_pulse()
        return demand_state


class ServoGroup:
    """ create a group of servo objects for system control """
    
    def __init__(self, servo_parameters: dict):
        self.servos = {pin: ServoSG90(pin, *servo_parameters[pin])
                       for pin in servo_parameters}

    def initialise(self):
        """ initialise all servo group to state 0 """
        for servo_ in self.servos.values():
            servo_.set_off()
    
    def move(self, demand: dict):
        """ move servos to match switch demands """
        for srv_id in demand:
            self.servos[srv_id].move_linear(demand[srv_id])
   
    def diagnostics(self):
        """ print servo parameter values"""
        for servo_ in self.servos.values():
            print(f'=== pin: {servo_.pin} ===')
            print(f'off ns: {servo_.off_ns:,}')
            print(f'on  ns: {servo_.on_ns:,}')
            print(f'transit: {servo_.transit_time}s')
            print()

# === test / demonstration code


def main():
    """ test of servo movement """
    from time import sleep_ms

    # test data
    servo_params = {0: (45, 135),
                    1: (135, 45),
                    2: (80, 100, 2.0),
                    3: (45, 135)
                    }
    
    switch_servos = {16: (0, 1),
                     17: (2,),
                     18: (3,)
                     }

    test_sw_states = ({16: 0, 17: 0, 18: 0},
                      {16: 1, 17: 0, 18: 0},
                      {16: 1, 17: 0, 18: 0},
                      {16: 0, 17: 0, 18: 0},
                      {16: 0, 17: 0, 18: 0},
                      {16: 1, 17: 0, 18: 0},
                      {16: 0, 17: 0, 18: 0})

    # create servo_group object
    servo_group = ServoGroup(servo_params)
    # print servo parameters
    servo_group.diagnostics()
    # set all servos to 0 position
    servo_group.initialise()
    
    test_interval = 1_000  # ms
    for group_setting in test_sw_states:
        print(f'switch status: {group_setting}')
        servo_settings = {}
        for sw_pin in group_setting:
            for servo_id in switch_servos[sw_pin]:
                servo_settings[servo_id] = group_setting[sw_pin]
        servo_group.move(servo_settings)
        sleep_ms(test_interval)
    print('test complete')


if __name__ == '__main__':
    main()
