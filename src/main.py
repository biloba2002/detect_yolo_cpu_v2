"""
Point d'entrée principal de l'application detect_yolo_cpu_v2.
Orchestre configuration, détection, annotation, MQTT.
"""

import os
os.environ["CUDA_VISIBLE_DEVICES"] = ""
os.environ["ULTRALYTICS_FORCE_CPU"] = "1"

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
    global watcher, mqtt_client
    logger.info("Signal de terminaison reçu, arrêt de l'application", extra={"signal": signum})
    if watcher and watcher.is_running():
        logger.info("Arrêt du FileWatcher...")
        watcher.stop()
    if mqtt_client:
        logger.info("Déconnexion MQTT...")
        mqtt_client.disconnect()
    logger.info("Application arrêtée proprement")
    sys.exit(0)


def extract_camera_name(filename: str) -> str:
    parts = filename.split("_")
    return parts[0] if len(parts) >= 2 else "generique"


def process_image(
    image_path: Path,
    config,
    detector: Detector,
    mqtt_client: MQTTPublisher,
    message_builder: MessageBuilder,
) -> None:
    try:
        camera_name = extract_camera_name(image_path.name)

        logger.info("Traitement image démarré", extra={"file": str(image_path), "camera": camera_name})

        # Config caméra ou fallback "generique"
        camera_config = next((c for c in config.cameras if c.name == camera_name), None)
        if camera_config is None:
            logger.warning("Caméra non trouvée, utilisation de 'generique'", extra={"camera_requested": camera_name})
            camera_config = next((c for c in config.cameras if c.name == "generique"), None)
            camera_name = "generique" if camera_config else camera_name
        if camera_config is None:
            logger.error("Aucune caméra 'generique' dans la config, abandon")
            return

        # 1) Détection
        detections, counters = detector.detect(str(image_path), camera_config)
        logger.info(
            "Détection terminée",
            extra={"camera": camera_name, "total": counters["total"], "false": counters["false"], "by_class": counters["by_class"]},
        )

        # 2) Annotation – composite unique avec zones
        annotator = ImageAnnotator(camera_config)
        from cv2 import imread
        img = imread(str(image_path))
        if img is None:
            raise RuntimeError(f"Impossible de lire l'image: {image_path}")
        image_h, image_w = img.shape[:2]
        zone_manager = ZoneManager(camera_config.zones, image_w, image_h) if camera_config.zones else None

        # Répertoire de sortie
        output_dir = Path(config.directories.output)
        original_filename = image_path.name  # Conserve le nom original complet
        is_valid = (counters["total"] - counters["false"]) > 0
        result_dir = "true" if is_valid else "false"
        if config.processing.output_structure.organize_by_result:
            dest_dir = (output_dir / result_dir / camera_name) if config.processing.output_structure.organize_by_camera else (output_dir / result_dir)
        else:
            dest_dir = (output_dir / camera_name) if config.processing.output_structure.organize_by_camera else output_dir
        dest_dir.mkdir(parents=True, exist_ok=True)

        composite_path = dest_dir / original_filename  # Utilise le nom original
        annotator.annotate_composite(str(image_path), str(composite_path), detections, zone_manager)
        logger.info("Image composite créée", extra={"path": str(composite_path)})

        # 3) NOTIFICATIONS
        # Map: zone_name -> liste de détections VALIDE (is_false=False) appartenant à la zone
        zone_detections_map = {}
        for d in detections:
            if d.get("is_false"):
                continue
            for zname in d.get("zones", []):
                zone_detections_map.setdefault(zname, []).append(d)

        # Zones qui ont au moins une détection valide
        zones_with_dets = [z for z in camera_config.zones if zone_detections_map.get(z.name)]
        # Au moins une zone autorise une notif ?
        has_zone_notify = any((z.text_msg or z.audio_msg) for z in zones_with_dets)

        # 3.1 Notifications ZONE (uniquement celles autorisées)
        for z in zones_with_dets:
            if z.text_msg or z.audio_msg:
                z_dets = zone_detections_map.get(z.name, [])
                zone_msg = message_builder.build_zone_message(z, counters, z_dets)
                if zone_msg and z.text_msg:
                    mqtt_client.publish_notification(
                        camera_name, z.name, zone_msg["message"], zone_msg.get("audio", False)
                    )

        # 3.2 Notification CAMÉRA
        # Règle: aucune notif caméra si des zones ont des détections mais qu'aucune n'autorise message/audio
        send_camera_msg = False
        if not camera_config.zones:
            send_camera_msg = True
        elif zones_with_dets and has_zone_notify:
            send_camera_msg = False
        elif zones_with_dets and not has_zone_notify:
            send_camera_msg = False
        else:
            send_camera_msg = False

        if send_camera_msg and camera_config.text_msg:
            camera_msg = message_builder.build_camera_message(camera_config, counters)
            if camera_msg:
                mqtt_client.publish_notification(
                    camera_name, None, camera_msg["message"], camera_msg.get("audio", False)
                )

        # 4) Capteurs MQTT
        if camera_config.entity_ha:
            if camera_config.zones:
                det_sum = sum(v.get("total", 0) for v in counters.get("by_zone", {}).values())
            else:
                det_sum = counters["total"] - counters["false"]
            mqtt_client.publish_sensor(camera_name, "detections", det_sum)
            mqtt_client.publish_sensor(camera_name, "false_detections", counters["false"])

            # Publie les compteurs par zone
            for zone_key, zc in counters.get("by_zone", {}).items():
                zname = zone_key.split("zone_", 1)[1] if zone_key.startswith("zone_") else zone_key
                mqtt_client.publish_sensor(camera_name, f"zone_zone_{zname}_total", zc.get("total", 0))
                mqtt_client.publish_sensor(camera_name, f"zone_zone_{zname}_by_class", zc.get("by_class", {}))

        # 5) Post-traitement de la source
        handle_processed_image(
            str(image_path),
            config.processing.input_action,
            str(config.directories.output),
            save_original=bool(config.processing.output_structure.save_original),
            original_by_camera=bool(config.processing.output_structure.original_by_camera),
            camera=camera_name,
        )

        logger.info(
            "Traitement image terminé avec succès",
            extra={
                "file": str(image_path),
                "camera": camera_name,
                "detections": det_sum if camera_config.zones else (counters["total"] - counters["false"]),
            },
        )

    except Exception as e:
        logger.error("Erreur lors du traitement de l'image", extra={"file": str(image_path), "error": str(e)}, exc_info=True)


def main():
    global logger, watcher, mqtt_client
    try:
        config = load_config("config/config.yaml")
    except Exception as e:
        print(f"❌ Erreur chargement configuration : {e}")
        sys.exit(1)

    logger = setup_logger(config.logging.level, config.logging.format)
    logger.info("Application démarrée", extra={"app": config.app.name, "version": config.app.version})

    input_dir = Path(config.directories.input)
    output_dir = Path(config.directories.output)
    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Répertoires configurés", extra={"input": str(input_dir), "output": str(output_dir)})

    try:
        mqtt_client = MQTTPublisher(config)
        mqtt_client.connect()
        logger.info("Connexion MQTT établie")
    except Exception as e:
        logger.error(f"Erreur connexion MQTT : {e}", exc_info=True)
        sys.exit(1)

    try:
        detector = Detector(config.detection.model, confidence_threshold=config.detection.confidence_threshold)
        logger.info("Détecteur YOLO initialisé", extra={"model": config.detection.model})
    except Exception as e:
        logger.error(f"Erreur initialisation détecteur : {e}", exc_info=True)
        mqtt_client.disconnect()
        sys.exit(1)

    message_builder = MessageBuilder()

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    def on_new_file(file_path: Path):
        process_image(file_path, config, detector, mqtt_client, message_builder)

    watcher = FileWatcher(input_dir, callback=on_new_file, extensions=(".jpg", ".jpeg"))

    logger.info("Traitement des fichiers existants dans shared_in...")
    watcher.process_existing_files()

    watcher.start()
    logger.info("Surveillance active, en attente de nouveaux fichiers...", extra={"directory": str(input_dir)})

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)


if __name__ == "__main__":
    main()