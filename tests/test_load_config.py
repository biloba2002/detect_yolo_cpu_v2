from src.config_loader import load_config

try:
    # Charger la config
    config = load_config("config/config.yaml")
    
    print("✅ Config chargée avec succès!")
    print(f"📷 Caméras trouvées: {[cam.name for cam in config.cameras]}")
    print(f"🔧 Niveau de log: {config.logging.level}")
    print(f"📡 Broker MQTT: {config.mqtt.broker}:{config.mqtt.port}")
    
    # Tester fallback caméra générique
    cam = config.get_camera_config("unknown_camera")
    print(f"🔄 Fallback caméra: {cam.name}")
    
except FileNotFoundError as e:
    print(f"❌ Fichier non trouvé: {e}")
    print("💡 Créez-le avec: cp config/config.sample.yaml config/config.yaml")
    
except Exception as e:
    print(f"❌ Erreur de chargement: {e}")