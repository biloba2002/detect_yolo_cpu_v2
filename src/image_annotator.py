"""
Annotation d'images avec zones et objets détectés.
"""

from pathlib import Path
from typing import List, Dict, Tuple, Optional
import cv2
import numpy as np
from src.zone_manager import ZoneManager
from src.config_loader import CameraConfig
from src.logger import get_logger

logger = get_logger(__name__)


class ImageAnnotator:
    """Annotateur d'images pour visualiser zones et détections."""
    
    # Couleurs prédéfinies (BGR pour OpenCV)
    ZONE_COLORS = [
        (0, 255, 0),      # Vert
        (255, 0, 0),      # Bleu
        (0, 255, 255),    # Jaune
        (255, 0, 255),    # Magenta
        (255, 165, 0),    # Orange
        (128, 0, 128),    # Violet
    ]
    
    DETECTION_COLOR = (0, 0, 255)      # Rouge pour détections
    FALSE_DETECTION_COLOR = (128, 128, 128)  # Gris pour fausses détections
    TEXT_COLOR = (255, 255, 255)       # Blanc pour texte
    TEXT_BG_COLOR = (0, 0, 0)          # Noir pour fond texte
    
    def __init__(self, camera_config: CameraConfig):
        """
        Initialise l'annotateur.
        
        Args:
            camera_config: Configuration de la caméra
        """
        self.camera_config = camera_config
        self.zone_manager: Optional[ZoneManager] = None
    
    def annotate_composite(
        self,
        image_path: str,
        output_path: str,
        detections: List[Dict],
        zone_manager: Optional[ZoneManager] = None
    ) -> bool:
        """
        Crée une image composite avec toutes les zones et détections.
        
        Args:
            image_path: Chemin image source
            output_path: Chemin image de sortie
            detections: Liste des détections
            zone_manager: Gestionnaire de zones (optionnel)
            
        Returns:
            True si succès
        """
        # Charger l'image
        image = cv2.imread(image_path)
        if image is None:
            logger.error("image_load_failed", path=image_path)
            return False
        
        annotated = image.copy()
        
        # Dessiner les zones si activées
        if zone_manager and self.camera_config.zones:
            for idx, zone_config in enumerate(self.camera_config.zones):
                if zone_config.show_zone:
                    color = self.ZONE_COLORS[idx % len(self.ZONE_COLORS)]
                    self._draw_zone(annotated, zone_manager, zone_config.name, color)
        
        # Dessiner les détections si activées
        if self.camera_config.show_object:
            for detection in detections:
                self._draw_detection(annotated, detection)
        
        # Sauvegarder
        success = cv2.imwrite(output_path, annotated)
        if success:
            logger.info("composite_created", output=output_path)
        else:
            logger.error("composite_save_failed", output=output_path)
        
        return success
    
    def annotate_zone(
        self,
        image_path: str,
        output_path: str,
        zone_name: str,
        detections: List[Dict],
        zone_manager: ZoneManager
    ) -> bool:
        """
        Crée une image annotée pour une zone spécifique.
        
        Args:
            image_path: Chemin image source
            output_path: Chemin image de sortie
            zone_name: Nom de la zone
            detections: Liste des détections (déjà filtrées pour cette zone)
            zone_manager: Gestionnaire de zones
            
        Returns:
            True si succès
        """
        # Charger l'image
        image = cv2.imread(image_path)
        if image is None:
            logger.error("image_load_failed", path=image_path)
            return False
        
        annotated = image.copy()
        
        # Trouver la config de la zone
        try:
            zone_config = zone_manager.get_zone_config(zone_name)
        except ValueError:
            logger.error("zone_config_not_found", zone=zone_name)
            return False
        
        # Dessiner la zone
        if zone_config.show_zone:
            self._draw_zone(annotated, zone_manager, zone_name, self.ZONE_COLORS[0])
        
        # Dessiner les détections dans cette zone
        if zone_config.show_object:
            for detection in detections:
                if zone_name in detection.get('zones', []):
                    self._draw_detection(annotated, detection)
        
        # Sauvegarder
        success = cv2.imwrite(output_path, annotated)
        if success:
            logger.info("zone_image_created", zone=zone_name, output=output_path)
        else:
            logger.error("zone_image_save_failed", zone=zone_name, output=output_path)
        
        return success
    
    def _draw_zone(
        self,
        image: np.ndarray,
        zone_manager: ZoneManager,
        zone_name: str,
        color: Tuple[int, int, int]
    ) -> None:
        """
        Dessine le contour d'une zone avec transparence.
        
        Args:
            image: Image numpy array (modifiée in-place)
            zone_manager: Gestionnaire de zones
            zone_name: Nom de la zone
            color: Couleur BGR
        """
        coords = zone_manager.get_polygon_pixel_coords(zone_name)
        if not coords:
            return
        
        # Convertir en numpy array
        points = np.array(coords, dtype=np.int32)
        
        # Créer overlay pour transparence du contour
        overlay = image.copy()
        
        # Dessiner le contour sur l'overlay
        cv2.polylines(overlay, [points], isClosed=True, color=color, thickness=3)
        
        # Fusionner avec 50% de transparence
        alpha = 0.8
        cv2.addWeighted(overlay, alpha, image, 1 - alpha, 0, image)
        
        # Ajouter le nom de la zone
        if len(coords) > 0:
            text_pos = coords[0]
            self._draw_text(image, zone_name, text_pos, color)
    
    def _draw_detection(
        self,
        image: np.ndarray,
        detection: Dict
    ) -> None:
        """
        Dessine une détection (bounding box + label).
        
        Args:
            image: Image numpy array (modifiée in-place)
            detection: Dict avec keys 'bbox', 'class', 'confidence', 'is_false'
        """
        bbox = detection['bbox']
        x1, y1, x2, y2 = map(int, bbox)
        
        # Couleur selon fausse détection ou non
        color = self.FALSE_DETECTION_COLOR if detection.get('is_false', False) else self.DETECTION_COLOR
        
        # Dessiner la bounding box
        cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)
        
        # Label avec classe et confidence
        label = f"{detection['class']} {detection['confidence']:.2f}"
        if detection.get('is_false', False):
            label += " (LOW)"
        
        self._draw_text(image, label, (x1, y1 - 10), color)
    
    def _draw_text(
        self,
        image: np.ndarray,
        text: str,
        position: Tuple[int, int],
        color: Tuple[int, int, int]
    ) -> None:
        """
        Dessine du texte avec fond pour meilleure lisibilité.
        
        Args:
            image: Image numpy array (modifiée in-place)
            text: Texte à afficher
            position: Position (x, y)
            color: Couleur du texte
        """
        x, y = position
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 1.0  # Augmenté de 0.6 à 1.0 pour meilleure lisibilité
        thickness = 3     # Augmenté de 2 à 3 pour meilleure visibilité
        
        # Calculer la taille du texte
        (text_width, text_height), baseline = cv2.getTextSize(
            text, font, font_scale, thickness
        )
        
        # Dessiner le fond noir
        cv2.rectangle(
            image,
            (x, y - text_height - baseline),
            (x + text_width, y + baseline),
            self.TEXT_BG_COLOR,
            -1
        )
        
        # Dessiner le texte
        cv2.putText(
            image,
            text,
            (x, y),
            font,
            font_scale,
            self.TEXT_COLOR,
            thickness
        )