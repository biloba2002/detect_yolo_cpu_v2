"""
Construction de messages personnalisés pour notifications.
"""

from typing import Dict, List
from src.config_loader import ZoneConfig, CameraConfig
from src.logger import get_logger

logger = get_logger(__name__)


class MessageBuilder:
    """Constructeur de messages de notification."""
    
    def build_camera_message(
        self,
        camera_config: CameraConfig,
        counters: Dict
    ) -> Dict:
        """
        Construit un message pour une caméra.
        
        Args:
            camera_config: Configuration de la caméra
            counters: Compteurs de détections
            
        Returns:
            Dict avec type, audio, message, camera, detections
        """
        if not camera_config.text_msg:
            return {}
        
        total_valid = counters['total'] - counters['false']
        
        if total_valid == 0:
            return {}
        
        # Construire le message basique
        message = f"{total_valid} objet(s) détecté(s)"
        
        # Détail par classe
        by_class = counters.get('by_class', {})
        if by_class:
            class_details = [f"{count} {cls}" for cls, count in by_class.items()]
            message = f"{', '.join(class_details)} détecté(s)"
        
        result = {
            'type': 'text',
            'audio': camera_config.audio_msg,
            'message': message,
            'camera': camera_config.name,
            'detections': by_class
        }
        
        logger.debug("camera_message_built", camera=camera_config.name, message=message)
        
        return result
    
    def build_zone_message(
        self,
        zone_config: ZoneConfig,
        camera_name: str,
        zone_detections: List[Dict]
    ) -> Dict:
        """
        Construit un message pour une zone spécifique.
        
        Args:
            zone_config: Configuration de la zone
            camera_name: Nom de la caméra
            zone_detections: Détections dans cette zone
            
        Returns:
            Dict avec type, audio, message, camera, zone, detections
        """
        if not zone_config.text_msg:
            return {}
        
        # Filtrer les fausses détections
        valid_detections = [d for d in zone_detections if not d.get('is_false', False)]
        
        if not valid_detections:
            return {}
        
        # Compter par classe
        class_counts = {}
        for det in valid_detections:
            cls = det['class']
            class_counts[cls] = class_counts.get(cls, 0) + 1
        
        # Utiliser le template si disponible
        if zone_config.msg_template:
            message = self._apply_template(zone_config.msg_template, class_counts)
        else:
            # Message par défaut
            class_details = [f"{count} {cls}" for cls, count in class_counts.items()]
            message = f"{', '.join(class_details)} détecté(s) dans {zone_config.name}"
        
        result = {
            'type': 'text',
            'audio': zone_config.audio_msg,
            'message': message,
            'camera': camera_name,
            'zone': zone_config.name,
            'detections': class_counts
        }
        
        logger.debug(
            "zone_message_built",
            camera=camera_name,
            zone=zone_config.name,
            message=message
        )
        
        return result
    
    def _apply_template(self, template: str, class_counts: Dict[str, int]) -> str:
        """
        Applique un template de message avec remplacement de variables.
        
        Args:
            template: Template avec placeholders {count_CLASS}
            class_counts: Dict {class_name: count}
            
        Returns:
            Message formaté
        """
        message = template
        
        # Remplacer chaque {count_CLASS}
        for cls, count in class_counts.items():
            placeholder = f"{{count_{cls}}}"
            message = message.replace(placeholder, str(count))
        
        # Remplacer les placeholders non trouvés par 0
        import re
        message = re.sub(r'\{count_\w+\}', '0', message)
        
        return message
    
    def build_summary_message(
        self,
        camera_name: str,
        counters: Dict,
        zones_messages: List[Dict]
    ) -> str:
        """
        Construit un message récapitulatif.
        
        Args:
            camera_name: Nom de la caméra
            counters: Compteurs globaux
            zones_messages: Messages des zones
            
        Returns:
            Message récapitulatif
        """
        total = counters['total']
        false = counters['false']
        valid = total - false
        
        lines = [
            f"📷 {camera_name}",
            f"✅ Détections valides: {valid}",
            f"❌ Fausses détections: {false}",
        ]
        
        # Détails par classe
        by_class = counters.get('by_class', {})
        if by_class:
            lines.append("📊 Par classe:")
            for cls, count in sorted(by_class.items()):
                lines.append(f"  - {cls}: {count}")
        
        # Détails par zone
        if zones_messages:
            lines.append("🗺️ Par zone:")
            for zone_msg in zones_messages:
                if zone_msg:
                    zone = zone_msg.get('zone', 'unknown')
                    msg = zone_msg.get('message', '')
                    lines.append(f"  - {zone}: {msg}")
        
        return "\n".join(lines)