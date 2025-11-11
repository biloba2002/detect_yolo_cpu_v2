"""
Tests pour le gestionnaire de zones.
"""

import pytest
from src.zone_manager import ZoneManager
from src.config_loader import ZoneConfig


@pytest.fixture
def sample_zones():
    """Fixture avec des zones de test."""
    return [
        ZoneConfig(
            name="zone1",
            polygon=[0.0, 0.0, 1.0, 0.0, 1.0, 0.5, 0.0, 0.5]  # Rectangle haut
        ),
        ZoneConfig(
            name="zone2",
            polygon=[0.0, 0.5, 1.0, 0.5, 1.0, 1.0, 0.0, 1.0]  # Rectangle bas
        )
    ]


def test_zone_manager_init(sample_zones):
    """Test initialisation du gestionnaire de zones."""
    zm = ZoneManager(sample_zones, image_width=1000, image_height=1000)
    
    assert len(zm.polygons) == 2
    assert "zone1" in zm.polygons
    assert "zone2" in zm.polygons


def test_normalize_to_pixels(sample_zones):
    """Test conversion coordonnées normalisées vers pixels."""
    zm = ZoneManager(sample_zones, image_width=1000, image_height=800)
    
    # Coordonnées normalisées [0, 0, 1, 1] → pixels
    pixels = zm._normalize_to_pixels([0.0, 0.0, 1.0, 1.0])
    
    assert pixels == [(0.0, 0.0), (1000.0, 800.0)]


def test_point_in_zone(sample_zones):
    """Test vérification point dans zone."""
    zm = ZoneManager(sample_zones, image_width=1000, image_height=1000)
    
    # Point au centre de zone1 (rectangle haut)
    assert zm.point_in_zone(500, 250, "zone1") is True
    
    # Point au centre de zone2 (rectangle bas)
    assert zm.point_in_zone(500, 750, "zone2") is True
    
    # Point hors zones
    assert zm.point_in_zone(-10, -10, "zone1") is False


def test_point_in_zone_not_found(sample_zones):
    """Test point dans zone inexistante."""
    zm = ZoneManager(sample_zones, image_width=1000, image_height=1000)
    
    # Zone qui n'existe pas
    assert zm.point_in_zone(500, 500, "zone_inexistante") is False


def test_bbox_center_in_zone(sample_zones):
    """Test vérification centre bbox dans zone."""
    zm = ZoneManager(sample_zones, image_width=1000, image_height=1000)
    
    # Bbox dont le centre est dans zone1
    bbox = (400, 100, 600, 300)  # Centre: (500, 200) → zone1
    assert zm.bbox_center_in_zone(bbox, "zone1") is True
    assert zm.bbox_center_in_zone(bbox, "zone2") is False


def test_filter_detections_by_zone(sample_zones):
    """Test filtrage détections par zone."""
    zm = ZoneManager(sample_zones, image_width=1000, image_height=1000)
    
    detections = [
        {'class': 'person', 'bbox': (400, 100, 600, 300)},  # Centre dans zone1
        {'class': 'car', 'bbox': (400, 600, 600, 800)},     # Centre dans zone2
        {'class': 'dog', 'bbox': (0, 0, 50, 50)},           # Centre dans zone1
    ]
    
    zone1_detections = zm.filter_detections_by_zone(detections, "zone1")
    zone2_detections = zm.filter_detections_by_zone(detections, "zone2")
    
    assert len(zone1_detections) == 2
    assert len(zone2_detections) == 1
    assert zone2_detections[0]['class'] == 'car'


def test_filter_detections_zone_not_found(sample_zones):
    """Test filtrage avec zone inexistante."""
    zm = ZoneManager(sample_zones, image_width=1000, image_height=1000)
    
    detections = [{'class': 'person', 'bbox': (400, 100, 600, 300)}]
    filtered = zm.filter_detections_by_zone(detections, "zone_inexistante")
    
    assert filtered == []


def test_get_zone_config(sample_zones):
    """Test récupération config zone."""
    zm = ZoneManager(sample_zones, image_width=1000, image_height=1000)
    
    config = zm.get_zone_config("zone1")
    assert config.name == "zone1"


def test_get_zone_config_not_found(sample_zones):
    """Test récupération config zone inexistante."""
    zm = ZoneManager(sample_zones, image_width=1000, image_height=1000)
    
    with pytest.raises(ValueError, match="not found"):
        zm.get_zone_config("zone_inexistante")


def test_get_polygon_pixel_coords(sample_zones):
    """Test récupération coordonnées polygone en pixels."""
    zm = ZoneManager(sample_zones, image_width=1000, image_height=1000)
    
    coords = zm.get_polygon_pixel_coords("zone1")
    
    assert len(coords) > 0
    assert all(isinstance(x, int) and isinstance(y, int) for x, y in coords)


def test_get_polygon_pixel_coords_not_found(sample_zones):
    """Test coordonnées polygone zone inexistante."""
    zm = ZoneManager(sample_zones, image_width=1000, image_height=1000)
    
    coords = zm.get_polygon_pixel_coords("zone_inexistante")
    assert coords == []


def test_empty_zones():
    """Test gestionnaire sans zones."""
    zm = ZoneManager([], image_width=1000, image_height=1000)
    
    assert len(zm.polygons) == 0
    assert zm.filter_detections_by_zone([], "any") == []