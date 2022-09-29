# MERG_pico_servos
Drive servos from an R Pi Pico running MicroPython

Code uploaded in support of articles for MERG Journal.

uasyncio library called to implement cooperative multitasking.

as_sw_servos.py: Drive servos from hardware switches.
    build_system(): parse user parameter settings and instantiate system objects
    startup(): initial poll of switches and servo positioning
    main(): async: build_system(), startup(), and loop indefinitely responding to switch settings
as_http_servos.py: Drive servos over WiFi by HTTP protocol.
    TBD
as_servo.py:
    ServoSG90: sets servos to on or off by linear steps over given time.
        init(pin, off_deg, on_deg, transit_time=1)
        set_to_u16(demand, constrain=True): set duty cycle by 16-bit register, constraining within standad servo limits
        move_linear(set_state): async: move to demand state by linear steps over servo transit_time
        TBC
as_sw_input.py:
    SwitchInput: abstract class inhertied by HwSwitches and HttpSwitches
        Initialises a set of virtual-switch states
        set_v_switch(index, value): setter for a virtual switch state
    SwitchPin:
        get_state(): reads, saves and returns current switch state by pin number
    HwSwitches: supports wired switches
        scan_switches(): scan all hardware switch inputs and set corresponding virtual switch state
        poll_switches(): async: call scan_switches() at regular intervals; set ev_input Event; await polling interval
    HttpSwitches: supports http switch input
        TBD
ssid_t.py:
    template: stores ssid, password and ISO 3166 2-letter country name
