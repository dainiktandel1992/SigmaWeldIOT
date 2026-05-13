import gc
import uos
import urequests
import utime
import os
import ujson
import ugit


def check_if_file_exists(filepath):
    try:
        with open(filepath, "r"):
            return True
    except OSError:
        return False


def validate_file(_conf):
    firstTest = False
    secondTest = False
    with open(_conf) as f:
        for line in f:
            if "=" in line:
                key, value = map(str.strip, line.split("=", 1))
                if key == "uuid" and value: firstTest = True
                elif key == "device_id" and value: secondTest = True
    return firstTest and secondTest


def download_file(_tg, _tn, _fn):
    success = False  # Track whether the download was successful
    while not success:
        try:
            gc.collect()  # Free unused memory
            print(f"Free memory before download: {gc.mem_free()} bytes")
            _url = f"https://satellite-tech-temp.s3.amazonaws.com/{_tg}/{_tn}/{_fn}"
            print(_url)
            
            try:
                _res = urequests.get(_url, timeout=20)
                if _res.status_code == 200:
                    with open(f"flash/{_fn}", "wb") as _file:
                        _file.write(_res.content)
                    success = True  # Mark success if download completes
                _res.close()
            except Exception as e:
                print(f"An error occurred while downloading {_fn}: {e}")
            utime.sleep(2)
        except Exception as e:
            print(f"An error occurred: {e}")


def read_config(file_name):
    _config = {}
    with open(file_name) as f:
        for line in f:
            if "=" in line:
                key, value = line.strip().split("=", 1)
                _config[key.strip()] = value.strip()
    return _config


def read_file(file_name):
    with open(file_name, "r") as f:
        return f.read()

 
def update_connection_file(input_string):
    patterns = {
        "wn=": "ssid =",
        "wp=": "psk =",
        "cf=": "reset_files",
        "uf=": "upload_files",

        # config.ini values
        "mc=": "min_current =",
        "vf=": "voltage_f =",
        "cs=": "current_slope =",
        "co=": "current_offset =",
        "as=": "adc_samples =",
    }

    numeric_keys = [
        "min_current =",
        "voltage_f =",
        "current_slope =",
        "current_offset =",
        "adc_samples =",
    ]

    replacement_key = None
    new_value = None

    for key, value in patterns.items():
        if input_string.startswith(key):
            new_value = input_string[len(key):]
            replacement_key = value
            break

    if replacement_key is None or new_value is None:
        print("Invalid input pattern.")
        return
    
     # Validate numeric values
    if replacement_key in numeric_keys:

        try:
            # int for adc_samples
            if replacement_key == "adc_samples =":
                new_value = int(new_value)
            else:
                new_value = float(new_value)

        except ValueError:
            print("Invalid numeric value")
            return

    if replacement_key == "reset_files":
        if new_value == "1":
            # delete_files()
            rename_files()
            print("Delete files successfully.")
        return
    
    
    if replacement_key == "upload_files":
        if new_value == "1":
            upload_file(
                    f"https://sigma-weld-config.s3.us-east-1.amazonaws.com/Machine-Test/config.ini",
                    "config.ini"
                )
        return

    # Decide which file to update
    if replacement_key in [
        "min_current =",
        "voltage_f =",
        "current_slope =",
        "current_offset =",
        "adc_samples =",
    ]:
        file_path = "config.ini"
    else:
        file_path = "connection.ini"

    try:
        with open(file_path, 'r') as file:
            lines = file.readlines()

        with open(file_path, 'w') as file:
            for line in lines:
                if line.startswith(replacement_key):
                    # print("Updating :", replacement_key)
                    line = f"{replacement_key} {new_value}\n"
                file.write(line)
        print(f"Successfully updated file '{file_path}'")

    except OSError as e:
        print(f"An error occurred: {e}")


def delete_files():

    files_to_delete = [
        "counter.txt",
        "published.txt",
        "pub_offset.txt",
    ]

    for file_name in files_to_delete:

        try:
            print("Deleting file :", file_name)
            uos.remove(file_name)
            print(f"File {file_name} Deleted Successfully:")
        except OSError:
            print("File not found:", file_name)


        # Recreate empty file
        try:
            with open(file_name, "w") as f:
                f.write("")

            print("Recreated empty file:", file_name)

        except Exception as e:
            print("Recreate failed:", e)

        gc.collect()

    return
     
def rename_files():
    files_to_rename = [
        "counter.txt",
        "published.txt",
        "pub_offset.txt",
    ]

    # Delete files
    for file_name in files_to_rename:

        """ print("*******************************")
        print(uos.listdir())
        print("*******************************") """

        # Check file exists first
        """ try:
            uos.stat(file_name)
        except OSError:
            print("File not found:", file_name)
            continue """

        try:

            
            name, ext = file_name.rsplit(".", 1)
            new_file = "{}_{}.{}".format(name, 1, ext)
            print("Renaming:", file_name, " to ", new_file)

            gc.collect()

            # temp_file = file_name + ".new"
            
            with open(file_name, "rb") as src:
                with open(new_file, "wb") as dst:
                    while True:
                        chunk = src.read(512)
                        if not chunk:
                            break

                        dst.write(chunk)
                        del chunk
                        gc.collect()

            gc.collect()
            utime.sleep_ms(200)

            print("Renaming:", file_name, " to ", new_file , " completed")
            
            # Recreate empty file
            try:
                with open(file_name, "w") as f:
                    f.write("")

                print("Recreated empty file:", file_name)

            except Exception as e:
                print("Recreate failed:", e)

            gc.collect()

            # print("Deleted:", file_name)
        except Exception as e:
            print("Rename failed:", e)
            try:
                uos.remove(new_file)
            except:
                pass

            gc.collect()
    
    return


def upload_file(url, filename):
    try:
        gc.collect()

        with open(filename, "rb") as f:
            file_data = f.read()

        r = urequests.put(
            url,
            data=file_data,
            headers={
                "Content-Type": "application/octet-stream"
            }
        )

        if r.status_code == 200 or r.status_code == 201:
            print("Upload Success")
        else:
            print("Upload Failed:", r.status_code)

        r.close()
        del r
        gc.collect()

    except Exception as e:
        print("Upload error:", e)



def downloadFile(_conf):
    _tg = _conf["MQTT_CLIENT_ID"]
    _tn = _conf["THING_NAME"]
    _file_ext = [".cert.pem", ".private.key", "-Policy"]
    for _ext in _file_ext:
        _fn = _tn + _ext
        file_path = f"flash/{_fn}"
        if not check_if_file_exists(file_path):
            download_file(_tg, _tn, _fn)
        else:
            print("File Exists", file_path)
        utime.sleep(1)




def ota_update11(version):
    url = "https://sigmaweld-ota-update.s3.us-east-1.amazonaws.com/version.json"
    r = urequests.get(url)
    data = ujson.loads(r.text)
    latest_version = data["version"]
    
    if latest_version != version:
        print("New update available")
        for file in data["files"]:
            try:
                gc.collect()
                print(f"Free memory before download: {gc.mem_free()} bytes")
                _url = f"https://sigmaweld-ota-update.s3.us-east-1.amazonaws.com/{file}"
                print(_url)
                
                try:
                    _res = urequests.get(_url, timeout=20)
                    if _res.status_code == 200:
                        with open(file, "wb") as _file:
                            while True:
                                chunk = _res.raw.read(512)
                                if not chunk:
                                    break
                                _file.write(chunk)
                    _res.close()
                except Exception as e:
                    print(f"An error occurred while downloading {file}: {e}")
                utime.sleep(2)
            except Exception as e:
                print(f"An error occurred: {e}")

        print("Update complete")



def ota_update(current_version):
    try:
        gc.collect()
        print("Free RAM before OTA:", gc.mem_free())
        version_url = "https://sigmaweld-ota-update.s3.us-east-1.amazonaws.com/version.json"
        print("Checking OTA version...", version_url)
        r = urequests.get(version_url, timeout=20)
        print("Checking OTA version...", r.status_code)

        if r.status_code != 200:
            print("Failed to fetch version file")
            r.close()
            return False

        data = ujson.loads(r.text)
        r.close()

        # latest_version = data["version"]

        print("Current Version :", current_version)
        print("Latest Version  :", data["version"])

        if data["version"] == current_version:
            print("Device already up to date")
            return False

        print("New update available")
        files = data["files"]
        for file in files:
            try:
                gc.collect()
                print("--------------------------------")
                print("Downloading:", file)
                print("Free RAM:", gc.mem_free())

                file_url = (
                    "https://sigmaweld-ota-update.s3.us-east-1.amazonaws.com/"
                    + file
                )

                response = urequests.get(file_url, timeout=20)
                if response.status_code != 200:
                    print("Failed:", file)
                    response.close()
                    continue
                temp_file = file + ".new"
                with open(temp_file, "wb") as f:
                    while True:
                        chunk = response.raw.read(512)
                        if not chunk:
                            break
                        f.write(chunk)
                response.close()
                # Replace old file only after successful download
                try:
                    uos.remove(file)
                except:
                    pass

                uos.rename(temp_file, file)
                print("Updated:", file)
                gc.collect()
                utime.sleep_ms(500)

            except Exception as e:
                print("File update failed:", file)
                print("Error:", e)

        print("OTA update complete")
        return True

    except Exception as e:
        print("OTA failed:", e)
        return False



def ota_update_ugit():
    try:
        gc.collect()
        print("Free RAM before OTA:", gc.mem_free())
        print("Checking OTA version...")

        changes = ugit.check_for_updates(isconnected=True)

        gc.collect()
        print("Free RAM after check:", gc.mem_free())
        print(changes)

        if changes['new'] or changes['changed']:
            gc.collect()
            ugit.pull_all(isconnected=True)
            gc.collect()
            print("OTA update complete")
            return True

        print("No updates available")
        return False

    except Exception as e:
        print("OTA failed:", e)
        return False


