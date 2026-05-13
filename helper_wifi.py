import network
import utime
import gc
from helper_var import _ssid, _psk

_wifi_ssid = _ssid
_wifi_password  = _psk

_connect_timeout_ms  = 15_000   # max time to wait for initial connection
_reconnect_timeout_ms = 8_000   # max time per reconnect attempt
_poll_interval_ms    =    250

class WiFiManager:
    def __init__(self):
        self._wlan = network.WLAN(network.STA_IF)
        self._reset_wifi()
        # self._wlan.active(True)
        print("WiFi: connecting to '{}'...".format(_wifi_ssid))
        self._connect(timeout_ms=_connect_timeout_ms)

    def _reset_wifi(self):
        try:
            self._wlan.disconnect()
        except:
            pass

        try:
            self._wlan.active(False)
        except:
            pass

        utime.sleep_ms(200)

        self._wlan.active(True)

        # Disable power save (improves ESP32 stability)
        try:
            self._wlan.config(pm=0xa11140)
        except:
            pass

        utime.sleep_ms(200)

        gc.collect()


    def _connect(self, timeout_ms: int) -> bool:
        if self._wlan.isconnected():
            return True

        status = self._wlan.status()
        # print("WiFi status before connect:", status)

        try:
            self._wlan.connect(_wifi_ssid, _wifi_password)
        except Exception as e:
            print("WiFi: connect() error:", e)
            self._reset_wifi()
            return False

        start = utime.ticks_ms()

        while not self._wlan.isconnected():
            status = self._wlan.status()
            # negative status = failed
            if status < 0:
                print("WiFi failed with status:", status)
                return False

            if utime.ticks_diff(utime.ticks_ms(), start) > timeout_ms:
                print("WiFi connection timeout")
                return False

            utime.sleep_ms(_poll_interval_ms)

        ip, _, _, _ = self._wlan.ifconfig()
        print("WiFi: connected  |  IP: {}  |  SSID: {}".format(ip, _wifi_ssid))
        return True

    def is_connected(self) -> bool:
        return self._wlan.isconnected()

    def reconnect(self) -> bool:
        print("WiFi: link lost — attempting reconnect to '{}'...".format(_wifi_ssid))
        self._reset_wifi()
        """ try:
            self._wlan.disconnect()
        except Exception:
            pass
        utime.sleep_ms(500) """

        success = self._connect(timeout_ms=_reconnect_timeout_ms)
        if not success:
            print("WiFi: reconnect failed — SD logging continues, will retry next interval")
        return success

    def ip(self) -> str:
        """Return current IP address string, or empty string if not connected."""
        if self.is_connected():
            return self._wlan.ifconfig()[0]
        return ""

    def stop(self):
        """Disconnect and deactivate the WiFi interface."""
        try:
            self._wlan.disconnect()
            self._wlan.active(False)
        except Exception:
            pass
        print("WiFi: interface deactivated")