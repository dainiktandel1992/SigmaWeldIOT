from helper_config import read_config
import gc
cloud = read_config("cloud.ini")
config = read_config("config.ini")
connection = read_config("connection.ini")

_device_id       = str(cloud.get("device_id","Machine-111"))
_api_url         = cloud.get("api_url", "https://4rqb6z06lh.execute-api.us-east-1.amazonaws.com/default/sigmaWeldcloud?device_id")
_s3_url          = cloud.get("sss_url", "https://sigma-weld-cloud.s3.us-east-1.amazonaws.com")
_mqtt_port       = int(cloud.get("mqtt_port"))
_topic           = cloud.get("mqtt_topic")
_mqtt_host       = cloud.get("mqtt_host")

_max_ram_records    = int(config.get("max_ram_record"))
_log_folder       = config.get("log_folder","/sd/logs")
_buffer_size        = int(config.get("buffer_size",2))
_min_current        = int(config.get("min_current",20))
_interval           = int(config.get("interval_ms",900))
_voltage_f          = int(config.get("voltage_f",4))
_current_slope      = int(config.get("current_slope",40))
_current_offset     = float(config.get("current_offset",3.4))
_adc_sample         = int(config.get("adc_samples",1000))
_mqtt_push_data     = int(config.get("mqtt_push_data",50))


_ssid      =  connection.get("ssid","admin")
_psk       =  connection.get("psk", "1234567890")

del config
del cloud
del connection
gc.collect()