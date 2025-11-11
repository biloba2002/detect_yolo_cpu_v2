"""
Tests pour les fonctions utilitaires.
"""

import pytest
import os
from pathlib import Path
from src.utils import (
    handle_processed_image, 
    ensure_directory_exists, 
    list_images,
    get_output_path,
    save_original_image
)


def test_save_original_image(test_image, tmp_path):
    """Test sauvegarde de l'image originale."""
    output_dir = str(tmp_path)
    
    success = save_original_image(test_image, output_dir, "reolink", organize_by_camera=True)
    
    assert success is True
    
    # Vérifier que l'original existe
    original_path = os.path.join(output_dir, "original", "reolink", os.path.basename(test_image))
    assert os.path.exists(original_path)
    
    # Vérifier que l'original a le même contenu
    with open(test_image, 'r') as f1, open(original_path, 'r') as f2:
        assert f1.read() == f2.read()


def test_save_original_image_duplicate(test_image, tmp_path):
    """Test sauvegarde avec doublon existant."""
    output_dir = str(tmp_path)
    filename = os.path.basename(test_image)
    
    # Créer un fichier existant
    original_dir = os.path.join(output_dir, "original", "reolink")
    os.makedirs(original_dir, exist_ok=True)
    existing = os.path.join(original_dir, filename)
    Path(existing).write_text("existing content")
    
    # Sauvegarder
    success = save_original_image(test_image, output_dir, "reolink", organize_by_camera=True)
    
    assert success is True
    
    # Vérifier que l'original existe intact
    assert os.path.exists(existing)
    
    # Vérifier que le nouveau a un suffixe
    base, ext = os.path.splitext(filename)
    renamed = os.path.join(original_dir, f"{base}_1{ext}")
    assert os.path.exists(renamed)


def test_save_original_image_source_not_found(tmp_path):
    """Test avec image source inexistante."""
    success = save_original_image("/nonexistent/image.jpg", str(tmp_path), "test")
    
    assert success is False


def test_get_output_path_full_organization(tmp_path):
    """Test chemin avec result ET camera."""
    output_dir = str(tmp_path)
    
    # Avec détections
    path = get_output_path(
        output_dir, 
        "test.jpg", 
        "reolink", 
        has_valid_detections=True,
        organize_by_result=True,
        organize_by_camera=True
    )
    
    assert path == os.path.join(output_dir, "true", "reolink", "test.jpg")
    assert os.path.exists(os.path.dirname(path))  # Dossier créé
    
    # Sans détections
    path_false = get_output_path(
        output_dir,
        "test2.jpg",
        "ptz",
        has_valid_detections=False,
        organize_by_result=True,
        organize_by_camera=True
    )
    
    assert path_false == os.path.join(output_dir, "false", "ptz", "test2.jpg")


def test_get_output_path_result_only(tmp_path):
    """Test chemin avec result seulement."""
    output_dir = str(tmp_path)
    
    path = get_output_path(
        output_dir,
        "test.jpg",
        "reolink",
        has_valid_detections=True,
        organize_by_result=True,
        organize_by_camera=False
    )
    
    assert path == os.path.join(output_dir, "true", "test.jpg")


def test_get_output_path_camera_only(tmp_path):
    """Test chemin avec camera seulement."""
    output_dir = str(tmp_path)
    
    path = get_output_path(
        output_dir,
        "test.jpg",
        "reolink",
        has_valid_detections=True,
        organize_by_result=False,
        organize_by_camera=True
    )
    
    assert path == os.path.join(output_dir, "reolink", "test.jpg")


def test_get_output_path_flat(tmp_path):
    """Test chemin plat (pas d'organisation)."""
    output_dir = str(tmp_path)
    
    path = get_output_path(
        output_dir,
        "test.jpg",
        "reolink",
        has_valid_detections=True,
        organize_by_result=False,
        organize_by_camera=False
    )
    
    assert path == os.path.join(output_dir, "test.jpg")


@pytest.fixture
def test_image(tmp_path):
    """Crée une image de test temporaire."""
    image_path = tmp_path / "test_image.jpg"
    image_path.write_text("fake image content")
    return str(image_path)


@pytest.fixture
def output_dir(tmp_path):
    """Crée un dossier de sortie temporaire."""
    output = tmp_path / "output"
    output.mkdir()
    return str(output)


def test_handle_processed_image_none(test_image):
    """Test action 'none' - fichier reste en place."""
    assert os.path.exists(test_image)
    
    success = handle_processed_image(test_image, "none")
    
    assert success is True
    assert os.path.exists(test_image)  # Fichier toujours là


def test_handle_processed_image_erase(test_image):
    """Test action 'erase' - fichier supprimé."""
    assert os.path.exists(test_image)
    
    success = handle_processed_image(test_image, "erase")
    
    assert success is True
    assert not os.path.exists(test_image)  # Fichier supprimé


def test_handle_processed_image_move(test_image, output_dir):
    """Test action 'move' - fichier déplacé."""
    filename = os.path.basename(test_image)
    dest_path = os.path.join(output_dir, filename)
    
    assert os.path.exists(test_image)
    assert not os.path.exists(dest_path)
    
    success = handle_processed_image(test_image, "move", output_dir)
    
    assert success is True
    assert not os.path.exists(test_image)  # Fichier source supprimé
    assert os.path.exists(dest_path)  # Fichier dans output


def test_handle_processed_image_move_no_output_dir(test_image):
    """Test action 'move' sans output_dir → ValueError."""
    with pytest.raises(ValueError, match="output_dir required"):
        handle_processed_image(test_image, "move")


def test_handle_processed_image_move_duplicate(test_image, output_dir):
    """Test move avec fichier existant → renommage automatique."""
    filename = os.path.basename(test_image)
    
    # Créer un fichier existant dans output
    existing = os.path.join(output_dir, filename)
    Path(existing).write_text("existing file")
    
    success = handle_processed_image(test_image, "move", output_dir)
    
    assert success is True
    assert os.path.exists(existing)  # Fichier original intact
    
    # Nouveau fichier avec suffixe _1
    base, ext = os.path.splitext(filename)
    renamed = os.path.join(output_dir, f"{base}_1{ext}")
    assert os.path.exists(renamed)


def test_handle_processed_image_invalid_action(test_image):
    """Test action invalide."""
    success = handle_processed_image(test_image, "invalid_action")
    
    assert success is False
    assert os.path.exists(test_image)  # Fichier intact


def test_handle_processed_image_source_not_found(tmp_path):
    """Test avec fichier source inexistant."""
    fake_path = str(tmp_path / "nonexistent.jpg")
    
    success = handle_processed_image(fake_path, "move", str(tmp_path))
    
    assert success is False


def test_ensure_directory_exists_new(tmp_path):
    """Test création nouveau répertoire."""
    new_dir = tmp_path / "new_directory"
    assert not new_dir.exists()
    
    success = ensure_directory_exists(str(new_dir))
    
    assert success is True
    assert new_dir.exists()


def test_ensure_directory_exists_already_exists(tmp_path):
    """Test avec répertoire existant."""
    existing_dir = tmp_path / "existing"
    existing_dir.mkdir()
    
    success = ensure_directory_exists(str(existing_dir))
    
    assert success is True
    assert existing_dir.exists()


def test_list_images_empty_directory(tmp_path):
    """Test liste images dans dossier vide."""
    images = list_images(str(tmp_path))
    
    assert images == []


def test_list_images_with_images(tmp_path):
    """Test liste images avec plusieurs fichiers."""
    # Créer des images
    (tmp_path / "image1.jpg").write_text("img1")
    (tmp_path / "image2.jpeg").write_text("img2")
    (tmp_path / "image3.png").write_text("img3")
    (tmp_path / "not_an_image.txt").write_text("text")
    
    images = list_images(str(tmp_path))
    
    assert len(images) == 3
    assert all(img.endswith(('.jpg', '.jpeg', '.png')) for img in images)
    assert sorted(images) == images  # Vérifie le tri


def test_list_images_directory_not_found(tmp_path):
    """Test liste images dans dossier inexistant."""
    fake_dir = tmp_path / "nonexistent"
    
    images = list_images(str(fake_dir))
    
    assert images == []


def test_list_images_custom_extensions(tmp_path):
    """Test liste images avec extensions personnalisées."""
    (tmp_path / "doc.pdf").write_text("pdf")
    (tmp_path / "image.jpg").write_text("img")
    
    images = list_images(str(tmp_path), extensions=('.pdf',))
    
    assert len(images) == 1
    assert images[0].endswith('.pdf')