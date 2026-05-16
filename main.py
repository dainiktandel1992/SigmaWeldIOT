import gc
import utime
import machine
import random
from micropython import const

# from helper_storage import DataLogger, SDManager
# from helper_core import CoreLogger
# from helper_mqtt import MQTTManager
from helper_wifi import WiFiManager
from helper_config import refresh_conf
from helper_ble import BLEMonitor
from helper_file import ota_update
from helper_var import (
    _min_current,
    _interval,
    _voltage_f,
    _current_slope,
    _current_offset,
    _adc_sample,
    _device_id,
    _log_folder,
)

# from helper_modules import update_oled_display_statement
CURRENT_VERSION = "1.0.2"

# =========================
# Main Logger Function
# =========================
def log_sensor_data(interval_ms=900):
    gc.collect()
    # =========================
    # SD CARD
    # =========================
    """ sd_manager = SDManager()
    sd_manager.mount()
    logger = DataLogger(
        sd_manager=sd_manager,
        base_dir=_log_folder,
        buffer_size=5
    ) """
    
    wifi_manager = WiFiManager()
    if wifi_manager.is_connected():
        print("Wifi Connect.")
        # refresh_conf()

        # print("Checking for OTA updates...")
        if ota_update(CURRENT_VERSION):
            print("OTA update successful. Restarting device...")
            utime.sleep_ms(2000)
            # machine.reset()  # Uncomment this line to enable automatic restart after OTA update
        else:
            print("No OTA update available or update failed.")

    else:
        print("Wifi No Found.")
        utime.sleep_ms(1000)

    for i in range(10):
        print(f"Start in {10 - i}.")
        # update_oled_display_statement(f"Start in {10 - i}.")
        utime.sleep_ms(1000)
        gc.collect()
    
    #Reboot/ Reset ESP32
    """ print("Restarting...")
    print("Disconnect Wifi.....")
    wifi_manager.stop()
    utime.sleep_ms(2000)
    gc.collect()
    machine.reset() """

    # =========================
    # START DELAY
    # =========================
    # update_oled_display_statement("BLE Config Mode")
    ble_monitor = BLEMonitor(name=_device_id)

    print("Main work starting...")

    while True:
        current = random.randint(100, 1000)
        voltage = random.randint(10, 40)
        print(f"Arc Value Publish current : ", current, ", voltage : ",voltage)
        ble_monitor.update(voltage, current)
        utime.sleep(2)

    
    # =========================
    # WIFI CHECK
    # =========================

# =========================
# MAIN
# =========================
if __name__ == "__main__":
    log_sensor_data(interval_ms=int(_interval))
