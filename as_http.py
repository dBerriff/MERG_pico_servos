#as_sw_http.py
import uasyncio as asyncio
import network
import rp2
import time
import ssid

def wifi_connect(self, timeout_s = 10):
    """ - enable station interface (STA_IF)
        - try to connect to WiFi
    """
    wlan = network.WLAN(network.STA_IF)    
    rp2.country(ssid.COUNTRY)
    wlan = network.WLAN(network.STA_IF) # station aka client
    wlan.active(True)
    # optional:
    #wlan.config(pm = 0xa11140)  # server: disable power-save mode
    
    wlan.connect(ssid.SSID, ssid.PASSWORD)

    timeout = time.time() + int(timeout_s)
    while time.time() < timeout:
        if wlan.status() < 0 or wlan.status() >= 3:
            break
        print('Waiting for WiFi connection...')
        time.sleep_ms(1000)
    
    if wlan.status() != 3: # CYW43_LINK_UP == 3
        raise RuntimeError(f'!connection failed, status: {wlan.status()}')
        return None
    return wlan
