"""
Point d'entrée principal de l'application detect_yolo_cpu_v2.
Orchestre tous les modules : configuration, détection, annotation, MQTT, etc.
"""

import signal
import sys
import time
from pathlib import Path
from typing import Optional

from src.config_loader import load_config
from src.detector import Detector
from src.file_watcher import FileWatcher
from src.image_annotator import ImageAnnotator
from src.logger import setup_logger
from src.message_builder import MessageBuilder
from src.mqtt_publisher import MQTTPublisher
from src.utils import handle_processed_image
from src.zone_manager import ZoneManager

logger = None
watcher: Optional[FileWatcher] = None
mqtt_client: Optional[MQTTPublisher] = None


def signal_handler(signum, frame):
    """
    Gère les signaux de terminaison (SIGTERM, SIGINT).

    Args:
        signum: Numéro du signal
        frame: Frame courante
    """
    global watcher, mqtt_client

    logger.info(
        "Signal de terminaison reçu, arrêt de l'application",
        extra={"signal": signum},
    )

    # Arrêter le file watcher
    if watcher and watcher.is_running():
        logger.info("Arrêt du FileWatcher...")
        watcher.stop()

    # Déconnexion MQTT
    if mqtt_client:
        logger.info("Déconnexion MQTT...")
        mqtt_client.disconnect()

    logger.info("Application arrêtée proprement")
    sys.exit(0)


def extract_camera_name(filename: str) -> str:
    """
    Extrait le nom de la caméra depuis le nom du fichier.
    Format attendu : {camera}_{timestamp}.jpg

    Args:
        filename: Nom du fichier

    Returns:
        Nom de la caméra (ou 'generique' si non trouvé)
    """
    # Format: camera_2025-11-10_10-30-15.jpg
    parts = filename.split("_")
    if len(parts) >= 2:
        return parts[0]
    return "generique"


def process_image(
    image_path: Path,
    config,
    detector: Detector,
    mqtt_client: MQTTPublisher,
    message_builder: MessageBuilder,
) -> None:
    """
    Traite une image : détection, annotation, messages, publication MQTT.

    Args:
        image_path: Chemin de l'image
        config: Configuration globale
        detector: Instance du détecteur
        mqtt_client: Client MQTT
        message_builder: Constructeur de messages
    """
    try:
        # Extraire le nom de la caméra
        camera_name = extract_camera_name(image_path.name)

        logger.info(
            "Traitement image démarré",
            extra={
                "file": str(image_path),
                "camera": camera_name,
            },
        )

        # Trouver la config de la caméra
        camera_config = None
        for cam in config.cameras:
            if cam.name == camera_name:
                camera_config = cam
                break

        # Fallback sur caméra générique si non trouvée
        if camera_config is None:
            logger.warning(
                "Caméra non trouvée dans config, utilisation de 'generique'",
                extra={"camera_requested": camera_name},
            )
            for cam in config.cameras:
                if cam.name == "generique":
                    camera_config = cam
                    camera_name = "generique"
                    break

        if camera_config is None:
            logger.error("Aucune caméra 'generique' dans la config, abandon")
            return

        # 1. DÉTECTION YOLO + ZONES
        detections, counters = detector.detect(str(image_path), camera_config)

        logger.info(
            "Détection terminée",
            extra={
                "camera": camera_name,
                "total": counters["total"],
                "false": counters["false"],
                "by_class": counters["by_class"],
            },
        )

        # 2. ANNOTATION IMAGES
        annotator = ImageAnnotator(camera_config)
        output_dir = Path(config.directories.output)
        
        # Charger l'image pour obtenir ses dimensions (nécessaire pour ZoneManager)
        import cv2
        img = cv2.imread(str(image_path))
        image_height, image_width = img.shape[:2]

        # Créer les noms de fichiers de sortie
        timestamp = image_path.stem.split("_", 1)[1] if "_" in image_path.stem else "unknown"
        is_valid = counters["total"] - counters["false"] > 0

        # Déterminer le dossier de destination
        result_dir = "true" if is_valid else "false"
        if config.processing.output_structure.organize_by_result:
            if config.processing.output_structure.organize_by_camera:
                dest_dir = output_dir / result_dir / camera_name
            else:
                dest_dir = output_dir / result_dir
        else:
            if config.processing.output_structure.organize_by_camera:
                dest_dir = output_dir / camera_name
            else:
                dest_dir = output_dir

        dest_dir.mkdir(parents=True, exist_ok=True)

        # Image composite
        composite_path = dest_dir / f"composite_{timestamp}.jpg"
        annotator.annotate_composite(str(image_path), str(composite_path), detections)

        logger.info(
            "Image composite créée",
            extra={"path": str(composite_path)},
        )

        # Images par zone
        zone_images = {}
        if camera_config.zones:
            zone_manager = ZoneManager(camera_config.zones, image_width, image_height)
        
        for zone in camera_config.zones:
            zone_path = dest_dir / f"zone_{zone.name}_{timestamp}.jpg"
            zone_detections = [d for d in detections if zone.name in d.get("zones", [])]

            if annotator.annotate_zone(
                str(image_path), str(zone_path), zone.name, zone_detections, zone_manager
            ):
                zone_images[zone.name] = str(zone_path)
                logger.info(
                    "Image zone créée",
                    extra={
                        "zone": zone.name,
                        "path": str(zone_path),
                        "detections": len(zone_detections),
                    },
                )

        # 3. CONSTRUCTION MESSAGES
        # Message caméra global
        if camera_config.text_msg or camera_config.entity_ha:
            camera_msg = message_builder.build_camera_message(camera_config, counters)

            if camera_msg and camera_config.text_msg:
                # Publier notification caméra
                mqtt_client.publish_notification(
                    camera_name, None, camera_msg["message"], camera_msg.get("audio", False)
                )

        # Messages par zone
        for zone in camera_config.zones:
            if zone.text_msg or zone.entity_ha:
                # Récupérer les détections pour cette zone spécifique
                zone_detections = counters.get("by_zone", {}).get(zone.name, {})
                zone_msg = message_builder.build_zone_message(zone, counters, zone_detections)
                    

                if zone_msg and zone.text_msg:
                    # Publier notification zone
                    mqtt_client.publish_notification(
                        camera_name, zone.name, zone_msg["message"], zone_msg.get("audio", False)
                    )

        # 4. PUBLICATION MQTT SENSORS
        if camera_config.entity_ha:
            # Sensor détections totales
            mqtt_client.publish_sensor(
                camera_name, "detections", counters["total"] - counters["false"]
            )

            # Sensor fausses détections
            mqtt_client.publish_sensor(camera_name, "false_detections", counters["false"])

            # Sensors par zone et par classe
            for zone_name, zone_counters in counters.get("by_zone", {}).items():
                for obj_class, count in zone_counters.items():
                    mqtt_client.publish_sensor(
                        camera_name, f"zone_{zone_name}_{obj_class}", count
                    )

        # 5. PUBLICATION IMAGE METADATA
   #    mqtt_client.publish_image(camera_name, str(composite_path))

        # 6. GESTION FICHIER SOURCE
        handle_processed_image(
    str(image_path), 
    config.processing.input_action,
    str(config.directories.output)
)

        logger.info(
            "Traitement image terminé avec succès",
            extra={
                "file": str(image_path),
                "camera": camera_name,
                "detections": counters["total"] - counters["false"],
            },
        )

    except Exception as e:
        logger.error(
            "Erreur lors du traitement de l'image",
            extra={
                "file": str(image_path),
                "error": str(e),
            },
            exc_info=True,
        )


def main():
    """Fonction principale de l'application."""
    global logger, watcher, mqtt_client

    # 1. CHARGEMENT CONFIGURATION
    try:
        config = load_config("config/config.yaml")
    except Exception as e:
        print(f"❌ Erreur chargement configuration : {e}")
        sys.exit(1)

    # 2. CONFIGURATION LOGGER
    logger = setup_logger(config.logging.level, config.logging.format)
    logger.info(
        "Application démarrée",
        extra={
            "app": config.app.name,
            "version": config.app.version,
        },
    )

    # 3. VÉRIFICATION RÉPERTOIRES
    input_dir = Path(config.directories.input)
    output_dir = Path(config.directories.output)

    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info(
        "Répertoires configurés",
        extra={
            "input": str(input_dir),
            "output": str(output_dir),
        },
    )

    # 4. INITIALISATION MQTT
    try:
        mqtt_client = MQTTPublisher(config)
        mqtt_client.connect()
        
        # Note: L'autodiscovery Home Assistant se fera automatiquement
        # lors de la première publication de chaque sensor
        
        logger.info("Connexion MQTT établie")

    except Exception as e:
        logger.error(f"Erreur connexion MQTT : {e}", exc_info=True)
        sys.exit(1)

    # 5. INITIALISATION DÉTECTEUR YOLO
    try:
        detector = Detector(
            config.detection.model, confidence_threshold=config.detection.confidence_threshold
        )
        logger.info(
            "Détecteur YOLO initialisé",
            extra={"model": config.detection.model},
        )
    except Exception as e:
        logger.error(f"Erreur initialisation détecteur : {e}", exc_info=True)
        mqtt_client.disconnect()
        sys.exit(1)

    # 6. INITIALISATION MESSAGE BUILDER
    message_builder = MessageBuilder()

    # 7. CONFIGURATION GESTION SIGNAUX
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # 8. CRÉATION FILE WATCHER
    def on_new_file(file_path: Path):
        """Callback appelé lors de la détection d'un nouveau fichier."""
        process_image(file_path, config, detector, mqtt_client, message_builder)

    watcher = FileWatcher(input_dir, callback=on_new_file, extensions=(".jpg", ".jpeg"))

    # 9. TRAITEMENT FICHIERS EXISTANTS (optionnel)
    logger.info("Traitement des fichiers existants dans shared_in...")
    watcher.process_existing_files()

    # 10. DÉMARRAGE SURVEILLANCE
    watcher.start()
    logger.info(
        "Surveillance active, en attente de nouveaux fichiers...",
        extra={"directory": str(input_dir)},
    )

    # 11. BOUCLE PRINCIPALE
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)


if __name__ == "__main__":
    main()