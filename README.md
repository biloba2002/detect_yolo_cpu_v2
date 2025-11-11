# Detect YOLO CPU v2

Application de détection d'objets avec YOLO (CPU) pour caméras de surveillance, avec support des zones de détection et intégration Home Assistant via MQTT.

## 🎯 Fonctionnalités

- ✅ Détection d'objets avec YOLOv11n (CPU optimisé)
- ✅ Support multi-caméras avec configuration individuelle
- ✅ Zones de détection personnalisables (polygones)
- ✅ Intégration Home Assistant (autodiscovery MQTT)
- ✅ Compteurs par caméra et par zone
- ✅ Messages texte/audio personnalisés
- ✅ Images annotées (zones + objets détectés)
- ✅ Logs structurés JSON
- ✅ Déploiement Docker

## 📋 Prérequis

- Docker & Docker Compose
- Broker MQTT (ex: Mosquitto)
- Home Assistant (optionnel)
- Images au format JPEG

## 🚀 Installation

### 1. Cloner le projet

```bash
git clone https://gitea.maison43.duckdns.org/gilles/detect_yolo_cpu_v2.git
cd detect_yolo_cpu_v2
```

### 2. Configurer l'environnement

```bash
# Copier le template de configuration
cp config/config.sample.yaml config/config.yaml
cp .env.sample .env

# Éditer la configuration
nano config/config.yaml  # Adapter les caméras, zones, MQTT
nano .env                # Renseigner les credentials MQTT
```

### 3. Adapter la configuration

Éditez `config/config.yaml` pour :
- Définir vos caméras (noms, objets à détecter)
- Configurer les zones avec les polygones Frigate
- Personnaliser les messages de notification
- Ajuster les paramètres MQTT et Home Assistant

### 4. Lancer l'application

```bash
docker compose up -d
```

## 📁 Structure du projet

```
detect_yolo_cpu_v2/
├── config/
│   ├── config.yaml           # Configuration principale
│   └── config.sample.yaml    # Template de configuration
├── src/
│   ├── main.py              # Point d'entrée
│   ├── config_loader.py     # Chargement config
│   ├── detector.py          # Moteur de détection
│   ├── zone_manager.py      # Gestion des zones
│   ├── file_watcher.py      # Surveillance fichiers
│   ├── mqtt_publisher.py    # Publication MQTT
│   ├── image_annotator.py   # Annotation d'images
│   ├── message_builder.py   # Construction messages
│   └── logger.py            # Configuration logs
├── shared_in/               # Dossier images entrantes
├── shared_out/              # Dossier images traitées
├── docker-compose.yml
├── Dockerfile
└── README.md
```

## 🔧 Configuration

### Format des noms de fichiers

Les images doivent être nommées : `{camera_name}_{timestamp}.jpg`

Exemples :
- `reolink_2025-11-10_10-30-15.jpg`
- `ptz_2025-11-10_14-22-05.jpg`

Si le nom de caméra n'est pas trouvé dans la config, la caméra `generique` sera utilisée.

### Zones de détection

Les coordonnées des polygones sont normalisées (valeurs entre 0 et 1) :
- `0,0` = coin supérieur gauche
- `1,1` = coin inférieur droit

Format : `[x1, y1, x2, y2, x3, y3, ...]` (minimum 3 points)

### Topics MQTT

**Sensors (compteurs)** :
```
detect_yolo_cpu_v2/sensor/{camera}/detections
detect_yolo_cpu_v2/sensor/{camera}/false_detections
detect_yolo_cpu_v2/sensor/{camera}/zone/{zone_name}/{object_type}
```

**Notifications** :
```
detect_yolo_cpu_v2/notify/{camera}/{zone_name}
```

**Images** :
```
detect_yolo_cpu_v2/image/{camera}
```

## 🏠 Intégration Home Assistant

L'autodiscovery MQTT crée automatiquement :
- **Sensors** : compteurs de détections par caméra et zone
- **Counters** : nombre de détections par type d'objet
- **Images** : métadonnées des images annotées

Les entités apparaissent dans Home Assistant sous :
```
sensor.reolink_detections_totales
sensor.reolink_zone_route_person
sensor.ptz_detections_totales
...
```

## 📊 Logs

Les logs sont structurés en JSON et disponibles via :

```bash
# Voir les logs en temps réel
docker compose logs -f app

# Logs des 100 dernières lignes
docker compose logs --tail=100 app
```

Niveaux de log (dans `config.yaml`) :
- `debug` : Détails de développement
- `info` : Flux normal (défaut)
- `warning` : Anomalies récupérables
- `error` : Échecs critiques

## 🧪 Tests

```bash
# Installer les dépendances de dev
uv sync --dev

# Lancer les tests
uv run pytest

# Avec coverage
uv run pytest --cov=src --cov-report=html
```

## 🛠️ Développement

### Installation locale

```bash
# Installer uv (gestionnaire de paquets ultra-rapide)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Installer les dépendances
uv sync

# Activer l'environnement
source .venv/bin/activate
```

### Commandes utiles

```bash
# Linter
uv run ruff check src/

# Formattage
uv run black src/

# Type checking
uv run mypy src/
```

## 🐛 Troubleshooting

### L'application ne démarre pas

1. Vérifier les logs : `docker compose logs app`
2. Vérifier la config : `docker compose exec app cat /app/config/config.yaml`
3. Vérifier les volumes : `docker compose exec app ls -la /app/shared_in`

### Pas de détections

1. Vérifier le format des noms de fichiers
2. Vérifier les permissions des dossiers `shared_in` et `shared_out`
3. Vérifier le seuil de confiance dans `config.yaml` (par défaut 0.5)

### Pas d'entités dans Home Assistant

1. Vérifier la connexion MQTT : `docker compose logs app | grep mqtt`
2. Vérifier l'autodiscovery HA dans `config.yaml`
3. Redémarrer Home Assistant

## 📝 Licence

Projet personnel - Usage libre

## 👤 Auteur

Gilles - [gitea.maison43.duckdns.org](https://gitea.maison43.duckdns.org/gilles)

## 📅 Version

**v2.0.0** - Novembre 2025