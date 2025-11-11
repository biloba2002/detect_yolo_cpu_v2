"""
Test de détection en batch sur toutes les images de shared_in/.
Ce test analyse chaque image et génère un rapport complet.
"""

import os
os.environ['CUDA_VISIBLE_DEVICES'] = ''  # ← Forcer CPU avant imports
import cv2
from pathlib import Path
from src.config_loader import load_config, extract_camera_name
from src.detector import Detector
from src.image_annotator import ImageAnnotator
from src.zone_manager import ZoneManager
from src.utils import list_images, handle_processed_image, get_output_path, save_original_image


def test_batch_detection():
    """Test de détection sur toutes les images du dossier shared_in."""
    
    print("\n" + "=" * 80)
    print("🎬 TEST DE DÉTECTION EN BATCH")
    print("=" * 80 + "\n")
    
    # Charger la config
    config = load_config("config/config.yaml")
    print(f"✅ Configuration chargée")
    print(f"   📁 Input: {config.directories.input}")
    print(f"   📁 Output: {config.directories.output}")
    print(f"   🎛️  Action après traitement: {config.processing.input_action}")
    print(f"   📂 Organisation par résultat (true/false): {config.processing.output_structure.organize_by_result}")
    print(f"   📂 Organisation par caméra: {config.processing.output_structure.organize_by_camera}")
    print(f"   💾 Sauvegarde originaux: {config.processing.output_structure.save_original}\n")
    
    # Lister toutes les images
    images = list_images(str(config.directories.input))
    
    if not images:
        print("⚠️  Aucune image trouvée dans shared_in/")
        print("   Ajoutez des images .jpg, .jpeg ou .png pour tester\n")
        return
    
    print(f"📸 {len(images)} image(s) trouvée(s):")
    for img in images:
        print(f"   - {os.path.basename(img)}")
    print()
    
    # Initialiser le détecteur
    print("📥 Chargement du modèle YOLO...")
    detector = Detector(
        model_path=config.detection.model,
        confidence_threshold=config.detection.confidence_threshold
    )
    print(f"✅ Modèle chargé (seuil: {config.detection.confidence_threshold})\n")
    
    # Traiter chaque image
    results = []
    
    for idx, image_path in enumerate(images, 1):
        filename = os.path.basename(image_path)
        
        print("─" * 80)
        print(f"🔬 [{idx}/{len(images)}] Traitement: {filename}")
        print("─" * 80)
        
        # Extraire le nom de la caméra
        camera_name = extract_camera_name(filename)
        camera_config = config.get_camera_config(camera_name)
        
        print(f"📷 Caméra détectée: {camera_name}")
        if camera_config.zones:
            print(f"🗺️  Zones actives: {', '.join([z.name for z in camera_config.zones])}")
        else:
            print(f"🗺️  Aucune zone configurée")
        
        # 1. Sauvegarder l'original si demandé
        if config.processing.output_structure.save_original:
            original_saved = save_original_image(
                image_path,
                str(config.directories.output),
                camera_name,
                config.processing.output_structure.original_by_camera
            )
            if original_saved:
                org_path = f"original/{camera_name}/" if config.processing.output_structure.original_by_camera else "original/"
                print(f"💾 Original sauvegardé: {org_path}{filename}")
        
        # 2. Détecter les objets
        detections, counters = detector.detect(image_path, camera_config)
        
        valid = counters['total'] - counters['false']
        has_valid_detections = valid > 0
        
        # Afficher les résultats
        print(f"\n📊 RÉSULTATS:")
        print(f"   Total détections: {counters['total']}")
        print(f"   ✅ Détections valides: {valid}")
        print(f"   ❌ Fausses détections: {counters['false']}")
        
        if counters['by_class']:
            print(f"\n   📈 Par classe:")
            for cls, count in counters['by_class'].items():
                print(f"      • {cls}: {count}")
        
        if counters['by_zone']:
            print(f"\n   🗺️  Par zone:")
            for zone_key, zone_data in counters['by_zone'].items():
                zone_name = zone_key.replace('zone_', '')
                print(f"      • {zone_name}: {zone_data['total']} détection(s)")
                for cls, count in zone_data['by_class'].items():
                    print(f"         - {cls}: {count}")
        
        # 3. Créer l'image annotée avec la structure organisée
        annotated_path = get_output_path(
            str(config.directories.output),
            filename,
            camera_name,
            has_valid_detections,
            config.processing.output_structure.organize_by_result,
            config.processing.output_structure.organize_by_camera
        )
        
        annotator = ImageAnnotator(camera_config)
        
        zone_manager = None
        if camera_config.zones:
            img = cv2.imread(image_path)
            if img is not None:
                height, width = img.shape[:2]
                zone_manager = ZoneManager(camera_config.zones, width, height)
        
        success = annotator.annotate_composite(
            image_path,
            annotated_path,
            detections,
            zone_manager
        )
        
        if success:
            # Afficher le chemin relatif pour plus de clarté
            rel_path = os.path.relpath(annotated_path, str(config.directories.output))
            result_type = "✅ true" if has_valid_detections else "❌ false"
            print(f"\n   {result_type} Image annotée: {rel_path}")
        else:
            print(f"\n   ⚠️  Échec création image annotée")
        
        # 4. Gérer l'image source selon la config
        # Si save_original=true, on utilise 'erase' pour éviter les doublons
        actual_action = config.processing.input_action
        if config.processing.output_structure.save_original and actual_action == "move":
            actual_action = "erase"  # L'original est déjà sauvegardé, on supprime la source
        
        if actual_action != "none":
            handle_success = handle_processed_image(
                image_path,
                actual_action,
                str(config.directories.output)
            )
            if handle_success:
                action_msg = {
                    "move": "déplacée",
                    "erase": "supprimée",
                    "none": "conservée"
                }
                print(f"   🗂️  Image source {action_msg[actual_action]}")
        
        print()
        
        # Stocker les résultats
        results.append({
            'filename': filename,
            'camera': camera_name,
            'total': counters['total'],
            'valid': valid,
            'false': counters['false'],
            'by_class': counters['by_class'],
            'by_zone': counters['by_zone'],
            'has_valid': has_valid_detections
        })
    
    # Résumé global
    print("=" * 80)
    print("📊 RÉSUMÉ GLOBAL")
    print("=" * 80 + "\n")
    
    total_images = len(results)
    total_valid = sum(r['valid'] for r in results)
    total_false = sum(r['false'] for r in results)
    images_with_detections = sum(1 for r in results if r['has_valid'])
    images_without_detections = total_images - images_with_detections
    
    print(f"📸 Images traitées: {total_images}")
    print(f"✅ Images avec détections valides: {images_with_detections}")
    print(f"❌ Images sans détection (fausses alertes): {images_without_detections}")
    print(f"\n📊 Détections totales:")
    print(f"   ✅ Valides: {total_valid}")
    print(f"   ❌ Fausses: {total_false}")
    
    # Statistiques par caméra
    cameras = {}
    for r in results:
        cam = r['camera']
        if cam not in cameras:
            cameras[cam] = {'count': 0, 'valid': 0, 'false': 0, 'with_detections': 0}
        cameras[cam]['count'] += 1
        cameras[cam]['valid'] += r['valid']
        cameras[cam]['false'] += r['false']
        if r['has_valid']:
            cameras[cam]['with_detections'] += 1
    
    print(f"\n📷 Par caméra:")
    for cam, stats in sorted(cameras.items()):
        print(f"   {cam}:")
        print(f"      Images: {stats['count']}")
        print(f"      Images avec détections: {stats['with_detections']}")
        print(f"      Détections valides: {stats['valid']}")
        print(f"      Fausses alertes: {stats['count'] - stats['with_detections']}")
    
    # Statistiques par classe d'objet
    all_classes = {}
    for r in results:
        for cls, count in r['by_class'].items():
            all_classes[cls] = all_classes.get(cls, 0) + count
    
    if all_classes:
        print(f"\n🎯 Par type d'objet détecté:")
        for cls, count in sorted(all_classes.items(), key=lambda x: x[1], reverse=True):
            print(f"   {cls}: {count}")
    
    # Statistiques par zone
    all_zones = {}
    for r in results:
        for zone_key, zone_data in r['by_zone'].items():
            zone_name = zone_key.replace('zone_', '')
            if zone_name not in all_zones:
                all_zones[zone_name] = 0
            all_zones[zone_name] += zone_data['total']
    
    if all_zones:
        print(f"\n🗺️  Par zone:")
        for zone, count in sorted(all_zones.items(), key=lambda x: x[1], reverse=True):
            print(f"   {zone}: {count} détection(s)")
    
    # Afficher la structure de sortie créée
    print(f"\n📂 Structure de sortie dans {config.directories.output}:")
    if config.processing.output_structure.save_original:
        print(f"   📁 original/ - {total_images} image(s) originale(s)")
    if config.processing.output_structure.organize_by_result:
        print(f"   📁 true/ - {images_with_detections} image(s) avec détections")
        print(f"   📁 false/ - {images_without_detections} image(s) sans détection")
    if config.processing.output_structure.organize_by_camera:
        print(f"   └─ Sous-dossiers par caméra: {', '.join(sorted(cameras.keys()))}")
    
    print("\n" + "=" * 80)
    print("✅ Test de détection en batch terminé")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    test_batch_detection()