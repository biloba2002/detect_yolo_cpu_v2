"""
Fonctions utilitaires pour la gestion des fichiers et autres helpers.
"""

import os
import shutil
from pathlib import Path
from typing import Optional
from src.logger import get_logger

logger = get_logger(__name__)


def save_original_image(
    source_path: str,
    output_dir: str,
    camera_name: str,
    organize_by_camera: bool = False
) -> bool:
    """
    Copie l'image originale dans le dossier original/.
    
    Args:
        source_path: Chemin image source
        output_dir: Dossier de sortie de base
        camera_name: Nom de la caméra
        organize_by_camera: Si True, crée un sous-dossier par caméra
        
    Returns:
        True si succès
    """
    try:
        if organize_by_camera:
            original_dir = os.path.join(output_dir, "original", camera_name)
        else:
            original_dir = os.path.join(output_dir, "original")
        
        os.makedirs(original_dir, exist_ok=True)
        
        filename = os.path.basename(source_path)
        dest_path = os.path.join(original_dir, filename)
        
        if os.path.exists(dest_path):
            base, ext = os.path.splitext(filename)
            counter = 1
            while os.path.exists(dest_path):
                dest_path = os.path.join(original_dir, f"{base}_{counter}{ext}")
                counter += 1
        
        shutil.copy2(source_path, dest_path)
        logger.info("original_saved", source=source_path, dest=dest_path)
        return True
        
    except Exception as e:
        logger.error("original_save_failed", source=source_path, error=str(e))
        return False


def get_output_path(
    output_dir: str,
    filename: str,
    camera_name: str,
    has_valid_detections: bool,
    organize_by_result: bool = True,
    organize_by_camera: bool = True
) -> str:
    """
    Construit le chemin de sortie selon la structure configurée.
    
    Args:
        output_dir: Dossier de sortie de base
        filename: Nom du fichier
        camera_name: Nom de la caméra
        has_valid_detections: True si détections valides, False si fausse alerte
        organize_by_result: Créer sous-dossiers true/false
        organize_by_camera: Créer sous-dossiers par caméra
        
    Returns:
        Chemin complet du fichier de sortie
    """
    path_parts = [output_dir]
    
    if organize_by_result:
        path_parts.append("true" if has_valid_detections else "false")
    
    if organize_by_camera:
        path_parts.append(camera_name)
    
    full_dir = os.path.join(*path_parts)
    os.makedirs(full_dir, exist_ok=True)
    
    return os.path.join(full_dir, filename)


def handle_processed_image(
    source_path: str,
    action: str,
    output_dir: Optional[str] = None
) -> bool:
    """
    Gère l'image source après traitement.
    
    Args:
        source_path: Chemin image source
        action: 'move' | 'erase' | 'none'
        output_dir: Dossier de sortie (requis pour action='move')
        
    Returns:
        True si succès, False sinon
        
    Raises:
        ValueError: Si action='move' sans output_dir
    """
    if action not in ['move', 'erase', 'none']:
        logger.error("invalid_action", action=action, valid_actions=['move', 'erase', 'none'])
        return False
    
    if not os.path.exists(source_path):
        logger.error("source_file_not_found", path=source_path)
        return False
    
    if action == "none":
        logger.debug("image_kept", path=source_path)
        return True
    
    elif action == "erase":
        try:
            os.remove(source_path)
            logger.info("image_erased", path=source_path)
            return True
        except Exception as e:
            logger.error("image_erase_failed", path=source_path, error=str(e))
            return False
    
    elif action == "move":
        if not output_dir:
            raise ValueError("output_dir required for action='move'")
        
        try:
            os.makedirs(output_dir, exist_ok=True)
            
            filename = os.path.basename(source_path)
            dest_path = os.path.join(output_dir, filename)
            
            if os.path.exists(dest_path):
                base, ext = os.path.splitext(filename)
                counter = 1
                while os.path.exists(dest_path):
                    dest_path = os.path.join(output_dir, f"{base}_{counter}{ext}")
                    counter += 1
                logger.warning("file_renamed", original=filename, new=os.path.basename(dest_path))
            
            shutil.move(source_path, dest_path)
            logger.info("image_moved", source=source_path, dest=dest_path)
            return True
            
        except Exception as e:
            logger.error("image_move_failed", path=source_path, error=str(e))
            return False
    
    return False


def ensure_directory_exists(directory: str) -> bool:
    """
    S'assure qu'un répertoire existe, le crée si nécessaire.
    
    Args:
        directory: Chemin du répertoire
        
    Returns:
        True si le répertoire existe (ou a été créé), False sinon
    """
    try:
        os.makedirs(directory, exist_ok=True)
        return True
    except Exception as e:
        logger.error("directory_creation_failed", path=directory, error=str(e))
        return False


def list_images(directory: str, extensions: tuple = ('.jpg', '.jpeg', '.png')) -> list:
    """
    Liste tous les fichiers image dans un répertoire.
    
    Args:
        directory: Chemin du répertoire
        extensions: Tuple des extensions acceptées
        
    Returns:
        Liste des chemins complets des images trouvées
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
