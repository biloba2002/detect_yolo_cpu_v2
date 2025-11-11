import json
from datetime import datetime, timezone
import paho.mqtt.client as mqtt
from src.logger import get_logger

logger = get_logger(__name__)

# --- helpers ------------------------------------------------------------

def _ok(rc) -> bool:
    try:
        return int(rc) == 0
    except Exception:
        try:
            return int(getattr(rc, "value", rc)) == 0
        except Exception:
            return False

def _iso_now():
    return datetime.now(timezone.utc).astimezone().isoformat()

def _get(obj, *keys, default=None):
    """Accès tolérant: supporte objets (attributs) et dicts imbriqués."""
    cur = obj
    for k in keys:
        if cur is None:
            return default
        if isinstance(cur, dict):
            cur = cur.get(k, default)
        else:
            cur = getattr(cur, k, default)
    return cur if cur is not None else default

# --- publisher ----------------------------------------------------------

class MQTTPublisher:
    def __init__(self, config):
        self.cfg = config
        # Pas de callback_api_version pour compat v1/v2
        self.client = mqtt.Client(protocol=mqtt.MQTTv5, transport="tcp")

        username = _get(self.cfg, "mqtt", "username", default="") or ""
        password = _get(self.cfg, "mqtt", "password", default="") or ""
        if username:
            self.client.username_pw_set(username, password)

        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect

        broker = _get(self.cfg, "mqtt", "broker")
        port = _get(self.cfg, "mqtt", "port", default=1883)
        logger.info("mqtt_client_initialized", extra={"broker": broker, "port": port})

    # v1: on_connect(client, userdata, flags, rc)
    # v2: on_connect(client, userdata, flags, reasonCode, properties)
    def _on_connect(self, client, userdata, flags, rc_or_reason, properties=None):
        if _ok(rc_or_reason):
            logger.info("mqtt_connection_established", extra={"result_code": "Success"})
            logger.info("mqtt_connected", extra={"broker": _get(self.cfg, "mqtt", "broker")})
        else:
            try:
                rc_val = int(rc_or_reason)
            except Exception:
                rc_val = str(rc_or_reason)
            logger.error("mqtt_connection_failed", extra={"result_code": rc_val})

    # v1: on_disconnect(client, userdata, rc)
    # v2: on_disconnect(client, userdata, reasonCode, properties)
    def _on_disconnect(self, client, userdata, rc_or_reason, properties=None):
        if _ok(rc_or_reason):
            logger.info("mqtt_disconnected", extra={"result_code": "Success"})
        else:
            try:
                rc_val = int(rc_or_reason)
            except Exception:
                rc_val = str(rc_or_reason)
            logger.warning("mqtt_disconnected", extra={"result_code": rc_val})

    def connect(self):
        broker = _get(self.cfg, "mqtt", "broker")
        port = _get(self.cfg, "mqtt", "port", default=1883)
        self.client.connect(broker, port, keepalive=60)
        self.client.loop_start()

    def disconnect(self):
        try:
            self.client.loop_stop()
        finally:
            self.client.disconnect()

    # --- Topics helpers -------------------------------------------------

    def _sensor_topic(self, camera: str, metric: str) -> str:
        tpl = _get(self.cfg, "mqtt", "topics", "sensor")  # e.g. detect_yolo_cpu_v2/sensor/{camera}/{metric}
        topic = (tpl or "detect_yolo_cpu_v2/sensor/{camera}/{metric}").replace("{camera}", camera).replace("{metric}", metric)
        return topic.replace("//", "/").rstrip("/")

    def _image_topic(self, camera: str) -> str:
        tpl = _get(self.cfg, "mqtt", "topics", "image")
        topic = (tpl or "detect_yolo_cpu_v2/image/{camera}").replace("{camera}", camera)
        return topic.replace("//", "/").rstrip("/")

    def _notify_topic(self, camera: str | None, zone: str | None, audio: bool) -> str:
        tpl = _get(self.cfg, "mqtt", "topics", "notify")  # e.g. detect_yolo_cpu_v2/notify/{camera}/{zone}
        tpl = tpl or "detect_yolo_cpu_v2/notify/{camera}/{zone}"
        if audio:
            # audio -> topic racine
            root = tpl.split("{", 1)[0].rstrip("/")
            return root or "detect_yolo_cpu_v2/notify"
        topic = tpl.replace("{camera}", camera or "").replace("{zone}", zone or "")
        return topic.replace("//", "/").rstrip("/")

    # --- Publish --------------------------------------------------------

    def publish_sensor(self, camera: str, metric: str, value):
        payload = {"value": value, "timestamp": _iso_now(), "unit": "count"}
        topic = self._sensor_topic(camera, metric)
        qos = _get(self.cfg, "mqtt", "qos", default=0)
        retain = _get(self.cfg, "mqtt", "retain", default=False)
        self.client.publish(topic, json.dumps(payload, ensure_ascii=False), qos=qos, retain=retain)

    def publish_image(self, camera: str, image_path: str):
        topic = self._image_topic(camera)
        payload = {"path": image_path, "timestamp": _iso_now()}
        qos = _get(self.cfg, "mqtt", "qos", default=0)
        retain = _get(self.cfg, "mqtt", "retain", default=False)
        self.client.publish(topic, json.dumps(payload, ensure_ascii=False), qos=qos, retain=retain)

    def publish_notification(self, camera: str, zone: str | None, message: str, audio: bool = False, extra: dict | None = None):
        topic = self._notify_topic(camera, zone, audio)
        payload = {
            "type": "text",
            "audio": bool(audio),
            "message": message,
            "camera": camera,
            "timestamp": _iso_now(),
        }
        if zone:
            payload["zone"] = zone
        if extra:
            # merge sans écraser 'message', 'audio', 'camera', 'timestamp'
            for k, v in extra.items():
                if k not in payload:
                    payload[k] = v
        qos = _get(self.cfg, "mqtt", "qos", default=0)
        retain = _get(self.cfg, "mqtt", "retain", default=False)
        self.client.publish(topic, json.dumps(payload, ensure_ascii=False), qos=qos, retain=retain)
        logger.info("notification_published", extra={"topic": topic, "camera": camera, "zone": zone, "audio": bool(audio)})
