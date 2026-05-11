import utime
import gc
import ujson as json
import os
import _thread
import machine
import ujson as json
from helper_modules import (
    voltage_adc,
    current_adc,
    get_average_voltage,
    read_time_tuple,
    update_oled_display,
    update_oled_display_statement
)

RETRY_INTERVAL_MS = 60_000
MQTT_BATCH_SIZE   = 10

def load_counter(base_dir):
    try:
        with open(f"{base_dir}/counter.txt", "r") as f:
            value = int(f.read().strip())
    except:
        with open(f"{base_dir}/counter.txt", "w") as f:
            f.write("0")
        value = 0
    return value
 
 
class CoreLogger:
    def __init__(self, logger, sd_m,
                 wifi_m=None, mqtt_m=None, ble_m=None,
                 adc_samples=100, process_interval=1000,
                 min_current=20, v_f=4, c_s=40, c_o=12, device_id = 1, log_folder = "/sd/logs"):
 
        self.logger   = logger
        self.sd_m     = sd_m
        self.wifi_m   = wifi_m
        self.mqtt_m   = mqtt_m
        self.ble_m    = ble_m
        self.adc_samples      = adc_samples
        self.process_interval = process_interval
        self.last_adc     = 0
        self.last_process = 0
        self.last_retry   = 0
        self.r_v = 0
        self.r_c = 0
        self.v_f = int(v_f)
        self.c_s = int(c_s)
        self.c_o = int(c_o)
        self.min_current  = min_current
        self.voltage =0
        self.current =0

        self._publish_lock    = _thread.allocate_lock()
        self._publish_running = False
        self._pending_batch   = []
        self._next_offset     = 0
        self.mqtt_batch_size = MQTT_BATCH_SIZE
        self.device_id = device_id
        self.catch_live = False
        self.timestamp = ""
        self.heartbeat = 1
        self.counter = 0
        self._current_backlog_file = ""
        self.log_folder = log_folder
        self.published_file = f"{self.log_folder}/published.txt"
        self.offset_file = f"{self.log_folder}/pub_offset.txt"


        self.load_state()
        self.counter = load_counter(self.log_folder)

        self._last_pub        = self._load_int(self.published_file, 0)
        self._last_pub_offset = self._load_int(self.offset_file, 0)

    # ── ADC ───────────────────────────────────────────────────────────────────

    def save_state(self):
        try:
            data = {
                "file": self._current_backlog_file,
                "offset": self._last_pub_offset,
                "last_at": self._last_pub
            }

            with open(f"{self.log_folder}/publish_state.json", "w") as f:
                f.write(json.dumps(data))

        except Exception as e:
            print("save_state error:", e)

    def load_state(self):
        try:
            with open(f"{self.log_folder}/publish_state.json", "r") as f:
                data = json.loads(f.read())

            self._current_backlog_file = data.get("file", "")
            self._last_pub_offset = data.get("offset", 0)
            self._last_pub = data.get("last_at", 0)

        except:
            self._current_backlog_file = ""
            self._last_pub_offset = 0
            self._last_pub = 0

    def read_adc(self):
        self.r_v = get_average_voltage(voltage_adc, self.adc_samples)
        self.r_c = get_average_voltage(current_adc, self.adc_samples)

    def convert_seconds(self, seconds: int) -> dict:
        hours = seconds // 3600
        remaining = seconds % 3600
        
        minutes = remaining // 60
        secs = remaining % 60

        return {
            "h": str(hours),
            "m": str(minutes),
            "s": str(secs)
        }

    # ── Process ───────────────────────────────────────────────────────────────

    def is_valid_time(self, ts):

        try:
            year = int(ts.split("-")[0])

            if year < 2024:
                return False

            return True

        except:
            return False

    def process_data(self):


        raw_v   = round(self.r_v * 5, 2)
        self.voltage = round(self.v_f * raw_v, 2)
        raw_c   = round(self.r_c * 5, 2)
        self.current = round((self.c_s * raw_c) - self.c_o, 2)

        if not self.sd_m.ismounted():
            update_oled_display_statement("E: SD not found.")
            return

        self.timestamp = read_time_tuple()

        if not self.is_valid_time(self.timestamp):
            update_oled_display_statement("Time error")
        else:
            self.counter += 1


        result = self.convert_seconds(self.counter)
        data_time = f"{result['h']}:{result['m']}:{result['s']}"


        unpublished = self.counter - 1 - self._last_pub
        retry_due   = utime.ticks_diff(utime.ticks_ms(), self.last_retry) >= RETRY_INTERVAL_MS
        print("Unpublish: ", unpublished)
    
        if self.current >= self.min_current:
            self.mqtt_batch_size = MQTT_BATCH_SIZE
            self.heartbeat = 0
        else:
            self.mqtt_batch_size =50
            self.heartbeat = 1
            self.current = 0

        # ---------------------------
        # WIFI OFF -> normal store
        # ---------------------------
        if not (self.wifi_m and self.wifi_m.is_connected()):
            update_oled_display(self.voltage, self.current, data_time, "E", "W")

            self.logger.add(
                T=str(self.timestamp),
                V=str(self.voltage),
                C=str(self.current),
                ID=str(self.device_id),
                HB=self.heartbeat,
                AT=self.counter
            )
            return

        if (unpublished >= 5 and self.current >= self.min_current and not self._publish_running):

            live_record = {
                "T": str(self.timestamp),
                "V": str(self.voltage),
                "C": str(self.current),
                "ID": str(self.device_id),
                "HB": self.heartbeat,
                "AT": self.counter,
                "P": 0
            }

            # save to SD first
            self.logger.add(**live_record)

            # publish instantly
            self._pending_batch = [live_record]
            self.catch_live = True
            self._start_publish_thread()

            update_oled_display(
                self.voltage,
                self.current,
                data_time,
                "W",
                "LIVE"
            )

        else:
            # normal record store
            self.logger.add(
                T=str(self.timestamp),
                V=str(self.voltage),
                C=str(self.current),
                ID=str(self.device_id),
                HB=self.heartbeat,
                AT=self.counter
            )

            update_oled_display(self.voltage, self.current, data_time,"W", "OK")

        # if thread running stop here
        if self._publish_running:
            return

        # publish backlog from SD
        if unpublished >= self.mqtt_batch_size or (retry_due and unpublished > 0):

            batch = self._read_batch()

            if batch:
                self._pending_batch = batch
                self._start_publish_thread()

                update_oled_display(self.voltage,self.current,data_time,"W","BACKLOG")

            self.last_retry = utime.ticks_ms()

    # ── Read batch from SD on main thread ─────────────────────────────────────

    def _read_batch(self):
        batch = []
        new_offset = self._last_pub_offset

        try:

            # first time only
            if not self._current_backlog_file:
                self._current_backlog_file = self.logger.get_next_file("")

            path = self._current_backlog_file

            print("Read path:", path)
            print("Offset:", self._last_pub_offset)

            if not path:
                return []

            # safety reset if offset > file size
            size = os.stat(path)[6]

            if self._last_pub_offset > size:
                self._last_pub_offset = 0
                new_offset = 0

            with open(path, "r") as f:

                f.seek(self._last_pub_offset)

                while len(batch) < self.mqtt_batch_size:

                    line = f.readline()

                    if not line:

                        # maybe next file exists
                        next_file = self.logger.get_next_file(path)

                        if next_file != path:
                            self._current_backlog_file = next_file
                            self._last_pub_offset = 0
                            self._next_offset = 0
                            self.save_state()

                        break

                    stripped = line.strip()

                    if not stripped:
                        new_offset = f.tell()
                        continue

                    try:
                        record = json.loads(stripped)
                    except:
                        new_offset = f.tell()
                        continue

                    if record.get("AT", 0) <= self._last_pub:
                        new_offset = f.tell()
                        continue

                    batch.append(record)
                    new_offset = f.tell()

            if batch:
                self._next_offset = new_offset

            return batch

        except Exception as e:
            print("SD read error:", e)
            return []

    def _start_publish_thread(self):
        with self._publish_lock:
            if self._publish_running:
                return
            self._publish_running = True
        try:
            _thread.start_new_thread(self._publish_worker, ())
        except Exception as e:
            print("Thread start error:", e)
            self._publish_running = False

    def _publish_worker(self):
        batch   = self._pending_batch
        success = False

        if not batch:
            self._publish_running = False
            return

        print("MQTT: publishing {} record(s), AT {} to {}".format(len(batch), batch[0]["AT"], batch[-1]["AT"]))
        if self.catch_live:
            try:
                gc.collect()
                if not self.mqtt_m.is_connected():
                    if not self.mqtt_m.connect():
                        update_oled_display(0, 0, 0,"E", "MQTT")
                        print("MQTT: connect failed — will retry next cycle")
                        return   # finally will still run
                success = self.mqtt_m.publish_batch(batch)
            except Exception as e:
                print("MQTT worker error:", e)
                self.logger.add(
                    T   =str(self.timestamp),
                    V   =str(self.voltage), 
                    C   =str(self.current), 
                    ID  = str(self.device_id),
                    HB  = self.heartbeat,
                    AT  =self.counter,
                )
            finally:
                self.catch_live = False
                self._pending_batch   = []
                self._publish_running = False
            return

        try:
            gc.collect()
            if not self.mqtt_m.is_connected():
                if not self.mqtt_m.connect():
                    update_oled_display(0, 0, 0,"E", "MQTT")
                    print("MQTT: connect failed — will retry next cycle")
                    return   # finally will still run
            success = self.mqtt_m.publish_batch(batch)

        except Exception as e:
            print("MQTT worker error:", e)

        finally:
            # Save progress ONLY on confirmed success
            if success:
                self._last_pub        = batch[-1]["AT"]
                self._last_pub_offset = self._next_offset
                self._save_int(self.published_file, self._last_pub)
                self._save_int(self.offset_file, self._last_pub_offset)
            else:
                print("MQTT: publish failed — AT {} to {} queued for retry".format(batch[0]["AT"], batch[-1]["AT"]))

            try:
                self.mqtt_m.stop()
            except Exception:
                pass

            self._pending_batch   = []
            self._publish_running = False

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _load_int(self, path, default):
        try:
            with open(path, "r") as f:
                return int(f.read().strip())
        except Exception:
            return default

    def _save_int(self, path, value):
        try:
            with open(path, "w") as f:
                f.write(str(value))
        except Exception as e:
            print("Save error ({}): {}".format(path, e))

    # ── Main loop ─────────────────────────────────────────────────────────────

    def start(self):

        rtc = machine.RTC()
        self.prev_sec = -1
        self.last_adc = utime.ticks_ms()

        while True:

            now = utime.ticks_ms()

            # ADC sampling every 10ms
            if utime.ticks_diff(now, self.last_adc) >= 10:
                self.read_adc()
                self.last_adc += 10

            # One process per RTC second
            current_sec = rtc.datetime()[6]

            if current_sec != self.prev_sec:
                self.prev_sec = current_sec

                if not self.sd_m.mounted:
                    self.sd_m.mount()

                self.process_data()

            utime.sleep_ms(5)
