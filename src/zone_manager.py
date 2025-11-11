"""
Gestionnaire de zones de détection avec polygones Shapely.
"""

from typing import List, Tuple, Dict
from shapely.geometry import Point, Polygon
from src.config_loader import ZoneConfig
from src.logger import get_logger

logger = get_logger(__name__)


class ZoneManager:
    """Gère les zones de détection définies par des polygones."""
    
    def __init__(self, zones: List[ZoneConfig], image_width: int, image_height: int):
        """
        Initialise le gestionnaire de zones.
        
        Args:
            zones: Liste des configurations de zones
            image_width: Largeur de l'image en pixels
            image_height: Hauteur de l'image en pixels
        """
        self.zones = zones
        self.image_width = image_width
        self.image_height = image_height
        self.polygons: Dict[str, Polygon] = {}
        
        # Créer les polygones Shapely à partir des coordonnées normalisées
        for zone in zones:
            polygon_coords = self._normalize_to_pixels(zone.polygon)
            self.polygons[zone.name] = Polygon(polygon_coords)
            logger.debug(
                "zone_created",
                zone_name=zone.name,
                points=len(polygon_coords),
                bounds=self.polygons[zone.name].bounds
            )
    
    def _normalize_to_pixels(self, coords: List[float]) -> List[Tuple[float, float]]:
        """
        Convertit les coordonnées normalisées [0..1] en pixels.
        
        Args:
            coords: Liste de coordonnées [x1, y1, x2, y2, ...]
            
        Returns:
            Liste de tuples [(x1, y1), (x2, y2), ...]
        """
        points = []
        for i in range(0, len(coords), 2):
            x_norm = coords[i]
            y_norm = coords[i + 1]
            x_pixel = x_norm * self.image_width
            y_pixel = y_norm * self.image_height
            points.append((x_pixel, y_pixel))
        return points
    
    def point_in_zone(self, x: float, y: float, zone_name: str) -> bool:
        """
        Vérifie si un point est dans une zone.
        
        Args:
            x: Coordonnée X en pixels
            y: Coordonnée Y en pixels
            zone_name: Nom de la zone
            
        Returns:
            True si le point est dans la zone
        """
        if zone_name not in self.polygons:
            logger.warning("zone_not_found", zone_name=zone_name)
            return False
        
        point = Point(x, y)
        return self.polygons[zone_name].contains(point)
    
    def bbox_center_in_zone(self, bbox: Tuple[float, float, float, float], zone_name: str) -> bool:
        """
        Vérifie si le centre d'une bounding box est dans une zone.
        
        Args:
            bbox: (x1, y1, x2, y2) coordonnées de la bbox en pixels
            zone_name: Nom de la zone
            
        Returns:
            True si le centre de la bbox est dans la zone
        """
        x1, y1, x2, y2 = bbox
        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2
        return self.point_in_zone(center_x, center_y, zone_name)
    
    def filter_detections_by_zone(
        self,
        detections: List[Dict],
        zone_name: str
    ) -> List[Dict]:
        """
        Filtre les détections pour ne garder que celles dans une zone.
        
        Args:
            detections: Liste de détections avec clé 'bbox'
            zone_name: Nom de la zone
            
        Returns:
            Liste filtrée de détections
        """
        if zone_name not in self.polygons:
            logger.warning("zone_not_found_for_filter", zone_name=zone_name)
            return []
        
        filtered = []
        for det in detections:
            if self.bbox_center_in_zone(det['bbox'], zone_name):
                filtered.append(det)
        
        logger.debug(
            "detections_filtered",
            zone_name=zone_name,
            total=len(detections),
            filtered=len(filtered)
        )
        
        return filtered
    
    def get_zone_config(self, zone_name: str) -> ZoneConfig:
        """
        Récupère la configuration d'une zone.
        
        Args:
            zone_name: Nom de la zone
            
        Returns:
            Configuration de la zone
            
        Raises:
            ValueError: Si la zone n'existe pas
        """
        for zone in self.zones:
            if zone.name == zone_name:
                return zone
        raise ValueError(f"Zone '{zone_name}' not found")
    
    def get_polygon_pixel_coords(self, zone_name: str) -> List[Tuple[int, int]]:
        """
        Récupère les coordonnées du polygone en pixels (pour dessin).
        
        Args:
            zone_name: Nom de la zone
            
        Returns:
            Liste de tuples (x, y) en pixels
        """
        if zone_name not in self.polygons:
            return []
        
        coords = list(self.polygons[zone_name].exterior.coords)
        return [(int(x), int(y)) for x, y in coords]