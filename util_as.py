# util.py
from machine import Pin
import uasyncio as asyncio


def board_is_w():
    """ is board Pico W? """
    import sys
    return "Pico W" in sys.implementation._machine


async def heartbeat(on_ms: int = 10, off_ms: int = 4_990):
    """ blink onboard LED """
    led = 'LED' if board_is_w() else 25
    onboard = Pin(led, Pin.OUT, value=0)
    while True:
        print('beat')
        onboard.on()
        await asyncio.sleep_ms(on_ms)
        onboard.off()
        await asyncio.sleep_ms(off_ms)

# === test / demo code below


async def print_int(n: int, pause: int):
    """ print an integer at set intervals """
    for i in range(n):
        print(i)
        await asyncio.sleep_ms(pause)


async def main():
    """ test concurrency """
    asyncio.create_task(print_int(100, 1_000))
    await heartbeat()
    
if __name__ == '__main__':
    try:
        asyncio.run(main())
    finally:
        asyncio.new_event_loop()  # clear retained state
        print('test complete')
