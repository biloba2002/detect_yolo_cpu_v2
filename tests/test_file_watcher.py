"""
Tests pour le module file_watcher.
"""

import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.file_watcher import FileWatcher


@pytest.fixture
def watch_dir(tmp_path):
    """Crée un répertoire temporaire pour la surveillance."""
    watch_path = tmp_path / "watch"
    watch_path.mkdir()
    return watch_path


@pytest.fixture
def callback_mock():
    """Mock de callback pour les tests."""
    return MagicMock()


def test_file_watcher_initialization(watch_dir, callback_mock):
    """Test initialisation du FileWatcher."""
    watcher = FileWatcher(watch_dir, callback_mock)

    assert watcher.watch_directory == watch_dir
    assert watcher.callback == callback_mock
    assert watcher.extensions == (".jpg", ".jpeg")
    assert not watcher.is_running()


def test_file_watcher_with_custom_extensions(watch_dir, callback_mock):
    """Test initialisation avec extensions personnalisées."""
    watcher = FileWatcher(watch_dir, callback_mock, extensions=(".png", ".gif"))

    assert watcher.extensions == (".png", ".gif")


def test_file_watcher_creates_directory(tmp_path, callback_mock):
    """Test que le watcher crée le répertoire s'il n'existe pas."""
    watch_path = tmp_path / "new_watch"
    assert not watch_path.exists()

    watcher = FileWatcher(watch_path, callback_mock)

    assert watch_path.exists()
    assert watch_path.is_dir()


def test_file_watcher_start_stop(watch_dir, callback_mock):
    """Test démarrage et arrêt du watcher."""
    watcher = FileWatcher(watch_dir, callback_mock)

    # Démarrer
    watcher.start()
    assert watcher.is_running()

    # Arrêter
    watcher.stop()
    assert not watcher.is_running()


def test_file_watcher_detects_new_jpg(watch_dir, callback_mock):
    """Test détection d'un nouveau fichier JPG."""
    watcher = FileWatcher(watch_dir, callback_mock)
    watcher.start()

    try:
        # Créer un fichier JPG
        test_file = watch_dir / "test_image.jpg"
        test_file.write_text("fake image content")

        # Attendre que watchdog détecte le fichier
        time.sleep(1.5)

        # Vérifier que le callback a été appelé
        assert callback_mock.call_count >= 1
        called_path = callback_mock.call_args[0][0]
        assert called_path.name == "test_image.jpg"

    finally:
        watcher.stop()


def test_file_watcher_detects_jpeg(watch_dir, callback_mock):
    """Test détection d'un fichier JPEG."""
    watcher = FileWatcher(watch_dir, callback_mock)
    watcher.start()

    try:
        # Créer un fichier JPEG
        test_file = watch_dir / "test_image.jpeg"
        test_file.write_text("fake image content")

        # Attendre détection
        time.sleep(1.5)

        # Vérifier callback
        assert callback_mock.call_count >= 1
        called_path = callback_mock.call_args[0][0]
        assert called_path.name == "test_image.jpeg"

    finally:
        watcher.stop()


def test_file_watcher_ignores_other_extensions(watch_dir, callback_mock):
    """Test que le watcher ignore les autres extensions."""
    watcher = FileWatcher(watch_dir, callback_mock)
    watcher.start()

    try:
        # Créer des fichiers non-JPG
        (watch_dir / "test.txt").write_text("text")
        (watch_dir / "test.png").write_text("png")
        (watch_dir / "test.pdf").write_text("pdf")

        # Attendre
        time.sleep(1.5)

        # Le callback ne devrait pas avoir été appelé
        assert callback_mock.call_count == 0

    finally:
        watcher.stop()


def test_file_watcher_ignores_directories(watch_dir, callback_mock):
    """Test que le watcher ignore les répertoires."""
    watcher = FileWatcher(watch_dir, callback_mock)
    watcher.start()

    try:
        # Créer un sous-répertoire
        subdir = watch_dir / "subdir"
        subdir.mkdir()

        # Attendre
        time.sleep(1.5)

        # Le callback ne devrait pas avoir été appelé
        assert callback_mock.call_count == 0

    finally:
        watcher.stop()


def test_file_watcher_process_existing_files(watch_dir, callback_mock):
    """Test traitement des fichiers existants."""
    # Créer des fichiers AVANT de démarrer le watcher
    file1 = watch_dir / "existing1.jpg"
    file2 = watch_dir / "existing2.jpeg"
    file3 = watch_dir / "existing3.txt"

    file1.write_text("image1")
    file2.write_text("image2")
    file3.write_text("text")

    # Créer le watcher
    watcher = FileWatcher(watch_dir, callback_mock)

    # Traiter les fichiers existants
    watcher.process_existing_files()

    # Le callback devrait avoir été appelé 2 fois (jpg + jpeg)
    assert callback_mock.call_count == 2

    # Vérifier que les bons fichiers ont été traités
    called_files = {call[0][0].name for call in callback_mock.call_args_list}
    assert "existing1.jpg" in called_files
    assert "existing2.jpeg" in called_files
    assert "existing3.txt" not in called_files


def test_file_watcher_callback_exception_handling(watch_dir, caplog):
    """Test que les exceptions dans le callback sont gérées."""
    # Callback qui lève une exception
    def failing_callback(path):
        raise ValueError("Test error")

    watcher = FileWatcher(watch_dir, failing_callback)
    watcher.start()

    try:
        # Créer un fichier
        test_file = watch_dir / "test.jpg"
        test_file.write_text("content")

        # Attendre
        time.sleep(1.5)

        # Vérifier que l'erreur a été loggée
        assert "Erreur lors du traitement du fichier" in caplog.text

    finally:
        watcher.stop()


def test_file_watcher_double_start(watch_dir, callback_mock, caplog):
    """Test qu'un double start ne pose pas de problème."""
    watcher = FileWatcher(watch_dir, callback_mock)

    watcher.start()
    assert watcher.is_running()

    # Deuxième start
    watcher.start()
    assert watcher.is_running()

    # Vérifier le warning
    assert "déjà démarré" in caplog.text

    watcher.stop()


def test_file_watcher_double_stop(watch_dir, callback_mock, caplog):
    """Test qu'un double stop ne pose pas de problème."""
    watcher = FileWatcher(watch_dir, callback_mock)

    watcher.start()
    watcher.stop()
    assert not watcher.is_running()

    # Deuxième stop
    watcher.stop()
    assert not watcher.is_running()

    # Vérifier le warning
    assert "déjà arrêté" in caplog.text


def test_file_watcher_multiple_files_rapid(watch_dir, callback_mock):
    """Test détection de plusieurs fichiers créés rapidement."""
    watcher = FileWatcher(watch_dir, callback_mock)
    watcher.start()

    try:
        # Créer plusieurs fichiers rapidement
        for i in range(5):
            test_file = watch_dir / f"test_{i}.jpg"
            test_file.write_text(f"content {i}")
            time.sleep(0.1)

        # Attendre que tous soient traités
        time.sleep(2)

        # Tous les fichiers devraient avoir été détectés
        assert callback_mock.call_count >= 5

    finally:
        watcher.stop()
