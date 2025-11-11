# LOT 2 : Détection & Zones - Instructions de test

## 📦 Fichiers créés

- ✅ `src/zone_manager.py` - Gestionnaire de zones avec Shapely
- ✅ `src/detector.py` - Moteur de détection YOLO
- ✅ `tests/test_zone_manager.py` - Tests unitaires zones
- ✅ `tests/test_detector.py` - Tests unitaires détecteur

## 🧪 Lancer les tests

### Tests du gestionnaire de zones (complets)

```bash
uv run pytest tests/test_zone_manager.py -v
```

**Résultat attendu** : Tous les tests passent (16 tests)

### Tests du détecteur (partiels)

```bash
uv run pytest tests/test_detector.py -v
```

**Note** : Les tests complets nécessitent :
1. Le modèle YOLO (`yolov11n.pt`)
2. Une image de test

## 📥 Télécharger le modèle YOLO

Le modèle sera téléchargé automatiquement au premier run, mais vous pouvez le faire manuellement :

```bash
# Créer un script de test rapide
cat > test_yolo_download.py << 'EOF'
from ultralytics import YOLO

# Télécharge automatiquement yolov11n.pt
model = YOLO("yolov11n.pt")
print("✅ Modèle YOLO téléchargé avec succès!")
EOF

# Exécuter
uv run python test_yolo_download.py
```

## 🖼️ Créer une image de test

```bash
# Utiliser Python pour créer une image de test simple
cat > create_test_image.py << 'EOF'
import cv2
import numpy as np

# Créer une image de test 1000x1000 avec un rectangle
img = np.zeros((1000, 1000, 3), dtype=np.uint8)
img[:] = (240, 240, 240)  # Fond gris clair

# Dessiner un rectangle (simuler un objet)
cv2.rectangle(img, (400, 200), (600, 400), (0, 0, 255), -1)

# Sauvegarder
cv2.imwrite("tests/fixtures/test_image.jpg", img)
print("✅ Image de test créée: tests/fixtures/test_image.jpg")
EOF

uv run python create_test_image.py
```

## 🔬 Test d'intégration complet

Une fois le modèle téléchargé et l'image créée :

```bash
cat > test_full_detection.py << 'EOF'
from src.detector import Detector
from src.config_loader import CameraConfig, ZoneConfig

# Config de test
camera_config = CameraConfig(
    name="test",
    detect=["person", "car", "dog", "cat", "bicycle", "truck"],
    zones=[
        ZoneConfig(
            name="full_image",
            polygon=[0.0, 0.0, 1.0, 0.0, 1.0, 1.0, 0.0, 1.0]
        )
    ]
)

# Détection
detector = Detector("yolov11n.pt", confidence_threshold=0.5)
detections, counters = detector.detect("tests/fixtures/test_image.jpg", camera_config)

print(f"✅ Détections: {len(detections)}")
print(f"📊 Compteurs: {counters}")
EOF

uv run python test_full_detection.py
```

## ✅ Validation LOT 2

Une fois tous les tests passés :

```bash
# Lancer tous les tests
uv run pytest tests/ -v

# Avec coverage
uv run pytest tests/ --cov=src --cov-report=term-missing
```

**Critères de validation** :
- ✅ Tests `test_zone_manager.py` : 100% passent
- ✅ Tests `test_detector.py` : Passent (même partiels)
- ✅ Coverage `zone_manager.py` : > 80%
- ✅ Coverage `detector.py` : > 70%

## 🎯 Prochaine étape

Commande à taper : **`OK:LOT-2`** pour passer au LOT 3 (Images annotées & Messages)