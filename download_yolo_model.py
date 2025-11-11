from ultralytics import YOLO

print("📥 Téléchargement du modèle YOLOv11n...")
print("   Taille: ~6 MB")
print("   Peut prendre 1-2 minutes selon votre connexion...\n")

# Cela télécharge automatiquement le modèle
model = YOLO("yolo11n.pt")

print("\n✅ Modèle téléchargé avec succès!")
print(f"📁 Emplacement: {model.ckpt_path}")
