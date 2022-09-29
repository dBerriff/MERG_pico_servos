#as_servo.py
""" set PWM duty cycle to position standard servos
    - uses Pi Pico PWM hardware to set pulse width
"""
from machine import Pin, PWM
import uasyncio as asyncio


class ServoSG90(PWM):
    """ control servo from a Pi Pico.
        - extends the machine.PWM class
        - PWM set by 16-bit counter: 0 to 65535 (u16)
    """
   
    # class constants
    # SG90 pulse-width limits for 16-bit PWM register
    # 100% duty: u16 = 65535 (2**16 - 1)
    _FREQ = 50 # Hz
    _PERIOD_us = 20_000 # micro s
    U16 = 65535
    U16_MIN = 1638 # approx 0 degrees, 2.5% d.c.
    U16_MAX = 8192 # approx 180 degrees, 12.5% d.c.
    U16_DEGREES = 36.41 # @ 50Hz
    NOT_SET = -1
    OFF = 0
    ON = 1
    
    # for move_coords
    _motion_coords = {
        'linear': ((100, 100),),
        'bounce': ((50, 110), (65, 120), (90, 90), (100, 100)),
        's_curve': ((25, 10), (75, 90), (100, 100)),
        'slowing': ((25, 54), (50, 81), (75, 95), (100, 100))
        }

    @staticmethod
    def degrees_to_u16(degrees):
        return int(degrees * ServoSG90.U16_DEGREES) + ServoSG90.U16_MIN

    def __init__(self, pin, off_deg, on_deg, transit_time=1.0):
        # initialise PWM with Pin(number), then frequency
        super().__init__(Pin(pin))
        self.freq(self._FREQ)
        
        self.pin = pin
        self.off_u16 = self.degrees_to_u16(off_deg)
        self.on_u16 = self.degrees_to_u16(on_deg)
        self.transit_time = transit_time # s
        self.saved_state = self.NOT_SET

    def set_to_u16(self, demand_u16: int, constrain=True):
        """ move servo direct to demand duty cycle
            - pulse period must be fixed at 20ms """
        if constrain:
            if demand_u16 < self.U16_MIN:
                demand_u16 = self.U16_MIN
            elif demand_u16 > self.U16_MAX:
                demand_u16 = self.U16_MAX
        # duty_u16() is a PWM library method
        self.duty_u16(demand_u16)
    
    def set_to_percent(self, demand_pc: int):
        """ set by duty cycle percent """
        demand_u16 = demand_pc * self.U16 // 100
        self.set_to_u16(demand_u16, constrain = False)
    
    def set_to_us(self, demand_us: int):
        """ move servo direct to demand micro s """
        demand_u16 = demand_us * self.U16 // self._PERIOD_us
        self.set_to_u16(demand_u16)
    
    def set_to_degrees(self, demand_deg: int):
        """ move servo direct to nominal degrees
            - in range 0 to 180 """
        self.set_to_u16(degrees_to_u16(demand_deg))
    
    def set_on(self):
        """ set on, save state """
        self.set_to_u16(self.on_u16)
        self.saved_state = self.ON
    
    def set_off(self):
        """ set off, save state """
        self.set_to_u16(self.off_u16)
        self.saved_state = self.OFF
    
    def activate_pulse(self):
        """ turn on PWM output
            - use PWM.deinit() to disable output """
        if self.saved_state == 1:
            self.set_to_u16(self.on_u16)
        elif self.saved_state == 0:
            self.set_to_u16(self.off_u16)

    def zero_pulse(self):
        """ 0 duty cycle """
        self.duty_u16(0)
    
    async def move_linear(self, set_state):
        """ move servo in equal steps over time period
            - 50 steps matches frequency over 1s
            - but 100 more generally gives smooth motion
        """
        self.activate_pulse()
        # set initial conditions
        if set_state == 1:
            pw_u16 = self.off_u16
            demand_u16 = self.on_u16
            final_setting = self.set_on
        elif set_state == 0:
            pw_u16 = self.on_u16
            demand_u16 = self.off_u16
            final_setting = self.set_off
        else:
            return

        steps = 100
        # 2 places of decimal reduce incremental drift
        pw_step = round((demand_u16 - pw_u16) / steps, 2)
        pause_ms = int(self.transit_time * 1000) // steps
        for x in range(steps):
            pw_u16 += pw_step
            self.set_to_u16(int(pw_u16))
            await asyncio.sleep_ms(pause_ms)
        final_setting()
        # final settling period before zero pulse
        await asyncio.sleep_ms(200)
        self.zero_pulse()
        return self.pin, self.saved_state
