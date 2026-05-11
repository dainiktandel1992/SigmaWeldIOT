from machine import SPI, Pin
import ujson as json
import os
from helper_modules import update_oled_display_statement


def load_counter(base_dir):
    try:
        with open(f"{base_dir}/counter.txt", "r") as f:
            value = int(f.read().strip())
    except:
        ensure_dir(base_dir)
        with open(f"{base_dir}/counter.txt", "w") as f:
            f.write("0")
        value = 0
    return value

def save_counter(base_dir,value):
    with open(f"{base_dir}/counter.txt", "w") as f:
        f.write(str(value))

def ensure_dir(path):
    try:
        os.mkdir(path)
    except:
        pass


class DataLogger:
    def __init__(self,sd_manager,base_dir="/sd/logs",buffer_size=5):
        self.sd_manager = sd_manager
        self.base_dir = base_dir
        self.buffer_size = buffer_size
        self.buffer = []
        self.current_file = None
        self.counter = load_counter(base_dir)

    def get_all_files(self):
        files = sorted(os.listdir(self.base_dir))
        return [
            self.base_dir + "/" + f
            for f in files
            if f.endswith(".jsonl")
        ]

    def get_next_file(self, current_file):

        files = sorted(os.listdir(self.base_dir))

        all_files = []

        for name in files:
            if name.endswith(".jsonl"):
                if name == "recovery.jsonl":
                    continue
                all_files.append(self.base_dir + "/" + name)

        if not current_file:
            return all_files[0] if all_files else None

        for i in range(len(all_files)):
            if all_files[i] == current_file:
                if i + 1 < len(all_files):
                    return all_files[i + 1]

        return current_file

    def get_oldest_file(self):

        try:
            files = sorted(os.listdir(self.base_dir))

            for name in files:
                if name == "recovery.jsonl":
                    continue
                if name.endswith(".jsonl"):
                    return self.base_dir + "/" + name

        except:
            pass

        return None

    # ----------------------------------------------
    # T = 2026-05-10 18:59:59
    # => /sd/logs/2026-05-10.jsonl
    # ----------------------------------------------

    def is_valid_time(self, ts):

        try:
            year = int(ts.split("-")[0])

            if year < 2024:
                return False

            return True

        except:
            return False


    def get_filename(self, t):

        if not self.is_valid_time(t):
            update_oled_display_statement("Time error")
            return self.base_dir + "/recovery.jsonl"

        date_part = t.split(" ")[0]      # 2026-05-10
        yyyy, mm, dd = date_part.split("-")

        return "%s/%s-%s-%s.jsonl" % (
            self.base_dir,
            yyyy,
            mm,
            dd
        )

    # ----------------------------------------------
    # Rotate if date changed
    # ----------------------------------------------
    def rotate_if_needed(self, t):

        new_file = self.get_filename(t)

        if new_file != self.current_file:

            self.flush()

            if self.sd_manager.mounted:
                ensure_dir(self.base_dir)

            self.current_file = new_file

    # ----------------------------------------------
    # Add new record
    # ----------------------------------------------
    def add(self, **data):

        if "T" not in data:
            return

        self.counter += 1

        self.rotate_if_needed(data["T"])

        self.buffer.append(data)

        if len(self.buffer) >= self.buffer_size:
            save_counter(self.base_dir,self.counter)
            self.flush()

    # ----------------------------------------------
    # Flush buffer to SD
    # ----------------------------------------------
    def flush(self):
        if not self.buffer:
            return
        if not self.sd_manager.mounted:
            return
        try:
            with open(self.current_file, "ab") as f:
                for row in self.buffer:
                    f.write(json.dumps(row).encode())
                    f.write(b"\n")
            self.buffer.clear()
        except Exception as e:
            #print("write error:", e)
            self.sd_manager.unmount()

    # ----------------------------------------------
    # Force save before restart
    # ----------------------------------------------
    def close(self):
        save_counter(self.base_dir,self.counter)
        self.flush()

class SDManager:
    def __init__(self, mount_point="/sd"):
        self.mount_point = mount_point
        self.sd = None
        self.mounted = False
        self.mount_failed = False
        self.spi = SPI(
            2,
            baudrate=2000000,
            polarity=0,
            phase=0,
            mosi=Pin(13),
            miso=Pin(11),
            sck=Pin(12),
        )
        self.cs = Pin(14, Pin.OUT)
    
    def mount(self):
        try:
            import os
            import sdcard
            self.sd = sdcard.SDCard(self.spi, self.cs)
            os.mount(self.sd, self.mount_point)
            self.mounted = True
            self.mount_failed = False
            # print("✅ SD card mounted")
            return True
        except Exception as e:
            self.mounted = False
            if not self.mount_failed:
                # print("⚠️ No SD card found...")
                self.mount_failed = True
            return False
    
    def unmount(self):
        try:
            import os
            os.umount(self.mount_point)
        except:
            pass
        self.mounted = False
        self.sd = None

    def ismounted(self):
        return self.mounted
