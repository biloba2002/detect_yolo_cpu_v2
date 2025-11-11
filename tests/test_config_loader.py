"""
Tests pour le chargeur de configuration.
"""

import pytest
from pathlib import Path
from pydantic import ValidationError
from src.config_loader import (
    Config,
    CameraConfig,
    ZoneConfig,
    extract_camera_name,
    load_config
)


def test_extract_camera_name_valid():
    """Test extraction nom caméra depuis filename valide."""
    assert extract_camera_name("reolink_2025-11-10_10-30-15.jpg") == "reolink"
    assert extract_camera_name("ptz_2025-11-10_14-22-05.jpg") == "ptz"
    assert extract_camera_name("camera1_image.jpg") == "camera1"


def test_extract_camera_name_no_underscore():
    """Test extraction sans underscore → generique."""
    assert extract_camera_name("image.jpg") == "image"


def test_extract_camera_name_empty():
    """Test extraction nom vide → generique."""
    assert extract_camera_name("_.jpg") == ""


def test_zone_config_valid_polygon():
    """Test création zone avec polygone valide."""
    zone = ZoneConfig(
        name="test_zone",
        polygon=[0.0, 0.0, 1.0, 0.0, 0.5, 1.0]  # Triangle
    )
    assert zone.name == "test_zone"
    assert len(zone.polygon) == 6


def test_zone_config_invalid_polygon_odd():
    """Test rejet polygone avec nombre impair de coordonnées."""
    with pytest.raises(ValidationError, match="at least 6 items"):
        ZoneConfig(
            name="bad_zone",
            polygon=[0.0, 0.0, 1.0]  # 3 coords (impair)
        )


def test_zone_config_invalid_polygon_too_few():
    """Test rejet polygone avec moins de 3 points."""
    with pytest.raises(ValidationError, match="at least 6 items"):
        ZoneConfig(
            name="bad_zone",
            polygon=[0.0, 0.0, 1.0, 0.0]  # 2 points seulement
        )


def test_zone_config_invalid_polygon_out_of_range():
    """Test rejet polygone avec coordonnées hors [0,1]."""
    with pytest.raises(ValueError, match="between 0 and 1"):
        ZoneConfig(
            name="bad_zone",
            polygon=[0.0, 0.0, 1.5, 0.0, 0.5, 1.0]  # 1.5 > 1
        )


def test_camera_config_defaults():
    """Test valeurs par défaut CameraConfig."""
    camera = CameraConfig(name="test_cam")
    assert camera.name == "test_cam"
    assert camera.detect == []
    assert camera.text_msg is False
    assert camera.show_object is True
    assert camera.zones == []


def test_camera_config_with_zones():
    """Test caméra avec zones."""
    camera = CameraConfig(
        name="cam1",
        detect=["person", "car"],
        zones=[
            ZoneConfig(name="zone1", polygon=[0.0, 0.0, 1.0, 0.0, 0.5, 1.0])
        ]
    )
    assert len(camera.zones) == 1
    assert camera.zones[0].name == "zone1"


def test_config_get_camera_existing():
    """Test récupération caméra existante."""
    config = Config(
        app={"name": "test", "version": "1.0"},
        directories={"input": "/in", "output": "/out"},
        logging={"level": "info", "format": "json"},
        mqtt={
            "broker": "localhost",
            "topics": {}
        },
        homeassistant={"autodiscovery": True},
        detection={"model": "yolov11n.pt", "confidence_threshold": 0.5},
        cameras=[
            CameraConfig(name="reolink"),
            CameraConfig(name="generique")
        ]
    )
    
    cam = config.get_camera_config("reolink")
    assert cam.name == "reolink"


def test_config_get_camera_fallback_generique():
    """Test fallback vers caméra générique si nom inconnu."""
    config = Config(
        app={"name": "test", "version": "1.0"},
        directories={"input": "/in", "output": "/out"},
        logging={"level": "info", "format": "json"},
        mqtt={
            "broker": "localhost",
            "topics": {}
        },
        homeassistant={"autodiscovery": True},
        detection={"model": "yolov11n.pt", "confidence_threshold": 0.5},
        cameras=[
            CameraConfig(name="reolink"),
            CameraConfig(name="generique")
        ]
    )
    
    cam = config.get_camera_config("unknown_camera")
    assert cam.name == "generique"


def test_config_no_generique_raises():
    """Test erreur si pas de caméra générique en fallback."""
    config = Config(
        app={"name": "test", "version": "1.0"},
        directories={"input": "/in", "output": "/out"},
        logging={"level": "info", "format": "json"},
        mqtt={
            "broker": "localhost",
            "topics": {}
        },
        homeassistant={"autodiscovery": True},
        detection={"model": "yolov11n.pt", "confidence_threshold": 0.5},
        cameras=[
            CameraConfig(name="reolink")
        ]
    )
    
    with pytest.raises(ValueError, match="generique"):
        config.get_camera_config("unknown")


def test_load_config_file_not_found():
    """Test erreur si fichier config inexistant."""
    with pytest.raises(FileNotFoundError):
        load_config("/nonexistent/config.yaml")