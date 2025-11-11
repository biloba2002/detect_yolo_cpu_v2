"""
Surveillance du répertoire d'entrée pour détecter les nouvelles images.
Utilise watchdog pour monitorer les ajouts de fichiers .jpg.
"""

import logging
import time
from pathlib import Path
from typing import Callable, Optional

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

logger = logging.getLogger(__name__)


class ImageFileHandler(FileSystemEventHandler):
    """Handler pour les événements de fichiers images."""

    def __init__(self, callback: Callable[[Path], None], extensions: tuple = (".jpg", ".jpeg")):
        """
        Initialise le handler.

        Args:
            callback: Fonction à appeler lors de la détection d'un nouveau fichier
            extensions: Tuple des extensions de fichiers à surveiller
        """
        super().__init__()
        self.callback = callback
        self.extensions = extensions
        self._processing = set()  # Éviter les doublons

    def on_created(self, event: FileSystemEvent) -> None:
        """
        Appelé quand un fichier est créé.

        Args:
            event: Événement watchdog
        """
        if event.is_directory:
            return

        file_path = Path(event.src_path)

        # Vérifier l'extension
        if file_path.suffix.lower() not in self.extensions:
            return

        # Éviter les doublons (watchdog peut trigger plusieurs fois)
        if file_path in self._processing:
            return

        self._processing.add(file_path)

        try:
            # Attendre que le fichier soit complètement écrit
            # (utile si le fichier est copié depuis un autre processus)
            self._wait_for_file_complete(file_path)

            logger.info(
                "Nouveau fichier détecté",
                extra={
                    "file": str(file_path),
                    "size": file_path.stat().st_size,
                },
            )

            # Appeler le callback pour traiter le fichier
            self.callback(file_path)

        except Exception as e:
            logger.error(
                "Erreur lors du traitement du fichier",
                extra={
                    "file": str(file_path),
                    "error": str(e),
                },
            )
        finally:
            self._processing.discard(file_path)

    def _wait_for_file_complete(self, file_path: Path, timeout: float = 5.0) -> None:
        """
        Attendre que le fichier soit complètement écrit.

        Args:
            file_path: Chemin du fichier
            timeout: Timeout en secondes

        Raises:
            TimeoutError: Si le fichier n'est pas stable après timeout
        """
        start_time = time.time()
        last_size = -1

        while time.time() - start_time < timeout:
            try:
                current_size = file_path.stat().st_size
                if current_size == last_size and current_size > 0:
                    # Taille stable, fichier probablement complet
                    time.sleep(0.1)  # Petite pause de sécurité
                    return
                last_size = current_size
                time.sleep(0.1)
            except FileNotFoundError:
                # Fichier pas encore accessible
                time.sleep(0.1)

        raise TimeoutError(f"Le fichier {file_path} n'est pas stable après {timeout}s")


class FileWatcher:
    """Surveillant de répertoire pour détecter les nouvelles images."""

    def __init__(
        self,
        watch_directory: Path,
        callback: Callable[[Path], None],
        extensions: tuple = (".jpg", ".jpeg"),
    ):
        """
        Initialise le watcher.

        Args:
            watch_directory: Répertoire à surveiller
            callback: Fonction à appeler pour chaque nouveau fichier
            extensions: Extensions de fichiers à surveiller
        """
        self.watch_directory = Path(watch_directory)
        self.callback = callback
        self.extensions = extensions
        self.observer: Optional[Observer] = None
        self._is_running = False

        # Créer le répertoire s'il n'existe pas
        self.watch_directory.mkdir(parents=True, exist_ok=True)

        logger.info(
            "FileWatcher initialisé",
            extra={
                "directory": str(self.watch_directory),
                "extensions": extensions,
            },
        )

    def start(self) -> None:
        """Démarre la surveillance du répertoire."""
        if self._is_running:
            logger.warning("FileWatcher déjà démarré")
            return

        self.observer = Observer()
        event_handler = ImageFileHandler(self.callback, self.extensions)

        self.observer.schedule(
            event_handler,
            str(self.watch_directory),
            recursive=False,
        )

        self.observer.start()
        self._is_running = True

        logger.info(
            "FileWatcher démarré",
            extra={"directory": str(self.watch_directory)},
        )

    def stop(self) -> None:
        """Arrête la surveillance du répertoire."""
        if not self._is_running or self.observer is None:
            logger.warning("FileWatcher déjà arrêté")
            return

        self.observer.stop()
        self.observer.join(timeout=5.0)
        self._is_running = False

        logger.info("FileWatcher arrêté")

    def is_running(self) -> bool:
        """
        Vérifie si le watcher est actif.

        Returns:
            True si le watcher est actif
        """
        return self._is_running

    def process_existing_files(self) -> None:
        """
        Traite les fichiers déjà présents dans le répertoire.
        Utile au démarrage de l'application.
        """
        logger.info(
            "Traitement des fichiers existants",
            extra={"directory": str(self.watch_directory)},
        )

        files_processed = 0
        for extension in self.extensions:
            for file_path in self.watch_directory.glob(f"*{extension}"):
                try:
                    logger.info(
                        "Traitement fichier existant",
                        extra={"file": str(file_path)},
                    )
                    self.callback(file_path)
                    files_processed += 1
                except Exception as e:
                    logger.error(
                        "Erreur traitement fichier existant",
                        extra={
                            "file": str(file_path),
                            "error": str(e),
                        },
                    )

        logger.info(
            "Traitement fichiers existants terminé",
            extra={"files_processed": files_processed},
        )