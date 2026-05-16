import ubluetooth
from micropython import const
import ubinascii
import uos
import urandom

import utime

from helper_file import (
    update_file,
)

# ── AD types ──────────────────────────────────────────────────────────────────
_AD_FLAGS        = const(0x01)
_AD_NAME         = const(0x09)
_AD_MANUFACTURER = const(0xFF)

_FLAG_READ = const(0x0002)
_FLAG_WRITE_NO_RESPONSE = const(0x0004)
_FLAG_WRITE = const(0x0008)
_FLAG_NOTIFY = const(0x0010)

_IRQ_CENTRAL_CONNECT    = const(1)
_IRQ_CENTRAL_DISCONNECT = const(2)
_IRQ_GATTS_WRITE        = const(3)


def generate_random_uuid(vendor_id):
    vendor_id = ubinascii.hexlify(vendor_id.encode("utf-8")).decode("utf-8")
    random_bytes = bytes([urandom.getrandbits(8) for _ in range(16)])
    uuid_str = "".join(["{:02x}".format(b) for b in random_bytes])
    return f"{vendor_id[:8]}-{uuid_str[8:12]}-{uuid_str[12:16]}-{uuid_str[16:20]}-{uuid_str[20:32]}"


def generate_unique_id():
    random_bytes = uos.urandom(3)
    random_number = int.from_bytes(random_bytes, "big")
    unique_id = random_number % 10000
    return f"{unique_id:05d}"


def _field(ad_type, value):
    return bytes((len(value) + 1, ad_type)) + value
 

class BLEMonitor:

    def __init__(self, name="SigmaWeld"):
        self._ble = ubluetooth.BLE()
        print("Device name",name)

        self._name     = name
        self._voltage  = 0.0
        self._current  = 0.0
        self._last_adv = 0          # ticks_ms of last advertise call
        self._adv_interval_ms = 1000  # only re-advertise every 5s

        self._ble.active(True)
        self._ble.irq(self._irq)
        uui = generate_random_uuid("S-IT")
        self._UART_UUID = ubluetooth.UUID(uui)
        upld = "u=" + uui
        # print("UUID", upld)
        # update_file1(upld)
        utime.sleep(1)
        self._UART_TX = (
            ubluetooth.UUID(generate_random_uuid("S-IU")),
            _FLAG_READ | _FLAG_NOTIFY,
        )
        self._UART_RX = (
            ubluetooth.UUID(generate_random_uuid("S-IV")),
            _FLAG_WRITE | _FLAG_WRITE_NO_RESPONSE,
        )
        self._UART_SERVICE = (
            self._UART_UUID,
            (self._UART_TX, self._UART_RX),
        )
        ((self._handle_tx, self._handle_rx),) = self._ble.gatts_register_services(
            (self._UART_SERVICE,)
        )
        self._connections = set()
        self._write_callback = None
        self._advertising = True
        self._disconnet_ble = False

        self._initialize()
        self._advertise()

        print("BLE advertising started")


    
    
    def _irq(self, event, data):
        # print("_advertising", self._advertising, "disconnet_ble", self._disconnet_ble)
        print("IRQ event:", event)
        if event == _IRQ_CENTRAL_CONNECT:
            conn_handle, _, _ = data
            print("New connection", conn_handle)
            self._connections.add(conn_handle)
            self._ble.gattc_exchange_mtu(conn_handle)
        elif event == _IRQ_CENTRAL_DISCONNECT:
            conn_handle, _, _ = data
            print("Disconnected", conn_handle)
            if conn_handle in self._connections:
                self._connections.remove(conn_handle)
            
            # self._connections.remove(conn_handle)
            self._advertising = False
            # self._ble.gap_advertise(None)
            # self._disconnet_ble = True
            self._advertise()

        elif event == _IRQ_GATTS_WRITE:
            conn_handle, value_handle = data
            verify = self._ble.gatts_read(value_handle)
            if verify.decode("utf-8") == "stop":
                self._disconnet_ble = True
                self._advertising = False
                self._ble.gap_advertise(None)
            else:
                if value_handle == self._handle_rx and self._write_callback:
                    self._write_callback(verify)
                    update_file(verify.decode("utf-8"))

    def is_connected(self):
        return len(self._connections) > 0

    
    def update(self, voltage, current):
        """Update values and refresh advert packet at most every 5s."""
        self._voltage = voltage
        self._current = current

        # print("Call Update function-------------------------")
        now = utime.ticks_ms()
        if utime.ticks_diff(now, self._last_adv) >= self._adv_interval_ms:
            # print("Call advertise function")
            self._advertise()
            self._last_adv = now

    def _advertise(self):    
        adv = (
            _field(_AD_FLAGS, bytes((0x06,))) +
            _field(_AD_NAME,  self._name.encode())
        )

        # Scan response: 2-byte company ID (0xFFFF = not assigned) + sensor string
        readable = "V:{:.2f},I:{:.2f}".format(self._voltage, self._current)
        resp = _field(_AD_MANUFACTURER, b'\xFF\xFF' + readable.encode("utf-8"))
        # print("resp : ", resp)
        self._ble.gap_advertise(500000, adv_data=adv, resp_data=resp)


    def on_write(self, callback):
        self._write_callback = callback

    def _initialize(self):

        def on_rx(v):
            print("RX", v)
        self.on_write(on_rx)