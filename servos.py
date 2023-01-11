# servos.py
""" position SG90 servos by setting the PWM duty cycle
    - uses RP2040 PWM hardware to set pulse width
"""
from machine import Pin, PWM
from time import sleep_ms


class ServoSG90(PWM):
    """ control a servo by PWM
        - extends the machine.PWM class
    """
    # the machine library uses nanosecond as the unit of time
    FREQ = 50  # Hz
    PERIOD = 1_000_000_000 // FREQ  # ns

    # absolute servo motion is from approximately 0 to 180 degrees
    # corresponding pulse widths: 500_000 to 2_500_000 ns
    # linear motion is between 45 and 135 degrees
    DEGREES_MIN = 0
    PW_MIN = 500_000  # ns
    DEGREES_MAX = 180
    PW_MAX = 2_500_000  # ns
    
    # conversion factor ns per degree
    NS_PER_DEGREE = (PW_MAX - PW_MIN) // (DEGREES_MAX - DEGREES_MIN)
    
    # demand states
    OFF = 0
    ON = 1
    
    # short delay period
    MIN_SLEEP = 200  # ms

    def __init__(self, pin: int, off_deg: float, on_deg: float,
                 rotation_time: float = 1.0):
        # initialise PWM with GPIO pin
        super().__init__(Pin(pin))
        # set pulse frequency
        self.freq(ServoSG90.FREQ)
        
        self.pin = pin  # for diagnostics
        self.off_deg = off_deg
        self.on_deg = on_deg
        self.rotation_time = rotation_time  # s
        
        self.off_ns = self.pw_in_range(
            self.degrees_to_ns(off_deg))
        self.on_ns = self.pw_in_range(
            self.degrees_to_ns(on_deg))
        self.state = None  # normally OFF or ON
        self.pw = None  # ns demand pulse-width

        # rotate servo incrementally
        self.x_inc = 1
        self.x_steps = 100 // self.x_inc

    def degrees_to_ns(self, degrees: float):
        """ convert degrees to pulse-width ns """
        return round(self.PW_MIN + degrees * self.NS_PER_DEGREE)
    
    def pw_in_range(self, pw_):
        """ return pulse-width within allowed range """
        pw_ = max(pw_, self.PW_MIN)
        pw_ = min(pw_, self.PW_MAX)
        return pw_

    def move_servo(self, pw_):
        """ servo machine.PWM setting method """
        # protect servo against out-of-range demands
        if pw_ < self.PW_MIN or pw_ > self.PW_MAX:
            return
        self.duty_ns(pw_)

    def set_off(self):
        """ set servo direct to off position """
        self.pw = self.off_ns
        self.move_servo(self.pw)
        self.state = self.OFF
    
    def set_on(self):
        """ set servo direct to on position """
        self.pw = self.on_ns
        self.move_servo(self.pw)
        self.state = self.ON
    
    def activate_pulse(self):
        """ turn on PWM output """
        self.move_servo(self.pw)

    def zero_pulse(self):
        """ turn off PWM output """
        self.duty_ns(0)

    def move_linear(self, demand_state: int):
        """ move servo in equal steps over transition time """
        if demand_state == self.state:
            return
        if demand_state == self.ON:
            end_pw = self.on_ns
            set_demand = self.set_on  # method
        elif demand_state == self.OFF:
            end_pw = self.off_ns
            set_demand = self.set_off  # method
        else:
            return
        
        self.activate_pulse()
        pw_inc = (end_pw - self.pw) // self.x_steps
        step_pause_ms = int(self.rotation_time * 1000) // self.x_steps
        x = 0
        while x < 100:
            x += self.x_inc
            self.pw += pw_inc
            self.move_servo(self.pw)
            sleep_ms(step_pause_ms)
        # set final position
        set_demand()
        # pause for motion to complete
        sleep_ms(self.MIN_SLEEP)
        self.zero_pulse()
        return self.state


class ServoGroup:
    """ create a group of servo objects for system control
        - format of servo_parameters dictionary is:
          {pin_number: servo-parameters, pin_number: servo-parameters, ...}
        - format of self.servos is:
          {pin_number: servo-object, pin_number: servo-object, ...}
          """
    
    def __init__(self, servo_parameters: dict):
        self.servos = {pin: ServoSG90(pin, *servo_parameters[pin])
                       for pin in servo_parameters}
        self.initialise()

    def initialise(self):
        """ initialise all servos """
        for servo in self.servos.values():
            servo.set_off()
            sleep_ms(200)
            servo.zero_pulse()
    
    def update(self, demand: dict):
        """ move each servo to match switch demands """
        for srv_id in demand:
            self.servos[srv_id].move_linear(demand[srv_id])
   
    def diagnostics(self):
        """ print servo parameter values"""
        for servo_ in self.servos.values():
            print(f'=== pin: {servo_.pin} ===')
            print(f'off ns: {servo_.off_ns:,}')
            print(f'on  ns: {servo_.on_ns:,}')
            print(f'transit: {servo_.rotation_time}s')
            print()

# === test / demonstration code


def test_servos(servo_params_, switch_servos_):
    """ run a test sequence """

    # represent changing switch input
    test_sw_states = ({16: 0, 17: 0, 18: 0},
                      {16: 1, 17: 1, 18: 1},
                      {16: 1, 17: 1, 18: 1},
                      {16: 0, 17: 0, 18: 0},
                      {16: 0, 17: 0, 18: 0},
                      {16: 1, 17: 1, 18: 1},
                      {16: 0, 17: 0, 18: 0})
    
    # create and initialise ServoGroup object
    servo_group = ServoGroup(servo_params_)
    servo_group.diagnostics()
    
    test_interval = 1_000  # ms between test "input"
    i = 0
    for group_settings in test_sw_states:
        print(f'settings: {i}')
        print(f'test switch settings:   {group_settings}')
        servo_settings = {}
        for switch_pin in group_settings:
            for servo_pin in switch_servos_[switch_pin]:
                servo_settings[servo_pin] = group_settings[switch_pin]
        print(f'updated servo settings: {servo_settings}')
        servo_group.update(servo_settings)
        print()
        sleep_ms(test_interval)
        i += 1
        
        
def main():
    """ test of servo movement """

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

    test_servos(servo_params, switch_servos)
    print('test complete')


if __name__ == '__main__':
    main()
