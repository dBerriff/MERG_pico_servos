#as_sw_input.py
from machine import Pin
import uasyncio as asyncio
import sys
        
def board_is_W():
    """ Pico W? """
    return 'Pico W' in sys.implementation._machine

async def heartbeat(on_ms=100, off_ms=2000):
    """ blink onboard LED as optional activity indicator """
    if board_is_W():
        led = 'LED'
    else:
        led = 25
    onboard = Pin(led, Pin.OUT, value=0) # Pico W
    while True:
        onboard.on()
        await asyncio.sleep_ms(on_ms)
        onboard.off()
        await asyncio.sleep_ms(off_ms)
        
class SwitchInput:
    """ abstract class to handle switch inputs from:
        - physical switches on GP pins
        - virtual switches over (WiFi) HTTP requests        
        - switch_states stores switch states (currently 0 or 1)
        - data_event signals newly scanned (hardware) or
          newly received (network) data """
    
    def __init__(self, n_switches: int):
        self.n_switches = n_switches
        # initialise switch settings to 0
        self.switch_states = [0 for _ in range(n_switches)]
        self.ev_input = asyncio.Event()
        
    def set_v_sw(self, index: int, value: int):
        """ setter for virtual switches """
        self.switch_states[index] = value
    

class SwitchPin(Pin):
    """ on/off switch (latching) input
        - extends machine.Pin class
        - currently no de-bounce logic """
    # class constants
    # PULL_UP logic: consistent with maker boards
    _IS_ON = 0
    _IS_OFF = 1
 
    def __init__(self, pin):
        # initialise Pin with pin number
        super().__init__(pin, Pin.IN, Pin.PULL_UP)
        self.pin = pin
        self.state = -1

    def read_state(self):
        """ get current physical switch state  """
        #TODO: de-bounce?
        if self.value() == self._IS_ON:
            self.state = 1
        elif self.value() == self._IS_OFF:
            self.state = 0
        else: # for future options
            self.state = -1

    def get_state(self):
        """ get current physical switch state  """
        self.read_state()
        return self.state


class HwSwitches(SwitchInput):
    """ wired switches """
    
    POLL_ms = 200 # ms
    
    def __init__(self, hw_switches):
        self.n_switches = len(hw_switches)
        super().__init__(self.n_switches)
        self.hw_switches = hw_switches

    def scan_switches(self):
        """ scan switches for current state
            - sets virtual switch_states in switch order """
        for i, switch in enumerate(self.hw_switches):
            self.set_v_sw(i, int(switch.get_state()))
                
    async def poll_switches(self):
        """ poll switches at regular intervals
            - set data_event to signal data available """
        while True:
            self.scan_switches()
            self.ev_input.set() # event triggers servo updates
            await asyncio.sleep_ms(self.POLL_ms)


class HttpSwitches(SwitchInput):
    """ http virtual switch settings
        - SwitchInput sets self.switch_states to 0 """
    
    def __init__(self, n_switches):
        self.n_switches = n_switches
        super().__init__(self.n_switches)        
        self.form_template = self.get_form_template()
        self.html_form = ''

    def get_form_template(self):
        """ read in the appropriate form template
            - html with formatting placeholders """
        file_name = 'form_' + str(self.n_switches) + '.html'
        with open(file_name, 'rt') as f:
            template = f.read()
        return template

    async def serve_client(self, reader, writer):
        """ handle client HTTP requests
            - asyncio.start_server() passes (reader, writer) as parameters """

        def build_html():
            """ build html form
                - radio buttons checked by switch states
                - set offset if hardware switches precede virtual """
            checked_list = []
            for state in self.switch_states:
                if state == 1:
                    checked_list.extend(['', 'checked'])
                else:
                    checked_list.extend(['checked', ''])
            # build form to match switch states
            self.html_form = self.form_template.format(
                self.switch_states, *checked_list)

        def respond(request):
            """ build response for data.php
                - no error checking!
                - assumes valid form has been served """
            # parse parameter part of request
            data_string = request.split('?', 1)[1]
            for param in data_string.split('&'):
                key, value = param.split('=', 1)
                self.set_v_sw(int(key[1:]), int(value))
            build_html()

        # server awaits next request
        request_line = await reader.readline()
        print(f'Request: {request_line}')
        # not interested in HTTP request headers; skip them
        while await reader.readline() != b"\r\n":
            pass
        #remove GET and HTTP parts
        request = str(request_line).split(' ')[1]
        # form.html and data.php are expected file names
        # do we have GET data?
        if request.find('/data') == 0:
            respond(request)
            response = self.html_form
            self.ev_input.set() # event triggers servo updates
        # else is the form requested?
        elif request.find('/form') == 0:
            build_html()
            response = self.html_form
            self.ev_input.set() # event triggers servo updates
        else:
            # send null response, do not set data_event
            response = ''
        # write out the response and await completion
        writer.write('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
        writer.write(response)

        await writer.drain()
        await writer.wait_closed()
