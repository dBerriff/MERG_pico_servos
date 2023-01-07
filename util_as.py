# util.py
from machine import Pin
import uasyncio as asyncio

def board_is_w():
    """ is board Pico W? """
    import sys
    board = sys.implementation._machine
    return "Pico W" in board

async def heartbeat(on_ms = 10, off_ms = 1_990):
    """ blink onboard LED """
    led = 'LED' if board_is_w() else 25
    onboard = Pin(led, Pin.OUT, value=0)
    while True:
        onboard.on()
        await asyncio.sleep_ms(on_ms)
        onboard.off()
        await asyncio.sleep_ms(off_ms)

async def main():
    """ test hearbeat() """
    asyncio.create_task(heartbeat())
    while True:
        print('_')
        await asyncio.sleep_ms(2_000)
    
if __name__ == '__main__':
    asyncio.run(main())