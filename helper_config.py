def read_config(filename):
    config = {}

    with open(filename) as f:
        for line in f:
            if "=" in line:
                key, value = line.strip().split("=")
                config[key.strip()] = value.strip()

    return config

def write_config(data):
    with open("config.ini", "w") as f:
        for k, v in data.items():
            f.write("{} = {}\n".format(k, v))

def refresh_conf():
    import gc
    import urequests
    from helper_var import _device_id, _api_url, _s3_url
    from helper_modules import set_time, update_oled_display_statement

    def download_file(url, filename):
        try:
            gc.collect()
            r = urequests.get(url)
            if r.status_code == 200:
                with open(filename, "wb") as f:
                    while True:
                        chunk = r.raw.read(512)
                        if not chunk:
                            break
                        f.write(chunk)
                # print("Downloaded:", filename)
                update_oled_display_statement(f"F: {filename}")
            else:
                # print("Download failed:", url)
                update_oled_display_statement(f"E: Not D")
            r.close()
            del r
            gc.collect()
        except Exception as e:
            print("Download error:", e)

    try:
        gc.collect()
        r = urequests.get(f"{_api_url}={_device_id}")
        if r.status_code != 200:
            r.close()
            del r
            return
        data = r.json()
        r.close()
        del r
        gc.collect()
        counter = data.get("counter")
        if counter != "no":
            if "time" in data:
                set_time(data["time"])
        if data.get("update") == "yes":
            download_file(
                f"{_s3_url}/{_device_id}/config.ini",
                "config.ini"
            )
            download_file(
                f"{_s3_url}/{_device_id}/connection.ini",
                "connection.ini"
            )
            download_file(
                f"{_s3_url}/{_device_id}/cloud.ini",
                "cloud.ini"
            )
        del data
        gc.collect()
    except Exception as e:
        print("refresh_conf error:", e)
        gc.collect()
