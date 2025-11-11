"""
Publication MQTT avec autodiscovery Home Assistant.
"""

import json
import time
from datetime import datetime
from typing import Dict, Optional, List
import paho.mqtt.client as mqtt
from src.config_loader import Config, CameraConfig
from src.logger import get_logger

logger = get_logger(__name__)


class MQTTPublisher:
    """Publisher MQTT avec support autodiscovery Home Assistant."""
    
    def __init__(self, config: Config):
        """
        Initialise le publisher MQTT.
        
        Args:
            config: Configuration de l'application
        """
        self.config = config
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.connected = False
        self.discovery_sent = set()  # Track des entités déjà configurées
        
        # Callbacks
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_publish = self._on_publish
        
        # Credentials si fournis
        if config.mqtt.username and config.mqtt.password:
            self.client.username_pw_set(config.mqtt.username, config.mqtt.password)
        
        logger.info("mqtt_client_initialized", broker=config.mqtt.broker, port=config.mqtt.port)
    
    def connect(self) -> bool:
        """
        Connecte au broker MQTT.
        
        Returns:
            True si connexion réussie
        """
        try:
            self.client.connect(
                self.config.mqtt.broker,
                self.config.mqtt.port,
                60  # keepalive
            )
            self.client.loop_start()
            
            # Attendre la connexion (max 5 secondes)
            timeout = 5
            while not self.connected and timeout > 0:
                time.sleep(0.1)
                timeout -= 0.1
            
            if self.connected:
                logger.info("mqtt_connected", broker=self.config.mqtt.broker)
                return True
            else:
                logger.error("mqtt_connection_timeout")
                return False
                
        except Exception as e:
            logger.error("mqtt_connection_failed", error=str(e))
            return False
    
    def disconnect(self):
        """Déconnecte du broker MQTT."""
        self.client.loop_stop()
        self.client.disconnect()
        logger.info("mqtt_disconnected")
    
    def _on_connect(self, client, userdata, flags, reason_code, properties=None):
# Dans _on_connect
        if reason_code == 0:
            self.connected = True
            logger.info("mqtt_connection_established", result_code=reason_code)
        else:
            self.connected = False
        logger.error("mqtt_connection_failed", result_code=reason_code)
    
    def _on_disconnect(self, client, userdata, flags, reason_code, properties=None):
        """Callback de déconnexion."""
        self.connected = False
        if reason_code != 0:
            logger.warning("mqtt_unexpected_disconnect", result_code=reason_code)
    
    def _on_publish(self, client, userdata, mid, reason_code=None, properties=None):
        """Callback de publication."""
        logger.debug("mqtt_message_published", message_id=mid)
    
    def publish_sensor(
        self,
        camera_name: str,
        metric: str,
        value: int,
        unit: str = "count"
    ) -> bool:
        """
        Publie une valeur de sensor.
        
        Args:
            camera_name: Nom de la caméra
            metric: Nom de la métrique (ex: "detections", "false_detections")
            value: Valeur numérique
            unit: Unité de mesure
            
        Returns:
            True si publié avec succès
        """
        if not self.connected:
            logger.warning("mqtt_not_connected", action="publish_sensor")
            return False
        
        topic = self.config.mqtt.topics['sensor'].format(camera=camera_name, metric=metric)
        
        payload = {
            "value": value,
            "timestamp": datetime.now().isoformat(),
            "unit": unit
        }
        
        try:
            result = self.client.publish(
                topic,
                json.dumps(payload),
                qos=self.config.mqtt.qos,
                retain=self.config.mqtt.retain
            )
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.debug("sensor_published", camera=camera_name, metric=metric, value=value)
                return True
            else:
                logger.error("sensor_publish_failed", camera=camera_name, metric=metric, rc=result.rc)
                return False
                
        except Exception as e:
            logger.error("sensor_publish_exception", camera=camera_name, error=str(e))
            return False
    
    def publish_notification(
        self,
        camera_name: str,
        zone_name: Optional[str],
        message: str,
        audio: bool = False,
        detections: Optional[Dict] = None
    ) -> bool:
        """
        Publie une notification.
        
        Args:
            camera_name: Nom de la caméra
            zone_name: Nom de la zone (ou None si global caméra)
            message: Message texte
            audio: Flag audio activé
            detections: Dict des détections par classe
            
        Returns:
            True si publié avec succès
        """
        if not self.connected:
            logger.warning("mqtt_not_connected", action="publish_notification")
            return False
        
        zone_part = f"/{zone_name}" if zone_name else ""
        topic = self.config.mqtt.topics['notify'].format(camera=camera_name, zone=zone_part)
        # Nettoyer le double slash si pas de zone
        topic = topic.replace("//", "/")
        
        payload = {
            "type": "text",
            "audio": audio,
            "message": message,
            "camera": camera_name,
            "timestamp": datetime.now().isoformat()
        }
        
        if zone_name:
            payload["zone"] = zone_name
        
        if detections:
            payload["detections"] = detections
        
        try:
            result = self.client.publish(
                topic,
                json.dumps(payload),
                qos=self.config.mqtt.qos,
                retain=False  # Notifications jamais retained
            )
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info("notification_published", camera=camera_name, zone=zone_name, message=message)
                return True
            else:
                logger.error("notification_publish_failed", camera=camera_name, rc=result.rc)
                return False
                
        except Exception as e:
            logger.error("notification_publish_exception", camera=camera_name, error=str(e))
            return False
    
    def publish_image_metadata(
        self,
        camera_name: str,
        filename: str,
        path: str,
        zones: List[str],
        total_detections: int
    ) -> bool:
        """
        Publie les métadonnées d'une image.
        
        Args:
            camera_name: Nom de la caméra
            filename: Nom du fichier
            path: Chemin du fichier
            zones: Liste des zones détectées
            total_detections: Nombre total de détections
            
        Returns:
            True si publié avec succès
        """
        if not self.connected:
            logger.warning("mqtt_not_connected", action="publish_image_metadata")
            return False
        
        topic = self.config.mqtt.topics['image'].format(camera=camera_name)
        
        payload = {
            "camera": camera_name,
            "filename": filename,
            "path": path,
            "timestamp": datetime.now().isoformat(),
            "zones": zones,
            "total_detections": total_detections
        }
        
        try:
            result = self.client.publish(
                topic,
                json.dumps(payload),
                qos=self.config.mqtt.qos,
                retain=self.config.mqtt.retain
            )
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.debug("image_metadata_published", camera=camera_name, filename=filename)
                return True
            else:
                logger.error("image_metadata_publish_failed", camera=camera_name, rc=result.rc)
                return False
                
        except Exception as e:
            logger.error("image_metadata_publish_exception", camera=camera_name, error=str(e))
            return False
    
    def send_autodiscovery(self, camera_config: CameraConfig) -> bool:
        """
        Envoie les messages d'autodiscovery Home Assistant pour une caméra.
        
        Args:
            camera_config: Configuration de la caméra
            
        Returns:
            True si envoyé avec succès
        """
        if not self.config.homeassistant.autodiscovery:
            return True
        
        if not self.connected:
            logger.warning("mqtt_not_connected", action="autodiscovery")
            return False
        
        camera_name = camera_config.name
        
        # Éviter de renvoyer si déjà fait
        if camera_name in self.discovery_sent:
            return True
        
        success = True
        
        # Sensor: Détections totales
        success &= self._send_sensor_discovery(
            camera_name,
            "detections",
            "Détections totales",
            "mdi:cctv"
        )
        
        # Sensor: Fausses détections
        success &= self._send_sensor_discovery(
            camera_name,
            "false_detections",
            "Fausses alertes",
            "mdi:alert-circle"
        )
        
        # Sensors par zone
        for zone in camera_config.zones:
            if zone.entity_ha:
                # Total par zone
                success &= self._send_sensor_discovery(
                    camera_name,
                    f"zone_{zone.name}_detections",
                    f"Détections zone {zone.name}",
                    "mdi:map-marker"
                )
        
        if success:
            self.discovery_sent.add(camera_name)
            logger.info("autodiscovery_sent", camera=camera_name)
        
        return success
    
    def _send_sensor_discovery(
        self,
        camera_name: str,
        metric: str,
        friendly_name: str,
        icon: str
    ) -> bool:
        """
        Envoie un message de découverte pour un sensor.
        
        Args:
            camera_name: Nom de la caméra
            metric: Nom de la métrique
            friendly_name: Nom affiché dans HA
            icon: Icône MDI
            
        Returns:
            True si envoyé
        """
        # Topic de découverte HA
        discovery_topic = f"{self.config.homeassistant.discovery_prefix}/sensor/{self.config.app.name}/{camera_name}_{metric}/config"
        
        # Topic d'état
        state_topic = self.config.mqtt.topics['sensor'].format(camera=camera_name, metric=metric)
        
        # Payload de découverte
        payload = {
            "name": f"{camera_name.capitalize()} {friendly_name}",
            "unique_id": f"{self.config.app.name}_{camera_name}_{metric}",
            "state_topic": state_topic,
            "value_template": "{{ value_json.value }}",
            "unit_of_measurement": "count",
            "icon": icon,
            "device": {
                "identifiers": [f"{self.config.app.name}_{camera_name}"],
                "name": f"Caméra {camera_name.capitalize()}",
                "manufacturer": self.config.app.name,
                "model": "YOLO Detection",
                "sw_version": self.config.app.version
            }
        }
        
        try:
            result = self.client.publish(
                discovery_topic,
                json.dumps(payload),
                qos=1,
                retain=True  # Discovery toujours retained
            )
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.debug("discovery_sent", camera=camera_name, metric=metric)
                return True
            else:
                logger.error("discovery_failed", camera=camera_name, metric=metric, rc=result.rc)
                return False
                
        except Exception as e:
            logger.error("discovery_exception", camera=camera_name, error=str(e))
            return False