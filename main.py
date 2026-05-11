import gc
import utime
from micropython import const

# from helper_storage import DataLogger, SDManager
# from helper_core import CoreLogger
# from helper_mqtt import MQTTManager
# from helper_wifi import WiFiManager
# from helper_config import refresh_conf
from helper_ble import BLEMonitor
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

    # =========================
    # START DELAY
    # =========================
    # update_oled_display_statement("BLE Config Mode")
    ble_monitor = BLEMonitor(name=_device_id)
    for i in range(10):
        print(f"Start in {10 - i}.")
        # update_oled_display_statement(f"Start in {10 - i}.")
        utime.sleep_ms(1000)
        gc.collect()
    print("Main function initialized with device ID:", _device_id)
    # =========================
    # WIFI CHECK
    # =========================

# =========================
# MAIN
# =========================
if __name__ == "__main__":
    log_sensor_data(interval_ms=int(_interval))
