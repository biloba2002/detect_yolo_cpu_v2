"""
Construction de messages personnalisés pour notifications.
"""

from collections import Counter
from typing import Dict, List, Optional
from src.config_loader import ZoneConfig, CameraConfig
from src.logger import get_logger

logger = get_logger(__name__)

# Dictionnaire par classe: libellé singulier, pluriel, genre ('m'/'f')
CLASS_META = {
    "person":     {"sg": "personne", "pl": "personnes", "g": "f"},
    "dog":        {"sg": "chien",    "pl": "chiens",    "g": "m"},
    "cat":        {"sg": "chat",     "pl": "chats",     "g": "m"},
    "car":        {"sg": "voiture",  "pl": "voitures",  "g": "f"},
    "truck":      {"sg": "camion",   "pl": "camions",   "g": "m"},
    "motorcycle": {"sg": "moto",     "pl": "motos",     "g": "f"},
    "bicycle":    {"sg": "vélo",     "pl": "vélos",     "g": "m"},
    "bird":       {"sg": "oiseau",   "pl": "oiseaux",   "g": "m"},
}

def _num_word(n: int, gender: str) -> str:
    """1 -> 'un'/'une' selon le genre. Sinon retourne le nombre."""
    if n == 1:
        return "une" if gender == "f" else "un"
    return str(n)

def _label(cls: str, n: int) -> str:
    meta = CLASS_META.get(cls)
    if meta:
        return meta["pl"] if n > 1 else meta["sg"]
    # fallback générique
    base = cls
    return f"{base}s" if n > 1 else base

def _gender(cls: str) -> str:
    meta = CLASS_META.get(cls)
    return meta["g"] if meta else "m"

def _format_by_class_sentence(by_class: Dict[str, int]) -> str:
    """Ex: 'une personne, un chien et 2 voitures'."""
    if not by_class:
        return "Aucune détection"
    parts = []
    for cls, n in by_class.items():
        parts.append(f"{_num_word(n, _gender(cls))} {_label(cls, n)}")
    if len(parts) == 1:
        return parts[0]
    return ", ".join(parts[:-1]) + " et " + parts[-1]

class MessageBuilder:
    """Constructeur de messages de notification."""

    def build_camera_message(
        self,
        camera_config: CameraConfig,
        counters: Dict
    ) -> Optional[Dict]:
        by_class: Dict[str, int] = dict(counters.get("by_class", {}))
        total_valid = sum(by_class.values())
        if total_valid == 0:
            return None

        sentence = _format_by_class_sentence(by_class)
        # Accord de 'détecté(e)(s)' simplifié
        msg = f"{sentence} détecté{'e' if total_valid == 1 else 'e'}{'s' if total_valid > 1 else ''}"

        out = {
            "message": msg,
            "audio": bool(getattr(camera_config, "audio_msg", False)),
            "by_class": by_class,
            "objects": list(by_class.keys()),
        }
        logger.debug("camera_message_built", camera=camera_config.name, message=msg, by_class=by_class)
        return out

    def build_zone_message(
        self,
        zone_config: ZoneConfig,
        counters: Dict,
        zone_detections: List[Dict],
    ) -> Optional[Dict]:
        if not zone_detections:
            return None

        ct = Counter(d["class"] for d in zone_detections if not d.get("is_false"))
        by_class: Dict[str, int] = dict(ct)
        total = sum(by_class.values())
        if total == 0:
            return None

        # Pas de template: messages auto avec un/une + pluriels
        sentence = _format_by_class_sentence(by_class)
        zone_name = getattr(zone_config, "name", "zone")
        msg = f"{sentence} dans la {zone_name}"

        out = {
            "message": msg,
            "audio": bool(getattr(zone_config, "audio_msg", False)),
            "by_class": by_class,
            "objects": list(by_class.keys()),
        }
        logger.debug("zone_message_built", zone=zone_name, message=msg, by_class=by_class)
        return out

    def build_summary_message(
        self,
        camera_name: str,
        counters: Dict,
        zones_messages: List[Dict]
    ) -> str:
        total = counters.get("total", 0)
        false = counters.get("false", 0)
        valid = total - false

        lines = [
            f"📷 {camera_name}",
            f"✅ Détections valides: {valid}",
            f"❌ Fausses détections: {false}",
        ]

        by_class = counters.get("by_class", {})
        if by_class:
            lines.append("📊 Par classe:")
            for cls, count in sorted(by_class.items()):
                lines.append(f"  - {_label(cls, count)}: {count}")

        if zones_messages:
            lines.append("🗺️ Par zone:")
            for zm in zones_messages:
                if not zm:
                    continue
                zone = zm.get("zone", "unknown")
                msg = zm.get("message", "")
                lines.append(f"  - {zone}: {msg}")

        return "\n".join(lines)
