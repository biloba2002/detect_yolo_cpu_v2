"""
Tests pour le publisher MQTT.
Note: Ces tests nécessitent un broker MQTT actif pour les tests d'intégration.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from src.mqtt_publisher import MQTTPublisher
from src.config_loader import Config, CameraConfig, MQTTConfig, ZoneConfig


@pytest.fixture
def mqtt_config():
    """Config MQTT de test."""
    return MQTTConfig(
        broker="localhost",
        port=1883,
        qos=1,
        retain=False,
        username="",
        password="",
        topics={
            "sensor": "test/sensor/{camera}/{metric}",
            "notify": "test/notify/{camera}/{zone}",
            "image": "test/image/{camera}"
        }
    )


@pytest.fixture
def test_config(mqtt_config):
    """Config complète de test."""
    return Config(
        app={"name": "test_app", "version": "1.0.0"},
        directories={"input": "in", "output": "out"},
        processing={"input_action": "move", "output_structure": {}},
        logging={"level": "info", "format": "json"},
        mqtt=mqtt_config,
        homeassistant={"autodiscovery": True, "discovery_prefix": "homeassistant"},
        detection={"model": "yolo11n.pt", "confidence_threshold": 0.5},
        cameras=[
            CameraConfig(name="test_cam", detect=["person"], zones=[])
        ]
    )


@pytest.fixture
def camera_config():
    """Config caméra de test."""
    return CameraConfig(
        name="test_cam",
        detect=["person", "car"],
        text_msg=True,
        audio_msg=False,
        show_object=True,
        entity_ha=True,
        zones=[
            ZoneConfig(
                name="zone1",
                polygon=[0.0, 0.0, 1.0, 0.0, 1.0, 1.0, 0.0, 1.0],
                entity_ha=True
            )
        ]
    )


def test_mqtt_publisher_init(test_config):
    """Test initialisation du publisher."""
    with patch('paho.mqtt.client.Client'):
        publisher = MQTTPublisher(test_config)
        
        assert publisher.config == test_config
        assert publisher.connected is False
        assert len(publisher.discovery_sent) == 0


def test_mqtt_connect_success(test_config):
    """Test connexion MQTT réussie."""
    with patch('paho.mqtt.client.Client') as mock_client:
        mock_instance = mock_client.return_value
        
        publisher = MQTTPublisher(test_config)
        
        # Simuler connexion réussie
        publisher.connected = True
        
        result = publisher.connect()
        
        mock_instance.connect.assert_called_once()
        mock_instance.loop_start.assert_called_once()


def test_mqtt_connect_with_credentials(test_config):
    """Test connexion avec credentials."""
    test_config.mqtt.username = "user"
    test_config.mqtt.password = "pass"
    
    with patch('paho.mqtt.client.Client') as mock_client:
        mock_instance = mock_client.return_value
        
        publisher = MQTTPublisher(test_config)
        
        mock_instance.username_pw_set.assert_called_once_with("user", "pass")


def test_publish_sensor_success(test_config):
    """Test publication sensor réussie."""
    with patch('paho.mqtt.client.Client') as mock_client:
        mock_instance = mock_client.return_value
        mock_result = Mock()
        mock_result.rc = 0  # MQTT_ERR_SUCCESS
        mock_instance.publish.return_value = mock_result
        
        publisher = MQTTPublisher(test_config)
        publisher.connected = True
        
        result = publisher.publish_sensor("test_cam", "detections", 5)
        
        assert result is True
        mock_instance.publish.assert_called_once()
        
        # Vérifier le payload
        call_args = mock_instance.publish.call_args
        topic = call_args[0][0]
        payload = json.loads(call_args[0][1])
        
        assert topic == "test/sensor/test_cam/detections"
        assert payload["value"] == 5
        assert payload["unit"] == "count"
        assert "timestamp" in payload


def test_publish_sensor_not_connected(test_config):
    """Test publication sensor sans connexion."""
    with patch('paho.mqtt.client.Client'):
        publisher = MQTTPublisher(test_config)
        publisher.connected = False
        
        result = publisher.publish_sensor("test_cam", "detections", 5)
        
        assert result is False


def test_publish_notification_with_zone(test_config):
    """Test publication notification avec zone."""
    with patch('paho.mqtt.client.Client') as mock_client:
        mock_instance = mock_client.return_value
        mock_result = Mock()
        mock_result.rc = 0
        mock_instance.publish.return_value = mock_result
        
        publisher = MQTTPublisher(test_config)
        publisher.connected = True
        
        result = publisher.publish_notification(
            "test_cam",
            "zone1",
            "2 person detected",
            audio=True,
            detections={"person": 2}
        )
        
        assert result is True
        
        call_args = mock_instance.publish.call_args
        payload = json.loads(call_args[0][1])
        
        assert payload["message"] == "2 person detected"
        assert payload["audio"] is True
        assert payload["zone"] == "zone1"
        assert payload["detections"] == {"person": 2}


def test_publish_notification_without_zone(test_config):
    """Test publication notification sans zone."""
    with patch('paho.mqtt.client.Client') as mock_client:
        mock_instance = mock_client.return_value
        mock_result = Mock()
        mock_result.rc = 0
        mock_instance.publish.return_value = mock_result
        
        publisher = MQTTPublisher(test_config)
        publisher.connected = True
        
        result = publisher.publish_notification(
            "test_cam",
            None,
            "Camera activated"
        )
        
        assert result is True
        
        call_args = mock_instance.publish.call_args
        payload = json.loads(call_args[0][1])
        
        assert "zone" not in payload


def test_publish_image_metadata(test_config):
    """Test publication métadonnées image."""
    with patch('paho.mqtt.client.Client') as mock_client:
        mock_instance = mock_client.return_value
        mock_result = Mock()
        mock_result.rc = 0
        mock_instance.publish.return_value = mock_result
        
        publisher = MQTTPublisher(test_config)
        publisher.connected = True
        
        result = publisher.publish_image_metadata(
            "test_cam",
            "test.jpg",
            "/path/to/test.jpg",
            ["zone1"],
            3
        )
        
        assert result is True
        
        call_args = mock_instance.publish.call_args
        topic = call_args[0][0]
        payload = json.loads(call_args[0][1])
        
        assert topic == "test/image/test_cam"
        assert payload["filename"] == "test.jpg"
        assert payload["zones"] == ["zone1"]
        assert payload["total_detections"] == 3


def test_send_autodiscovery(test_config, camera_config):
    """Test envoi autodiscovery HA."""
    with patch('paho.mqtt.client.Client') as mock_client:
        mock_instance = mock_client.return_value
        mock_result = Mock()
        mock_result.rc = 0
        mock_instance.publish.return_value = mock_result
        
        publisher = MQTTPublisher(test_config)
        publisher.connected = True
        
        result = publisher.send_autodiscovery(camera_config)
        
        assert result is True
        assert "test_cam" in publisher.discovery_sent
        
        # Vérifier que plusieurs topics de discovery ont été publiés
        assert mock_instance.publish.call_count >= 2  # detections + false_detections


def test_send_autodiscovery_disabled(test_config, camera_config):
    """Test autodiscovery désactivé."""
    test_config.homeassistant.autodiscovery = False
    
    with patch('paho.mqtt.client.Client'):
        publisher = MQTTPublisher(test_config)
        
        result = publisher.send_autodiscovery(camera_config)
        
        assert result is True
        assert len(publisher.discovery_sent) == 0


def test_send_autodiscovery_only_once(test_config, camera_config):
    """Test autodiscovery envoyé une seule fois."""
    with patch('paho.mqtt.client.Client') as mock_client:
        mock_instance = mock_client.return_value
        mock_result = Mock()
        mock_result.rc = 0
        mock_instance.publish.return_value = mock_result
        
        publisher = MQTTPublisher(test_config)
        publisher.connected = True
        
        # Premier envoi
        publisher.send_autodiscovery(camera_config)
        first_call_count = mock_instance.publish.call_count
        
        # Deuxième envoi (devrait être ignoré)
        publisher.send_autodiscovery(camera_config)
        second_call_count = mock_instance.publish.call_count
        
        assert first_call_count == second_call_count


def test_disconnect(test_config):
    """Test déconnexion MQTT."""
    with patch('paho.mqtt.client.Client') as mock_client:
        mock_instance = mock_client.return_value
        
        publisher = MQTTPublisher(test_config)
        publisher.disconnect()
        
        mock_instance.loop_stop.assert_called_once()
        mock_instance.disconnect.assert_called_once()