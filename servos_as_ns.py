# servos_as_ns.py
""" set PWM duty cycle to position standard servos
    - uses Pi RP2040 PWM hardware to set pulse width
"""
from machine import Pin, PWM
import uasyncio as asyncio


class ServoSG90(PWM):
    """ control servos from a Pi Pico.
        - extends the machine.PWM class; pw - pulse width
        - pulse duty cycle set by a 16-bit register (u16):
        -- 0 (0x0000) to 65535 (0xffff) is 0% to 100%
        - pw time units: nanoseconds, as in machine library
        TO DO: separate out rotation functions
    """
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

    # segment-end coordinates for non-linear motion
    # x: transition time; y: angular rotation
    # values are for (x, y): (0%, 0%) -> (100%, 100%)
    motion_coords = {
        'linear': ((100, 100),),
        'overshoot': ((50, 110), (65, 120), (90, 90), (100, 100)),
        'bounce': ((50, 100), (62, 75), (75, 100), (88, 90), (100, 100)),
        's_curve': ((25, 10), (75, 90), (100, 100)),
        'slowing': ((25, 54), (50, 81), (75, 95), (100, 100))
        }

    def __init__(self, pin: int, off_deg: float, on_deg: float,
                 transit_time: float = 1.0, motion: str = 's_curve'):
        # initialise PWM with Pin(number), then frequency
        super().__init__(Pin(pin))
        self.freq(self.FREQ)

        self.pin = pin  # for test/debug
        self.off_deg = off_deg
        self.on_deg = on_deg
        self.transit_time = transit_time
        self.motion_on = motion  # for future development
        self.motion_off = motion  # for future development
        
        # incremental parameters for transit x (time)
        self.x_steps = 50 if transit_time < 2.0 else 100
        self.x_inc = 100 // self.x_steps
        
        # servo off & on ns values are set from off_deg & on_deg
        # if degrees_offset is changed, off_ns and on_ns are updated
        self._degrees_offset = 0  # default
        self.off_ns = self.degrees_to_ns(
            self.off_deg, self.degrees_offset)
        self.on_ns = self.degrees_to_ns(
            self.on_deg, self.degrees_offset)
        # set actual values
        self.set_servo_off_on_ns()
        
        self.state = None  # normally OFF or ON

    @property
    def degrees_offset(self):
        """ set as property for setter code """
        return self._degrees_offset
    
    @degrees_offset.setter
    def degrees_offset(self, offset):
        """ set offset within absolute degrees range """
        offset = max(offset, self.DEGREES_ABS_MIN)
        offset = min(offset, self.DEGREES_ABS_MAX)
        self._degrees_offset = offset
        self.set_servo_off_on_ns()
    
    def degrees_to_ns(self, degrees: float, offset: float = 0):
        """ convert degrees to U16 duty cycle """
        degrees = degrees + offset
        return round(self.PW_MIN + degrees * self.NS_PER_DEGREE)

    def set_servo_off_on_ns(self):
        """ set the ns off and on values """
        self.off_ns = self.degrees_to_ns(
            self.off_deg, self.degrees_offset)
        self.on_ns = self.degrees_to_ns(
            self.on_deg, self.degrees_offset)
        
    def set_dc_ns(self, demand_ns: int):
        """ servo machine.PWM setting method
            - set demand duty cycle within set limits """
        demand_ns = max(demand_ns, self.PW_MIN)
        demand_ns = min(demand_ns, self.PW_MAX)
        self.duty_ns(demand_ns)

    def set_servo_off(self):
        """ set servo direct to off position """
        self.set_dc_ns(self.off_ns)
        self.state = self.OFF
    
    def set_servo_on(self):
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
        
    async def move_linear(self, demand_state: int):
        """ move servo in linear steps over transit-time """
        if demand_state == self.state:
            return
        
        if demand_state == self.ON:
            start_pw = self.off_ns
            end_pw = self.on_ns
            set_demand = self.set_servo_on  # method
        elif demand_state == self.OFF:
            start_pw = self.on_ns
            end_pw = self.off_ns
            set_demand = self.set_servo_off  # method
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
            await asyncio.sleep_ms(step_pause_ms)
        # set and save demand state
        set_demand()
        await asyncio.sleep_ms(self.MIN_SLEEP)
        self.zero_pulse()
        return demand_state

    async def move_coords(self, demand_state: int):
        """ set servo by linear segments through set coords on
            (0, 0) to (100, 100) scale over transit_time """
        if demand_state == self.state:
            return
        if demand_state == self.ON:  # off -> on
            start_pw = self.off_ns
            end_pw = self.on_ns
            set_demand = self.set_servo_on
            motion = self.motion_on
        elif demand_state == self.OFF:  # on -> off
            start_pw = self.on_ns
            end_pw = self.off_ns
            set_demand = self.set_servo_off
            motion = self.motion_off
        else:
            return

        step_pause_ms = int(
            self.transit_time * 1000) // self.x_steps

        self.activate_pulse()
        x0, y0 = (0, 0)
        x_range, y_range = (100, 100)
        
        # y to pulse-width conversion factor
        y_to_pw = (end_pw - start_pw) / y_range

        for (x1, y1) in self.motion_coords[motion]:
            pw_0 = round(y_to_pw * y0)
            pw_1 = round(y_to_pw * y1)
            y = start_pw + pw_0  # segment origin
            y_step = self.x_inc * (pw_1 - pw_0) / (x1 - x0)
            x = x0
            while x < x1:
                x += self.x_inc
                y += y_step
                self.set_dc_ns(int(y))
                await asyncio.sleep_ms(step_pause_ms)
            x0, y0 = (x1, y1)
        # ensure final state is set and saved
        set_demand()
        await asyncio.sleep_ms(self.MIN_SLEEP)
        self.zero_pulse()
        return demand_state        


def pin_servo(srv_params: dict, offset: float = 0):
    """ return dictionary of pin: servo-objects
        - optional offset from 0 to 180 degrees rotation scale """
    pin_srv = {}
    for pin_ in srv_params:
        servo = ServoSG90(pin_, *srv_params[pin_])
        servo.degrees_offset = offset
        pin_srv[pin_] = servo
    return pin_srv

# === test / demo code


async def test_servos(servos_):
    """ set servos to test positions """
    for test_state in (0, 1, 0, 0, 1, 1, 0):
        print(f'demand: {test_state}')
        tasks = []
        for pin in servos_:
            tasks.append(servos_[pin].move_linear(test_state))
        result = await asyncio.gather(*tasks)
        print(result)


def main():
    """ simple test of servo movement """
    
    def print_settings(servos_: dict):
        """ print servo parameter values"""
        for servo_ in servos_.values():
            print(f'=== pin: {servo_.pin}')
            print(f'rotation scale offset: {servo_.degrees_offset} degrees')
            print(f'servo-off: {servo_.off_deg:+} degrees')
            print(f'servo-on: {servo_.on_deg:+} degrees')
            print(f'off pulse-width: {servo_.off_ns:,} ns')
            print(f'on pulse-width: {servo_.on_ns:,} ns')
            print(f'transit time: {servo_.transit_time} s')
            print()
        
    # test data
    # servo absolute range is 0 to 180 degrees
    # 'safe' servo movement is in range 45 to 135 degrees
    # degrees_offset shifts the zero point from 0 degrees absolute
    
    # example: set mid-point of rotation as 0 degrees
    # rotate 45 degrees around this mid-point
    degrees_offset = 90
    servo_params = {0: (-45.5, 45.5, 2.0),
                    1: (-45, 45, 2.0)
                    }
    servos = pin_servo(servo_params, degrees_offset)
    print_settings(servos)
    
    # initialise servos to off
    for pin in servos:
        servos[pin].set_servo_off()

    await(test_servos(servos))

        
if __name__ == '__main__':
    try:
        asyncio.run(main())
    finally:
        asyncio.new_event_loop()  # clear retained state
        print('test complete')
