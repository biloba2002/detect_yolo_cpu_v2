"""
Fonctions utilitaires pour la gestion des fichiers et autres helpers.
"""

import os
import shutil
from pathlib import Path
from typing import Optional
from src.logger import get_logger

logger = get_logger(__name__)


# ------------------------------------------------------------------------
# Helpers internes
# ------------------------------------------------------------------------

def _unique_path(dest: Path) -> Path:
    """Retourne un chemin non-collisant en suffixant _N si besoin."""
    if not dest.exists():
        return dest
    stem, suf = dest.stem, dest.suffix
    i = 1
    while True:
        cand = dest.with_name(f"{stem}_{i}{suf}")
        if not cand.exists():
            return cand
        i += 1


# ------------------------------------------------------------------------
# Sauvegarde/copie de l'original (copie, pas déplacement)
# ------------------------------------------------------------------------

def save_original_image(
    source_path: str,
    output_dir: str,
    camera_name: str,
    organize_by_camera: bool = False
) -> bool:
    """
    Copie l'image originale dans le dossier original/.
    Ne modifie pas le fichier source.
    """
    try:
        if organize_by_camera:
            original_dir = os.path.join(output_dir, "original", camera_name)
        else:
            original_dir = os.path.join(output_dir, "original")

        os.makedirs(original_dir, exist_ok=True)

        filename = os.path.basename(source_path)
        dest_path = Path(original_dir) / filename
        dest_path = _unique_path(dest_path)

        shutil.copy2(source_path, dest_path)
        logger.info("original_saved", source=source_path, dest=str(dest_path))
        return True

    except Exception as e:
        logger.error("original_save_failed", source=source_path, error=str(e))
        return False


# ------------------------------------------------------------------------
# Construction des chemins de sortie pour les images ANNOTÉES
# ------------------------------------------------------------------------

def get_output_path(
    output_dir: str,
    filename: str,
    camera_name: str,
    has_valid_detections: bool,
    organize_by_result: bool = True,
    organize_by_camera: bool = True
) -> str:
    """
    Construit le chemin de sortie pour les images de sortie (annotées),
    selon la structure configurée.
    """
    path_parts = [output_dir]

    if organize_by_result:
        path_parts.append("true" if has_valid_detections else "false")

    if organize_by_camera:
        path_parts.append(camera_name)

    full_dir = os.path.join(*path_parts)
    os.makedirs(full_dir, exist_ok=True)

    return os.path.join(full_dir, filename)


# ------------------------------------------------------------------------
# Post-traitement du FICHIER SOURCE après détection
# ------------------------------------------------------------------------

def handle_processed_image(
    source_path: str,
    action: str,
    output_dir: Optional[str] = None,
    *,
    save_original: bool = True,
    original_by_camera: bool = False,
    camera: Optional[str] = None,
) -> bool:
    """
    Gère le fichier source après traitement.

    action:
      - 'none'  : ne rien faire
      - 'erase' : supprimer l'image source
      - 'move'  : déplacer l'image source
                 • si save_original=True  → vers  <output_dir>/original[/<camera>]/<fichier>
                 • si save_original=False → vers  <output_dir>/<fichier>  (racine)

    Remarque: ce comportement respecte la config existante sans ajouter de nouvelles clés.
    Pour placer la source dans original/, mettre save_original=true.
    """
    if action not in ("move", "erase", "none"):
        logger.error("invalid_action", action=action, valid_actions=["move", "erase", "none"])
        return False

    if not os.path.exists(source_path):
        logger.error("source_file_not_found", path=source_path)
        return False

    # 'none' → pas de modification de la source
    if action == "none":
        logger.debug("image_kept", path=source_path)
        return True

    # 'erase' → suppression
    if action == "erase":
        try:
            os.remove(source_path)
            logger.info("image_erased", path=source_path)
            return True
        except Exception as e:
            logger.error("image_erase_failed", path=source_path, error=str(e))
            return False

    # 'move' → déplacement
    if action == "move":
        if not output_dir:
            logger.error("output_dir_required_for_move")
            return False

        try:
            if save_original:
                # Déplacer dans shared_out/original[/camera]
                dest_dir = Path(output_dir) / "original"
                if original_by_camera and camera:
                    dest_dir = dest_dir / camera
            else:
                # Déplacer dans la racine de shared_out (comportement historique)
                dest_dir = Path(output_dir)

            dest_dir.mkdir(parents=True, exist_ok=True)

            filename = os.path.basename(source_path)
            dest_path = _unique_path(dest_dir / filename)

            shutil.move(source_path, dest_path)
            if save_original:
                logger.info(
                    "input_moved_to_original",
                    source=source_path,
                    dest=str(dest_path),
                )
            else:
                logger.info(
                    "input_moved_to_output_root",
                    source=source_path,
                    dest=str(dest_path),
                )
            return True

        except Exception as e:
            logger.error("image_move_failed", path=source_path, error=str(e))
            return False

    return False


# ------------------------------------------------------------------------
# Divers
# ------------------------------------------------------------------------

def ensure_directory_exists(directory: str) -> bool:
    """S'assure qu'un répertoire existe, le crée si nécessaire."""
    try:
        os.makedirs(directory, exist_ok=True)
        return True
    except Exception as e:
        logger.error("directory_creation_failed", path=directory, error=str(e))
        return False


def list_images(directory: str, extensions: tuple = (".jpg", ".jpeg", ".png")) -> list:
    """
    Liste tous les fichiers image dans un répertoire.
    """
    if not os.path.exists(directory):
        logger.warning("directory_not_found", path=directory)
        return []

    images = []
    try:
        for filename in os.listdir(directory):
            if filename.lower().endswith(extensions):
                images.append(os.path.join(directory, filename))

        logger.debug("images_listed", directory=directory, count=len(images))
        return sorted(images)

    except Exception as e:
        logger.error("list_images_failed", directory=directory, error=str(e))
        return []
