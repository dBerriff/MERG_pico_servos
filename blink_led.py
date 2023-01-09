# blink_led.py
from machine import Pin
from time import sleep


def board_is_w():
    """ return True if Pico W, else False
        - only tests loaded firmware, not hardware """
    import sys
    return 'Pico W' in sys.implementation._machine


def main():
    """ blink on-board LED on Pico or Pico W """
    # set correct pin parameter for board type
    led_pin = 'LED' if board_is_w() else 25
        
    # instantiate Pin object   
    led = Pin(led_pin, Pin.OUT)

    # blink on-board led 10 times
    print('onboard LED should blink 10 times')
    led.off()
    for _ in range(20):
        led.toggle()
        sleep(0.5)  # s
    # leave led in off state
    led.off()
    print('end of main()')


if __name__ == '__main__':
    main()
