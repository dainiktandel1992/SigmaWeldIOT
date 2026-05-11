import ubluetooth
from micropython import const
import ubinascii
import uos
import urandom

import utime

from helper_file import (
    update_connection_file,
)

_FLAG_READ = const(0x0002)
_FLAG_WRITE_NO_RESPONSE = const(0x0004)
_FLAG_WRITE = const(0x0008)
_FLAG_NOTIFY = const(0x0010)

_IRQ_CENTRAL_CONNECT    = const(1)
_IRQ_CENTRAL_DISCONNECT = const(2)
_IRQ_GATTS_WRITE        = const(3)



 
def advertising_payload(name=None, services=None):
        payload = bytearray()
        if name:
            payload += bytearray((len(name) + 1, 0x09)) + name
        if services:
            for uuid in services:
                b = bytes(uuid)
                payload += bytearray((len(b) + 1, 0x06)) + b
        return payload

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


class BLEMonitor:

    def __init__(self, name="SmartWeld"):
        self._ble = ubluetooth.BLE()
        print("Device name",name)
        self._ble.active(True)
        self._ble.irq(self._irq)
        uui = generate_random_uuid("S-IT")
        self._UART_UUID = ubluetooth.UUID(uui)
        upld = "u=" + uui
        print("UUID", upld)
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
        self._payload = advertising_payload(name=name, services=[self._UART_UUID])
        self._advertising = False
        self._disconnet_ble = False

        self._initialize()
        self._advertise()

        while True:
            if not self._advertising:
                break
            utime.sleep(1)
            
        """# Advertise for max 30 seconds
        start_time = utime.ticks_ms()
        timeout_ms = 15000   # 30 sec

        while True:

            # Device connected
            if not self._advertising:
                print("BLE connected")
                break

            # Timeout reached
            if utime.ticks_diff(utime.ticks_ms(), start_time) > timeout_ms:
                print("BLE advertise timeout")

                # Stop advertising
                self._ble.gap_advertise(None)

                self._advertising = False
                break

            utime.sleep(1) """

        print("Continue next process...")

    
    
    def _irq(self, event, data):
        print("_advertising", self._advertising, "disconnet_ble", self._disconnet_ble)
        print("IRQ event:", event)
        if event == _IRQ_CENTRAL_CONNECT:
            conn_handle, _, _ = data
            print("New connection", conn_handle)
            self._connections.add(conn_handle)
            self._ble.gattc_exchange_mtu(conn_handle)
        elif event == _IRQ_CENTRAL_DISCONNECT:
            conn_handle, _, _ = data
            print("Disconnected", conn_handle)
            self._connections.remove(conn_handle)
            self._advertising = False
            self._ble.gap_advertise(None)
            self._disconnet_ble = True

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
                    update_connection_file(verify.decode("utf-8"))

    def is_connected(self):
        return len(self._connections) > 0

    def _advertise(self, interval_us=500000):    
        if not self._advertising:
            print("Starting advertising", self._payload)
            self._advertising = True
            self._ble.gap_advertise(interval_us, adv_data=self._payload)

    def on_write(self, callback):
        self._write_callback = callback

    def _initialize(self):

        def on_rx(v):
            print("RX", v)
        self.on_write(on_rx)