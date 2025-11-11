"""
Moteur de détection YOLO avec filtrage par zones.
"""
import os
os.environ['CUDA_VISIBLE_DEVICES'] = ''  # ← AJOUTER cette ligne avant tous les imports


from pathlib import Path
from typing import List, Dict, Tuple, Optional
import cv2
from ultralytics import YOLO
from src.config_loader import CameraConfig
from src.zone_manager import ZoneManager
from src.logger import get_logger

logger = get_logger(__name__)


class Detector:
    """Détecteur d'objets YOLO avec support des zones."""
    
    def __init__(self, model_path: str, confidence_threshold: float = 0.5):
        """
        Initialise le détecteur YOLO.
        
        Args:
            model_path: Chemin vers le modèle YOLO (.pt)
            confidence_threshold: Seuil de confiance minimum (0-1)
        """
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        
        # Forcer l'utilisation du CPU uniquement
        import os
        os.environ['CUDA_VISIBLE_DEVICES'] = ''
        
        self.model = YOLO(model_path)
        logger.info("detector_initialized", model=model_path, threshold=confidence_threshold, device="cpu")
    
    def detect(
        self,
        image_path: str,
        camera_config: CameraConfig
    ) -> Tuple[List[Dict], Dict]:
        """
        Détecte les objets dans une image.
        
        Args:
            image_path: Chemin de l'image
            camera_config: Configuration de la caméra
            
        Returns:
            Tuple (detections, counters)
            - detections: Liste de dicts {class, bbox, confidence, is_false, zones}
            - counters: Dict des compteurs {total, false, by_class, by_zone}
        """
        # Charger l'image
        image = cv2.imread(image_path)
        if image is None:
            logger.error("image_load_failed", path=image_path)
            return [], self._empty_counters()
        
        height, width = image.shape[:2]
        logger.debug("image_loaded", path=image_path, width=width, height=height)
        
        # Exécuter la détection YOLO (CPU uniquement)
        results = self.model(image, verbose=False, device='cpu')[0]
        
        # Créer le gestionnaire de zones si nécessaire
        zone_manager = None
        if camera_config.zones:
            zone_manager = ZoneManager(camera_config.zones, width, height)
        
        # Extraire les détections
        detections = []
        counters = self._empty_counters()
        
        for box in results.boxes:
            class_id = int(box.cls[0])
            class_name = results.names[class_id]
            confidence = float(box.conf[0])
            bbox = box.xyxy[0].cpu().numpy().tolist()  # [x1, y1, x2, y2]
            
            # Filtrer par classe détectable
            if class_name not in camera_config.detect:
                continue
            
            # Marquer les fausses détections
            is_false = confidence < self.confidence_threshold
            
            detection = {
                'class': class_name,
                'confidence': confidence,
                'bbox': tuple(bbox),
                'is_false': is_false,
                'zones': []
            }
            
            # Compteurs globaux
            counters['total'] += 1
            if is_false:
                counters['false'] += 1
            else:
                counters['by_class'][class_name] = counters['by_class'].get(class_name, 0) + 1
            
            # Vérifier les zones
            if zone_manager:
                for zone_config in camera_config.zones:
                    if zone_manager.bbox_center_in_zone(detection['bbox'], zone_config.name):
                        detection['zones'].append(zone_config.name)
                        
                        # Compteurs par zone
                        if not is_false:
                            zone_key = f"zone_{zone_config.name}"
                            if zone_key not in counters['by_zone']:
                                counters['by_zone'][zone_key] = {'total': 0, 'by_class': {}}
                            
                            counters['by_zone'][zone_key]['total'] += 1
                            zone_class = counters['by_zone'][zone_key]['by_class']
                            zone_class[class_name] = zone_class.get(class_name, 0) + 1
            
            detections.append(detection)
        
        logger.info(
            "detection_completed",
            image=Path(image_path).name,
            total=counters['total'],
            valid=counters['total'] - counters['false'],
            false=counters['false']
        )
        
        # Marquer comme fausse détection si aucune détection valide
        if counters['total'] == 0 or (counters['total'] - counters['false']) == 0:
            counters['false'] = 1
            counters['total'] = 1
        
        return detections, counters
    
    def _empty_counters(self) -> Dict:
        """Retourne une structure de compteurs vide."""
        return {
            'total': 0,
            'false': 0,
            'by_class': {},
            'by_zone': {}
        }