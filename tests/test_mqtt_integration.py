"""
Test d'intégration MQTT avec un broker réel.
IMPORTANT: Ce test nécessite un broker MQTT actif sur 10.0.0.3:1883
"""

from src.config_loader import load_config
from src.mqtt_publisher import MQTTPublisher


def test_mqtt_integration():
    """Test complet de l'intégration MQTT."""
    
    print("\n" + "=" * 80)
    print("🔌 TEST D'INTÉGRATION MQTT")
    print("=" * 80 + "\n")
    
    # Charger la configuration
    config = load_config("config/config.yaml")
    print(f"✅ Configuration chargée")
    print(f"   📡 Broker: {config.mqtt.broker}:{config.mqtt.port}")
    print(f"   🔑 Username: {config.mqtt.username or '(non défini)'}")
    print(f"   🏠 Autodiscovery HA: {config.homeassistant.autodiscovery}\n")
    
    # Créer le publisher
    publisher = MQTTPublisher(config)
    
    # Tester la connexion
    print("🔌 Connexion au broker MQTT...")
    if not publisher.connect():
        print("❌ Échec de connexion au broker MQTT")
        print("   Vérifiez que le broker est accessible sur", config.mqtt.broker)
        return False
    
    print("✅ Connecté au broker MQTT\n")
    
    # Envoyer l'autodiscovery pour chaque caméra
    print("📢 Envoi de l'autodiscovery Home Assistant...")
    for camera in config.cameras:
        if camera.name != "generique":  # Skip la caméra générique
            success = publisher.send_autodiscovery(camera)
            if success:
                print(f"   ✅ Autodiscovery envoyé pour: {camera.name}")
            else:
                print(f"   ❌ Échec autodiscovery pour: {camera.name}")
    
    print()
    
    # Test de publication de sensors
    print("📊 Test de publication de sensors...")
    test_data = [
        ("reolink", "detections", 5),
        ("reolink", "false_detections", 1),
        ("ptz", "detections", 2),
        ("ptz", "false_detections", 0),
    ]
    
    for camera, metric, value in test_data:
        if any(cam.name == camera for cam in config.cameras if cam.name != "generique"):
            success = publisher.publish_sensor(camera, metric, value)
            if success:
                print(f"   ✅ Sensor publié: {camera}/{metric} = {value}")
            else:
                print(f"   ❌ Échec sensor: {camera}/{metric}")
    
    print()
    
    # Test de publication de notifications
    print("📬 Test de publication de notifications...")
    notifications = [
        ("reolink", "route", "2 voiture(s) détectée(s) sur la route", True, {"car": 2}),
        ("reolink", None, "Activité détectée", False, None),
        ("ptz", None, "1 personne détectée", True, {"person": 1}),
    ]
    
    for camera, zone, message, audio, detections in notifications:
        if any(cam.name == camera for cam in config.cameras if cam.name != "generique"):
            success = publisher.publish_notification(camera, zone, message, audio, detections)
            if success:
                zone_str = f" (zone: {zone})" if zone else ""
                audio_str = " 🔊" if audio else ""
                print(f"   ✅ Notification publiée: {camera}{zone_str}{audio_str}")
            else:
                print(f"   ❌ Échec notification: {camera}")
    
    print()
    
    # Test de publication de métadonnées image
    print("🖼️  Test de publication de métadonnées image...")
    image_tests = [
        ("reolink", "reolink_test.jpg", "shared_out/true/reolink/reolink_test.jpg", ["route", "cour"], 3),
        ("ptz", "ptz_test.jpg", "shared_out/true/ptz/ptz_test.jpg", [], 1),
    ]
    
    for camera, filename, path, zones, total in image_tests:
        if any(cam.name == camera for cam in config.cameras if cam.name != "generique"):
            success = publisher.publish_image_metadata(camera, filename, path, zones, total)
            if success:
                print(f"   ✅ Métadonnées publiées: {filename}")
            else:
                print(f"   ❌ Échec métadonnées: {filename}")
    
    print()
    
    # Déconnexion
    print("🔌 Déconnexion du broker...")
    publisher.disconnect()
    print("✅ Déconnecté\n")
    
    print("=" * 80)
    print("✅ Test d'intégration MQTT terminé")
    print("=" * 80)
    print("\n💡 Vérifiez dans Home Assistant que les entités apparaissent:")
    print("   - sensor.reolink_detections_totales")
    print("   - sensor.reolink_fausses_alertes")
    print("   - sensor.ptz_detections_totales")
    print("   - etc.\n")
    



if __name__ == "__main__":
    test_mqtt_integration()