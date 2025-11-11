"""
Tests pour l'annotateur d'images.
"""

import pytest
import cv2
import numpy as np
from pathlib import Path
from src.image_annotator import ImageAnnotator
from src.zone_manager import ZoneManager
from src.config_loader import CameraConfig, ZoneConfig


@pytest.fixture
def test_image_path(tmp_path):
    """Crée une image de test temporaire."""
    img = np.zeros((1000, 1000, 3), dtype=np.uint8)
    img[:] = (240, 240, 240)  # Fond gris
    
    image_path = tmp_path / "test_image.jpg"
    cv2.imwrite(str(image_path), img)
    
    return str(image_path)


@pytest.fixture
def camera_config_with_zones():
    """Config caméra avec zones."""
    return CameraConfig(
        name="test_cam",
        detect=["person", "car"],
        show_object=True,
        zones=[
            ZoneConfig(
                name="zone1",
                polygon=[0.0, 0.0, 1.0, 0.0, 1.0, 0.5, 0.0, 0.5],
                show_zone=True,
                show_object=True
            ),
            ZoneConfig(
                name="zone2",
                polygon=[0.0, 0.5, 1.0, 0.5, 1.0, 1.0, 0.0, 1.0],
                show_zone=True,
                show_object=True
            )
        ]
    )


@pytest.fixture
def sample_detections():
    """Détections de test."""
    return [
        {
            'class': 'person',
            'confidence': 0.85,
            'bbox': (100, 100, 300, 400),
            'is_false': False,
            'zones': ['zone1']
        },
        {
            'class': 'car',
            'confidence': 0.45,
            'bbox': (500, 600, 700, 800),
            'is_false': True,
            'zones': ['zone2']
        }
    ]


def test_annotator_init(camera_config_with_zones):
    """Test initialisation de l'annotateur."""
    annotator = ImageAnnotator(camera_config_with_zones)
    
    assert annotator.camera_config == camera_config_with_zones
    assert annotator.zone_manager is None


def test_annotate_composite_success(
    test_image_path,
    camera_config_with_zones,
    sample_detections,
    tmp_path
):
    """Test création image composite."""
    annotator = ImageAnnotator(camera_config_with_zones)
    output_path = tmp_path / "output_composite.jpg"
    
    # Créer zone manager
    zone_manager = ZoneManager(camera_config_with_zones.zones, 1000, 1000)
    
    success = annotator.annotate_composite(
        test_image_path,
        str(output_path),
        sample_detections,
        zone_manager
    )
    
    assert success is True
    assert output_path.exists()
    
    # Vérifier que l'image est lisible
    img = cv2.imread(str(output_path))
    assert img is not None
    assert img.shape == (1000, 1000, 3)


def test_annotate_composite_image_not_found(camera_config_with_zones, tmp_path):
    """Test échec si image source inexistante."""
    annotator = ImageAnnotator(camera_config_with_zones)
    output_path = tmp_path / "output.jpg"
    
    success = annotator.annotate_composite(
        "/nonexistent/image.jpg",
        str(output_path),
        []
    )
    
    assert success is False


def test_annotate_zone_success(
    test_image_path,
    camera_config_with_zones,
    sample_detections,
    tmp_path
):
    """Test création image pour une zone."""
    annotator = ImageAnnotator(camera_config_with_zones)
    output_path = tmp_path / "output_zone.jpg"
    
    zone_manager = ZoneManager(camera_config_with_zones.zones, 1000, 1000)
    
    success = annotator.annotate_zone(
        test_image_path,
        str(output_path),
        "zone1",
        sample_detections,
        zone_manager
    )
    
    assert success is True
    assert output_path.exists()


def test_annotate_zone_not_found(
    test_image_path,
    camera_config_with_zones,
    sample_detections,
    tmp_path
):
    """Test échec si zone inexistante."""
    annotator = ImageAnnotator(camera_config_with_zones)
    output_path = tmp_path / "output.jpg"
    
    zone_manager = ZoneManager(camera_config_with_zones.zones, 1000, 1000)
    
    success = annotator.annotate_zone(
        test_image_path,
        str(output_path),
        "zone_inexistante",
        sample_detections,
        zone_manager
    )
    
    assert success is False


def test_draw_detection(test_image_path, camera_config_with_zones):
    """Test dessin d'une détection."""
    annotator = ImageAnnotator(camera_config_with_zones)
    
    img = cv2.imread(test_image_path)
    detection = {
        'class': 'person',
        'confidence': 0.95,
        'bbox': (100, 100, 300, 400),
        'is_false': False
    }
    
    # Dessiner (ne devrait pas crasher)
    annotator._draw_detection(img, detection)
    
    # L'image devrait être modifiée (pas tout gris)
    assert not np.all(img == 240)


def test_draw_false_detection(test_image_path, camera_config_with_zones):
    """Test dessin fausse détection."""
    annotator = ImageAnnotator(camera_config_with_zones)
    
    img = cv2.imread(test_image_path)
    detection = {
        'class': 'car',
        'confidence': 0.45,
        'bbox': (500, 500, 700, 700),
        'is_false': True
    }
    
    annotator._draw_detection(img, detection)
    assert not np.all(img == 240)


def test_annotate_without_zones(test_image_path, tmp_path):
    """Test annotation caméra sans zones."""
    camera_config = CameraConfig(
        name="simple_cam",
        detect=["person"],
        show_object=True,
        zones=[]
    )
    
    annotator = ImageAnnotator(camera_config)
    output_path = tmp_path / "output_no_zones.jpg"
    
    detections = [{
        'class': 'person',
        'confidence': 0.85,
        'bbox': (100, 100, 300, 400),
        'is_false': False,
        'zones': []
    }]
    
    success = annotator.annotate_composite(
        test_image_path,
        str(output_path),
        detections
    )
    
    assert success is True