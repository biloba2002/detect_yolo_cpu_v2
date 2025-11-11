# Kanban — vision_yolo_zones

## Feature

### MVP (Must Have)

  - priority: high
  - defaultExpanded: false
  - steps:
      - [x] Config YAML centralisé (caméras, zones, MQTT, HA)
      - [x] Détection YOLO CPU multi-objets
      - [x] Filtrage par zones (polygones Frigate)
      - [x] Caméra générique (fallback)
      - [x] Compteurs HA par caméra et par zone
      - [ ] Messages texte personnalisés (MQTT)
      - [ ] Images annotées (objets + zones)
      - [ ] HA autodiscovery (sensors, counters)
      - [ ] Docker Compose avec volumes
      - [ ] Logs structurés (niveaux debug/info/warning/error)

### Nice-to-Have (Phase 2)

  - priority: high
  - defaultExpanded: false
  - steps:
      - [ ] Messages audio (TTS intégré ou URL)
      - [ ] API REST (stats, pilotage)
      - [ ] Persistance historique (SQLite)
      - [ ] Interface Web (dashboard)
      - [ ] Multi-threading avancé (pool workers)
      - [ ] Scan sécurité CI (Trivy)
      - [ ] Tests unitaires exhaustifs (coverage ≥80%)

## TODO

### LOT 6 : Docker & Déploiement

  - priority: medium
  - defaultExpanded: false
    ```md
    Objectif : Containerisation production-ready
    Charge : ⭐⭐ (2/5) | Risque : 🟢 Faible
    Tâches :
    
    Créer Dockerfile multi-stage :
    
    Base : python:3.11-slim-bookworm
    User non-root (appuser)
    Installation deps avec uv
    Healthcheck (vérifier logs récents)
    
    
    Créer docker-compose.yml :
    
    Volumes : config/, shared_in/, shared_out/
    Env vars depuis .env
    Restart policy : unless-stopped
    Network bridge
    
    
    Écrire .dockerignore
    Compléter README.md (build, run, troubleshooting)
    
    Livrables :
    
    ✅ Image Docker < 500MB
    ✅ Compose fonctionnel
    ✅ Documentation complète
    ```

## Doing

### LOT 5 : Watchdog & Orchestration

  - priority: medium
  - defaultExpanded: false
    ```md
    Objectif : Monitoring fichiers + pipeline complet
    Charge : ⭐⭐⭐ (3/5) | Risque : 🟢 Faible
    Tâches :
    
    Implémenter file_watcher.py :
    
    Observer shared_in/ (watchdog)
    Debounce 2s (éviter flood)
    Extraire nom caméra depuis filename
    Déplacer image traitée vers shared_out/
    
    
    Implémenter main.py :
    
    Charger config au démarrage
    Initialiser MQTT (autodiscovery)
    Lancer watchdog
    Orchestrer pipeline : détection → annotation → publication
    
    
    Gestion erreurs et logs contextuels
    
    Livrables :
    
    ✅ Pipeline end-to-end fonctionnel
    ✅ Logs détaillés (debug/info/warning/error)
    ```

## Done

### LOT 1 : Fondations (Squelette + Config)

  - defaultExpanded: false
    ```md
    Objectif : Projet fonctionnel avec configuration validée
    Charge : ⭐⭐ (2/5) | Risque : 🟢 Faible
    Tâches :
    
    Initialiser projet uv avec pyproject.toml
    Créer config.sample.yaml complet (3 caméras, zones)
    Implémenter config_loader.py avec Pydantic models
    Configurer logger.py (structlog, niveaux)
    Créer .env.sample (MQTT credentials)
    Écrire README.md initial (installation, config)
    
    Livrables :
    
    ✅ Config YAML validée et chargeable
    ✅ Logs structurés fonctionnels
    ✅ Documentation setup
    ```

### LOT 2 : Détection & Zones (Cœur métier)

  - defaultExpanded: false
    ```md
    Objectif : Détection YOLO + filtrage polygones opérationnels
    Charge : ⭐⭐⭐⭐ (4/5) | Risque : 🟡 Moyen (performance CPU)
    Tâches :
    
    Implémenter detector.py (YOLO11n, seuil confidence)
    Implémenter zone_manager.py (Shapely, point-in-polygon)
    Créer fonction de mapping caméra depuis filename
    Gérer fallback caméra générique
    Calculer compteurs (total, par type, par zone, fausses détections)
    
    Livrables :
    
    ✅ Détection d'objets avec scores
    ✅ Filtrage par zones précis
    ✅ Compteurs JSON structurés
    ```

### LOT 3 : Génération Outputs (Images + Messages)

  - defaultExpanded: false
    ```md
    Objectif : Images annotées + messages personnalisés
    Charge : ⭐⭐⭐ (3/5) | Risque : 🟢 Faible
    Tâches :
    
    Implémenter image_annotator.py :
    
    Dessiner polygones zones (contours colorés)
    Dessiner bbox objets + labels
    Générer image composite caméra
    Générer images par zone
    
    
    Implémenter message_builder.py :
    
    Templates de messages (config msg_template)
    Remplacement variables {count_person}, etc.
    Marqueur audio: true/false
    
    
    
    Livrables :
    
    ✅ Images annotées dans shared_out/
    ✅ Messages texte personnalisés
    ```

### LOT 4 : MQTT & Home Assistant

  - defaultExpanded: false
    ```md
    Objectif : Publication MQTT + autodiscovery HA
    Charge : ⭐⭐⭐⭐ (4/5) | Risque : 🟡 Moyen (reconnexion)
    Tâches :
    
    Implémenter mqtt_publisher.py :
    
    Connexion broker avec credentials
    Gestion reconnexion automatique
    Publication sensors (compteurs)
    Publication notify (messages)
    Publication images (metadata)
    
    
    Générer payloads autodiscovery HA :
    
    Sensors par caméra (total, fausses détections)
    Sensors par zone et par type d'objet
    Device grouping par caméra
    
    
    Tester QoS 1, retain=false
    
    Livrables :
    
    ✅ Entités HA créées automatiquement
    ✅ Compteurs mis à jour en temps réel
    ✅ Messages notify visibles dans HA
    ```

