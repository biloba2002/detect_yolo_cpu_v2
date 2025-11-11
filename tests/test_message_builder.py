"""
Tests pour le constructeur de messages.
"""

import pytest
from src.message_builder import MessageBuilder
from src.config_loader import CameraConfig, ZoneConfig


@pytest.fixture
def message_builder():
    """Fixture MessageBuilder."""
    return MessageBuilder()


@pytest.fixture
def camera_config():
    """Config caméra simple."""
    return CameraConfig(
        name="test_cam",
        detect=["person", "car"],
        text_msg=True,
        audio_msg=True,
        show_object=True
    )


@pytest.fixture
def zone_config():
    """Config zone avec template."""
    return ZoneConfig(
        name="entrance",
        polygon=[0.0, 0.0, 1.0, 0.0, 1.0, 1.0, 0.0, 1.0],
        text_msg=True,
        audio_msg=False,
        msg_template="{count_person} personne(s) et {count_car} voiture(s) détecté(es)"
    )


def test_build_camera_message_with_detections(message_builder, camera_config):
    """Test construction message caméra avec détections."""
    counters = {
        'total': 5,
        'false': 1,
        'by_class': {'person': 3, 'car': 1}
    }
    
    result = message_builder.build_camera_message(camera_config, counters)
    
    assert result['type'] == 'text'
    assert result['audio'] is True
    assert result['camera'] == 'test_cam'
    assert 'person' in result['message']
    assert 'car' in result['message']
    assert result['detections'] == {'person': 3, 'car': 1}


def test_build_camera_message_no_valid_detections(message_builder, camera_config):
    """Test message caméra sans détections valides."""
    counters = {
        'total': 2,
        'false': 2,
        'by_class': {}
    }
    
    result = message_builder.build_camera_message(camera_config, counters)
    
    assert result == {}


def test_build_camera_message_text_disabled(message_builder):
    """Test pas de message si text_msg désactivé."""
    camera_config = CameraConfig(
        name="test_cam",
        detect=["person"],
        text_msg=False,
        audio_msg=False,
        show_object=True
    )
    
    counters = {'total': 3, 'false': 0, 'by_class': {'person': 3}}
    
    result = message_builder.build_camera_message(camera_config, counters)
    
    assert result == {}


def test_build_zone_message_with_template(message_builder, zone_config):
    """Test message zone avec template."""
    detections = [
        {'class': 'person', 'is_false': False, 'zones': ['entrance']},
        {'class': 'person', 'is_false': False, 'zones': ['entrance']},
        {'class': 'car', 'is_false': False, 'zones': ['entrance']},
    ]
    
    result = message_builder.build_zone_message(zone_config, "test_cam", detections)
    
    assert result['type'] == 'text'
    assert result['audio'] is False
    assert result['zone'] == 'entrance'
    assert result['camera'] == 'test_cam'
    assert '2 personne(s)' in result['message']
    assert '1 voiture(s)' in result['message']


def test_build_zone_message_without_template(message_builder):
    """Test message zone sans template."""
    zone_config = ZoneConfig(
        name="parking",
        polygon=[0.0, 0.0, 1.0, 0.0, 1.0, 1.0, 0.0, 1.0],
        text_msg=True,
        audio_msg=True,
        msg_template=""
    )
    
    detections = [
        {'class': 'car', 'is_false': False, 'zones': ['parking']},
        {'class': 'car', 'is_false': False, 'zones': ['parking']},
    ]
    
    result = message_builder.build_zone_message(zone_config, "cam1", detections)
    
    assert result['message'] == '2 car détecté(s) dans parking'


def test_build_zone_message_filters_false_detections(message_builder, zone_config):
    """Test filtrage des fausses détections."""
    detections = [
        {'class': 'person', 'is_false': False, 'zones': ['entrance']},
        {'class': 'person', 'is_false': True, 'zones': ['entrance']},  # Fausse
        {'class': 'car', 'is_false': False, 'zones': ['entrance']},
    ]
    
    result = message_builder.build_zone_message(zone_config, "cam1", detections)
    
    # Seulement 1 personne (la fausse est exclue)
    assert '1 personne(s)' in result['message']


def test_build_zone_message_no_valid_detections(message_builder, zone_config):
    """Test message zone sans détections valides."""
    detections = [
        {'class': 'person', 'is_false': True, 'zones': ['entrance']},
    ]
    
    result = message_builder.build_zone_message(zone_config, "cam1", detections)
    
    assert result == {}


def test_build_zone_message_text_disabled(message_builder):
    """Test pas de message si text_msg désactivé."""
    zone_config = ZoneConfig(
        name="test_zone",
        polygon=[0.0, 0.0, 1.0, 0.0, 1.0, 1.0, 0.0, 1.0],
        text_msg=False
    )
    
    detections = [{'class': 'person', 'is_false': False, 'zones': ['test_zone']}]
    
    result = message_builder.build_zone_message(zone_config, "cam1", detections)
    
    assert result == {}


def test_apply_template(message_builder):
    """Test application de template."""
    template = "{count_person} personne(s) et {count_car} voiture(s)"
    class_counts = {'person': 2, 'car': 3}
    
    result = message_builder._apply_template(template, class_counts)
    
    assert result == "2 personne(s) et 3 voiture(s)"


def test_apply_template_missing_class(message_builder):
    """Test template avec classe manquante."""
    template = "{count_person} personne(s) et {count_dog} chien(s)"
    class_counts = {'person': 2}  # Pas de dog
    
    result = message_builder._apply_template(template, class_counts)
    
    assert result == "2 personne(s) et 0 chien(s)"


def test_build_summary_message(message_builder):
    """Test message récapitulatif."""
    counters = {
        'total': 10,
        'false': 2,
        'by_class': {'person': 5, 'car': 3}
    }
    
    zones_messages = [
        {'zone': 'zone1', 'message': '3 person in zone1'},
        {'zone': 'zone2', 'message': '2 car in zone2'}
    ]
    
    result = message_builder.build_summary_message("test_cam", counters, zones_messages)
    
    assert '📷 test_cam' in result
    assert 'Détections valides: 8' in result
    assert 'Fausses détections: 2' in result
    assert 'person: 5' in result
    assert 'car: 3' in result
    assert 'zone1' in result
    assert 'zone2' in result