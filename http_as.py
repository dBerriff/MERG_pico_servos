# as_sw_http.py
import uasyncio as asyncio
import network
import rp2
import time
import ssid
import util_as as util


class VSwitches:
    """ process http switch inputs
        - virtual switches are numbered: 0, 1, ...
        - virtual switches can have a prefix, e.g. V0, V1, ...
          -- this is for readability """
    
    def __init__(self, n_switches, prefix):
        self.n_switches = n_switches
        self.prefix = prefix
        self._states = self.build_init_states_dict()
        self.keys = list(self._states.keys())
        self.keys.sort()
        # switch names (keys) are invariant
        self.keys = tuple(self.keys)

    def build_init_states_dict(self):
        """ initialise state dictionary with state = 0 """
        states = {}
        for i in range(self.n_switches):
            states[self.prefix + str(i)] = 0
        return states

    @property
    def states(self):
        """ return dictionary of switch states """
        return self._states
    
    @states.setter
    def states(self, value_dict):
        """ set/reset virtual-switch values """
        self._states = value_dict
    
    def set_v_switch(self, key, state):
        """ set individual switch state """
        self._states[key] = state
    
    def print_states(self):
        """ print list of states in key order """
        state_string = ''
        for key in self.keys:
            state_string += f'{key}: {self._states[key]}, '
        # remove final comma and space
        print(f'{state_string[:-2]}')


def wifi_connect(timeout_s=10):
    """ - enable station interface (STA_IF)
        - try to connect to Wi-Fi
    """
    rp2.country(ssid.COUNTRY)
    wlan = network.WLAN(network.STA_IF)  # station aka client
    wlan.active(True)
    # optional:
    # wlan.config(pm = 0xa11140)  # server: disable power-save mode
    
    wlan.connect(ssid.SSID, ssid.PASSWORD)

    timeout = time.time() + timeout_s
    while time.time() < timeout:
        if wlan.status() < 0 or wlan.status() >= 3:
            break
        print('Waiting for WiFi connection...')
        time.sleep_ms(1000)
    
    if wlan.status() != 3:  # CYW43_LINK_UP == 3
        raise RuntimeError(f'!connection failed, status: {wlan.status()}')
    host = wlan.ifconfig()[0].rsplit('.', 1)[1]  # ip host address
    return wlan, host


class HttpServer:
    """ HTTP server to:
        - accept HTTP switching requests
       -  set virtual switches """
    
    def __init__(self, v_switches):
        self.v_switches = v_switches
        self.wlan, self.host = wifi_connect()
        if not self.wlan:
            raise Exception('Could not join WiFi network')
        self.form_template = self.get_form_template(
            'form_template.html')
        self.form_id = self.get_form_name()
        # declare asyncio events
        self.ev_input = asyncio.Event()
        self.ev_main_ready = asyncio.Event()

    @staticmethod
    def get_form_template(filename):
        """ read in the form template
            - html with string-formatting placeholders """
        with open(filename, 'rt') as f:
            template = f.read()
        return template

    def get_form_name(self):
        """ return string of form: 'nV_host' """
        return str(self.v_switches.n_switches) + \
            self.v_switches.prefix + '_' + self.host

    async def serve_client(self, reader, writer):
        """ callback function to handle client HTTP requests
            - asyncio.start_server() in main() passes:
              -- each request to this function
              -- (reader, writer) as parameters """

        def build_form(form_id, valid=False):
            """ build html form as string with virtual buttons
                - radio buttons checked to match v_switch states """
            r_btn = f'<input type="hidden" name="_id" value="{form_id}">\n'
            if valid:
                # build radio button string
                for sw_name in self.v_switches.keys:
                    state = self.v_switches.states[sw_name]
                    # build HTML radio buttons
                    r_btn += f'{sw_name}: <label>  Off: \n'
                    checked = 'checked="checked"' if state == 0 else ''
                    r_btn += f'<input type="radio" name="{sw_name}" value="0" {checked}>'
                    r_btn += '</label>\n'
                    r_btn += f'<label> On: \n'
                    checked = 'checked="checked"' if state == 1 else ''
                    r_btn += f'<input type="radio" name="{sw_name}" value="1" {checked}>'
                    r_btn += '</label><br>\n'
            else:
                # return empty radio button string
                r_btn += ' \n'
            # build form from template and return
            form = self.form_template.format(form_id, r_btn)
            return form
        
        def set_v_switches(parameters_):
            """ set virtual switches from parameters_ dictionary """
            for key in parameters_:
                # guard against settings from non-valid form
                if key in self.v_switches.keys:
                    self.v_switches.set_v_switch(key, int(parameters_[key]))

        def parse_parameters(request_: str):
            """ return request parameters dictionary """
            # extract parameter part of request
            request_ = request_.split('?', 1)[1]
            p_dict = {}
            for param in request_.split('&'):
                key, value = param.split('=')
                p_dict[key] = value
            return p_dict

        def parse_request(request_: str):
            """ parse request and
                return appropriate response to browser
                - expected file names: '/data.php', '/form.html' """
            if request_.find('/data') == 0:
                parameters = parse_parameters(request)
                if parameters['_id'] == self.form_id:
                    set_v_switches(parameters)
                    response_ = build_form(self.form_id, valid=True)
                    self.ev_input.set()
                else:
                    response_ = build_form('Form-name not valid', valid=False)
            elif request_.find('/form') == 0:
                # should re-requesting the form set all switches to 0?
                # uncomment following statement if that is required behaviour
                # self.v_switches.states = self.v_switches.build_init_states_dict()
                response_ = build_form(self.form_id, valid=True)
                self.ev_input.set()
            else:
                response_ = build_form('Request not valid', valid=False)
            return response_

        # === server awaits next call from asyncio server
        request_line = await reader.readline()
        # not interested in HTTP request headers; skip them
        while await reader.readline() != b"\r\n":
            pass
        # slice request_line as string to method, request, ...
        request = str(request_line).split(' ')[1]
        await self.ev_main_ready.wait()
        response = parse_request(request)
        # send response to the browser; see Pi Foundation example
        writer.write('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
        writer.write(response)
        await writer.drain()
        await writer.wait_closed()


def main():
    """ test polling of switch inputs """
    
    # optional heartbeat simply shows task activity
    asyncio.create_task(util.heartbeat())
    # allow task(s) to be run
    await asyncio.sleep_ms(0)

    # set number of HTTP switches
    http_switches = VSwitches(4, "V")
    http_server = HttpServer(http_switches)
    asyncio.create_task(asyncio.start_server(
        http_server.serve_client, "0.0.0.0", 80))

    # test diagnostics
    print('server running')
    print(f'wlan: {http_server.wlan}')
    print(f'host address: {http_server.host}')
    print(f'{http_switches.n_switches} virtual switch inputs: {http_switches.keys}')
    print()
    
    # loop awaits input activity
    while True:
        http_switches.print_states()
        http_server.ev_main_ready.set()
        await http_server.ev_input.wait()
        http_server.ev_input.clear()
        http_server.ev_main_ready.clear()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    finally:
        asyncio.new_event_loop()  # clear retained state
        print('test complete')
