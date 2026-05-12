""" import gc
import utime
from helper_storage import (DataLogger, SDManager)
from helper_core import CoreLogger
from helper_mqtt import MQTTManager
from helper_wifi import WiFiManager
from helper_config import refresh_conf
from helper_ble import BLEMonitor
from helper_var import _min_current, _interval, _voltage_f, _current_slope, _current_offset, _adc_sample, _device_id,_log_folder
from helper_modules import update_oled_display_statement

def log_sensor_data(interval_ms=900):
    gc.collect()
    sd_manager = SDManager()
    sd_manager.mount()
    logger = DataLogger(
        sd_manager=sd_manager,
        base_dir=_log_folder,
        buffer_size=5
    )
    for i in range(10):
        update_oled_display_statement(f"Start in {10 - i}.")
        utime.sleep_ms(1000)
        gc.collect()
    wifi_manager = WiFiManager()
    if wifi_manager.is_connected():
        update_oled_display_statement("Wifi Connect.")
        refresh_conf()
    else:
        update_oled_display_statement("Wifi No Found.")
        utime.sleep_ms(1000)
        update_oled_display_statement("")
        utime.sleep_ms(500)
        update_oled_display_statement("Wifi No Found.")
        utime.sleep_ms(2000)

    mqtt_manager = MQTTManager()

    ble_monitor = BLEMonitor(name=_device_id)
    gc.collect()
    core = CoreLogger(
        logger=logger,
        sd_m=sd_manager,
        wifi_m=wifi_manager,
        mqtt_m=mqtt_manager,
        adc_samples=_adc_sample,
        process_interval=interval_ms,
        ble_m=ble_monitor,
        min_current= int(_min_current),
        v_f = _voltage_f,
        c_s = _current_slope,
        c_o = _current_offset,
        device_id = _device_id,
        log_folder = _log_folder
    )
    core.start()

if __name__ == "__main__":
    log_sensor_data(interval_ms = int(_interval))


 """