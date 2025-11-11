"""
Configuration loader avec validation Pydantic.
Charge et valide le fichier config.yaml.
"""

from pathlib import Path
from typing import List, Optional

import yaml
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings


class ZoneConfig(BaseModel):
    """Configuration d'une zone de détection."""
    name: str
    polygon: List[float] = Field(..., min_length=6)  # Au moins 3 points (x,y)
    show_zone: bool = True
    show_object: bool = True
    entity_ha: bool = True
    text_msg: bool = False
    audio_msg: bool = False
    msg_template: str = ""

    @field_validator('polygon')
    @classmethod
    def validate_polygon(cls, v: List[float]) -> List[float]:
        """Valide que le polygone a un nombre pair de coordonnées."""
        if len(v) % 2 != 0:
            raise ValueError("Polygon must have an even number of coordinates (x,y pairs)")
        if len(v) < 6:
            raise ValueError("Polygon must have at least 3 points (6 coordinates)")
        if not all(0 <= coord <= 1 for coord in v):
            raise ValueError("All polygon coordinates must be between 0 and 1")
        return v


class CameraConfig(BaseModel):
    """Configuration d'une caméra."""
    name: str
    detect: List[str] = Field(default_factory=list)
    text_msg: bool = False
    audio_msg: bool = False
    show_object: bool = True
    entity_ha: bool = True
    zones: List[ZoneConfig] = Field(default_factory=list)


class MQTTConfig(BaseModel):
    """Configuration MQTT."""
    broker: str
    port: int = 1883
    qos: int = 1
    retain: bool = False
    username: str = ""
    password: str = ""
    topics: dict = Field(default_factory=dict)


class HomeAssistantConfig(BaseModel):
    """Configuration Home Assistant."""
    autodiscovery: bool = True
    discovery_prefix: str = "homeassistant"


class DetectionConfig(BaseModel):
    """Configuration de détection YOLO."""
    model: str = "yolov11n.pt"
    confidence_threshold: float = Field(default=0.5, ge=0.0, le=1.0)


class AppConfig(BaseModel):
    """Configuration générale de l'application."""
    name: str = "detect_yolo_cpu_v2"
    version: str = "2.0.0"


class DirectoriesConfig(BaseModel):
    """Configuration des répertoires."""
    input: Path
    output: Path


class OutputStructureConfig(BaseModel):
    """Configuration de la structure de sortie."""
    organize_by_result: bool = True      # true/false sous-dossiers
    organize_by_camera: bool = True      # sous-dossiers par caméra
    save_original: bool = True           # copier image originale
    original_by_camera: bool = False     # sous-dossiers caméra dans original/


class ProcessingConfig(BaseModel):
    """Configuration du traitement des images."""
    input_action: str = Field(default="move", pattern="^(move|erase|none)$")
    output_structure: OutputStructureConfig = OutputStructureConfig()


class LoggingConfig(BaseModel):
    """Configuration des logs."""
    level: str = Field(default="info", pattern="^(debug|info|warning|error)$")
    format: str = "json"


class Config(BaseSettings):
    """Configuration principale de l'application."""
    app: AppConfig
    directories: DirectoriesConfig
    processing: ProcessingConfig = ProcessingConfig()  # Valeur par défaut
    logging: LoggingConfig
    mqtt: MQTTConfig
    homeassistant: HomeAssistantConfig
    detection: DetectionConfig
    cameras: List[CameraConfig]

    def get_camera_config(self, camera_name: str) -> CameraConfig:
        """
        Récupère la configuration d'une caméra par son nom.
        Retourne la config 'generique' si le nom n'est pas trouvé.
        """
        for camera in self.cameras:
            if camera.name == camera_name:
                return camera
        
        # Fallback vers caméra générique
        for camera in self.cameras:
            if camera.name == "generique":
                return camera
        
        raise ValueError("No 'generique' camera configuration found as fallback")


def load_config(config_path: str = "/app/config/config.yaml") -> Config:
    """
    Charge et valide le fichier de configuration YAML.
    
    Args:
        config_path: Chemin vers le fichier config.yaml
        
    Returns:
        Config: Configuration validée
        
    Raises:
        FileNotFoundError: Si le fichier n'existe pas
        ValueError: Si la configuration est invalide
    """
    path = Path(config_path)
    
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    with open(path, 'r', encoding='utf-8') as f:
        config_data = yaml.safe_load(f)
    
    return Config(**config_data)


def extract_camera_name(filename: str) -> str:
    """
    Extrait le nom de la caméra depuis le nom du fichier.
    Format attendu: {camera_name}_{timestamp}.jpg
    
    Args:
        filename: Nom du fichier (ex: reolink_2025-11-10_10-30-15.jpg)
        
    Returns:
        str: Nom de la caméra (ex: reolink)
    """
    # Supprimer l'extension
    name_without_ext = Path(filename).stem
    
    # Extraire la partie avant le premier underscore
    parts = name_without_ext.split('_')
    
    if len(parts) > 0:
        return parts[0]
    
    return "generique"