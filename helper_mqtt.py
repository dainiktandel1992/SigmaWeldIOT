import gc
from umqtt.simple import MQTTClient
from helper_var import _mqtt_host, _device_id, _mqtt_port, _topic


class MQTTManager:

    def __init__(self):
        self._client    = None
        self._connected = False

    def connect(self):
        if self._connected:
            return True
        try:
            gc.collect()
            self._client = MQTTClient(
                client_id=_device_id,
                server=_mqtt_host,
                port=_mqtt_port,
                ssl=False,
                keepalive=30,
            )
            self._client.connect()
            self._connected = True
            # print("MQTT: connected ✅")
            return True
        except Exception as e:
            print("MQTT: connection failed:", e)
            self._connected = False
            self._client    = None
            return False

    def is_connected(self):
        return self._connected

    def convert_seconds(self, seconds: int) -> dict:
        hours = seconds // 3600
        remaining = seconds % 3600
        
        minutes = remaining // 60
        secs = remaining % 60

        return f"{hours}:{minutes}:{secs}"

    def publish_batch(self, records):
        """Send all records as a single JSON array payload.
        Returns True on success, False on failure.
        """
        if not self._connected:
            return False
        try:
            gc.collect()
            parts = []
            for r in records:
                if r["AT"]:
                    arc = str(self.convert_seconds(r['AT']))
                    arc_split = arc.split(":")
                    r["h"], r["m"], r["s"] = arc_split
                if r.get("P") == 0 and len(records) > 1:
                    print("mqtt publist stop... ")
                    continue
                parts.append('{{"datetime":"{}","deviceid":"{}","voltage":"{}","current":"{}","heartbeat":"{}","archour":"{}","arcmin":"{}","arcsec":"{}","operator_id":"0"}}'.format(r["T"], r["ID"], r["V"], r["C"], r["HB"], r["h"], r["m"], r["s"]))
            payload = "[" + ",".join(parts) + "]"
            self._client.publish(_topic, payload, qos=0)
            # print("MQTT: batch of {} published".format(len(records)))
            return True
        except Exception as e:
            print("MQTT: publish failed:", e)
            self._connected = False
            return False

    def stop(self):
        if self._client:
            try:
                self._client.disconnect()
            except Exception:
                pass
        self._connected = False
        self._client    = None
        gc.collect()
        # print("MQTT: disconnected")