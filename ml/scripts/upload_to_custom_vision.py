#!/usr/bin/env python3
"""
upload_to_custom_vision.py - Forest Guardian
Automated upload of training images to Azure Custom Vision

Usage:
    python upload_to_custom_vision.py

Environment Variables Required:
    AZURE_CV_TRAINING_ENDPOINT - Custom Vision training endpoint
    AZURE_CV_TRAINING_KEY - Custom Vision training key
"""

import os
import sys
import time
from pathlib import Path
from typing import List, Tuple

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'hub'))

# Training images directory
TRAINING_DIR = Path(__file__).parent.parent / 'ml' / 'training_images'

# Class folders and their tags
CLASS_FOLDERS = {
    'chainsaw': 'chainsaw',
    'nature': 'nature', 
    'vehicle': 'vehicle'
}

def check_environment():
    """Check if required environment variables are set"""
    # Load .env from hub directory
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent.parent / 'hub' / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ Loaded .env from {env_path}")
    
    endpoint = os.environ.get('AZURE_CUSTOM_VISION_TRAINING_ENDPOINT')
    key = os.environ.get('AZURE_CUSTOM_VISION_TRAINING_KEY')
    
    if not endpoint or not key:
        print("❌ Missing environment variables!")
        print("\nPlease set in hub/.env:")
        print("  AZURE_CUSTOM_VISION_TRAINING_ENDPOINT=https://your-region.cognitiveservices.azure.com/")
        print("  AZURE_CUSTOM_VISION_TRAINING_KEY=your-training-key")
        return False
    
    print(f"✅ Endpoint: {endpoint[:50]}...")
    print(f"✅ Key: {key[:10]}...")
    return True


def get_training_client():
    """Initialize Custom Vision training client"""
    try:
        from azure.cognitiveservices.vision.customvision.training import CustomVisionTrainingClient
        from msrest.authentication import ApiKeyCredentials
        
        endpoint = os.environ.get('AZURE_CUSTOM_VISION_TRAINING_ENDPOINT')
        key = os.environ.get('AZURE_CUSTOM_VISION_TRAINING_KEY')
        
        credentials = ApiKeyCredentials(in_headers={"Training-key": key})
        client = CustomVisionTrainingClient(endpoint, credentials)
        
        return client
    except ImportError:
        print("❌ Azure Custom Vision SDK not installed!")
        print("Run: pip install azure-cognitiveservices-vision-customvision")
        return None


def create_project(client, project_name: str = "forest-guardian-spectrogram"):
    """Create a new Custom Vision project"""
    from azure.cognitiveservices.vision.customvision.training.models import Domain
    
    # Get available domains
    domains = client.get_domains()
    
    # Find compact classification domain (required for export)
    compact_domain = None
    for domain in domains:
        if domain.type == "Classification" and domain.exportable:
            if "General" in domain.name:
                compact_domain = domain
                break
    
    if not compact_domain:
        # Fall back to any exportable domain
        for domain in domains:
            if domain.exportable:
                compact_domain = domain
                break
    
    if not compact_domain:
        print("❌ No exportable domain found!")
        return None
    
    print(f"📦 Using domain: {compact_domain.name} (exportable: {compact_domain.exportable})")
    
    # Check if project exists
    projects = client.get_projects()
    for project in projects:
        if project.name == project_name:
            print(f"✅ Project '{project_name}' already exists (ID: {project.id})")
            return project
    
    # Create new project
    project = client.create_project(
        project_name,
        domain_id=compact_domain.id,
        classification_type="Multiclass"
    )
    
    print(f"✅ Created project '{project_name}' (ID: {project.id})")
    return project


def create_tags(client, project) -> dict:
    """Create tags for each class"""
    existing_tags = client.get_tags(project.id)
    tag_map = {tag.name: tag for tag in existing_tags}
    
    for folder_name, tag_name in CLASS_FOLDERS.items():
        if tag_name not in tag_map:
            tag = client.create_tag(project.id, tag_name)
            tag_map[tag_name] = tag
            print(f"✅ Created tag: {tag_name}")
        else:
            print(f"✅ Tag exists: {tag_name}")
    
    return tag_map


def get_images_to_upload(tag_name: str) -> List[Path]:
    """Get list of images for a class"""
    folder = TRAINING_DIR / tag_name
    if not folder.exists():
        print(f"⚠️ Folder not found: {folder}")
        return []
    
    images = list(folder.glob("*.png")) + list(folder.glob("*.jpg"))
    return images


def upload_images(client, project, tag_map: dict, batch_size: int = 64):
    """Upload training images in batches"""
    from azure.cognitiveservices.vision.customvision.training.models import ImageFileCreateBatch, ImageFileCreateEntry
    
    total_uploaded = 0
    total_failed = 0
    
    for folder_name, tag_name in CLASS_FOLDERS.items():
        tag = tag_map.get(tag_name)
        if not tag:
            print(f"⚠️ Tag not found: {tag_name}")
            continue
        
        images = get_images_to_upload(folder_name)
        print(f"\n📁 {tag_name}: {len(images)} images")
        
        # Upload in batches
        for i in range(0, len(images), batch_size):
            batch_images = images[i:i + batch_size]
            entries = []
            
            for img_path in batch_images:
                try:
                    with open(img_path, "rb") as f:
                        contents = f.read()
                    
                    entry = ImageFileCreateEntry(
                        name=img_path.name,
                        contents=contents,
                        tag_ids=[tag.id]
                    )
                    entries.append(entry)
                except Exception as e:
                    print(f"  ⚠️ Failed to read {img_path.name}: {e}")
                    total_failed += 1
            
            if entries:
                try:
                    batch = ImageFileCreateBatch(images=entries)
                    result = client.create_images_from_files(project.id, batch)
                    
                    success = sum(1 for img in result.images if img.status == "OK")
                    duplicate = sum(1 for img in result.images if img.status == "OKDuplicate")
                    failed = sum(1 for img in result.images if img.status not in ["OK", "OKDuplicate"])
                    
                    total_uploaded += success
                    total_failed += failed
                    
                    print(f"  Batch {i//batch_size + 1}: ✅ {success} uploaded, 📋 {duplicate} duplicates, ❌ {failed} failed")
                    
                    # Rate limiting
                    time.sleep(1)
                    
                except Exception as e:
                    print(f"  ❌ Batch upload failed: {e}")
                    total_failed += len(entries)
    
    return total_uploaded, total_failed


def train_model(client, project):
    """Start training the model"""
    import time
    
    print("\n🚀 Starting training...")
    
    try:
        iteration = client.train_project(project.id)
        print(f"Training iteration: {iteration.name} (ID: {iteration.id})")
        
        # Wait for training to complete
        while iteration.status != "Completed":
            iteration = client.get_iteration(project.id, iteration.id)
            print(f"  Status: {iteration.status}...")
            
            if iteration.status == "Failed":
                print("❌ Training failed!")
                return None
            
            time.sleep(10)
        
        print(f"✅ Training completed!")
        return iteration
        
    except Exception as e:
        print(f"❌ Training error: {e}")
        return None


def publish_iteration(client, project, iteration, publish_name: str = "forest-guardian-v1"):
    """Publish the trained iteration for prediction"""
    prediction_resource_id = os.environ.get('AZURE_CV_PREDICTION_RESOURCE_ID')
    
    if not prediction_resource_id:
        print("⚠️ AZURE_CV_PREDICTION_RESOURCE_ID not set")
        print("  Get this from Azure Portal → Custom Vision → Properties → Resource ID")
        print("  You can still export the model without publishing")
        return False
    
    try:
        client.publish_iteration(
            project.id,
            iteration.id,
            publish_name,
            prediction_resource_id
        )
        print(f"✅ Published as: {publish_name}")
        return True
    except Exception as e:
        print(f"⚠️ Publish failed: {e}")
        return False


def export_model(client, project, iteration, platform: str = "TensorFlow", flavor: str = "TensorFlowLite"):
    """Export the model for offline use"""
    print(f"\n📦 Exporting model ({platform}/{flavor})...")
    
    try:
        # Request export
        export = client.export_iteration(project.id, iteration.id, platform, flavor)
        
        # Wait for export to be ready
        while export.status != "Done":
            exports = client.get_exports(project.id, iteration.id)
            for e in exports:
                if e.platform == platform and e.flavor == flavor:
                    export = e
                    break
            
            if export.status == "Failed":
                print(f"❌ Export failed!")
                return None
            
            print(f"  Export status: {export.status}...")
            time.sleep(5)
        
        print(f"✅ Export ready!")
        print(f"📥 Download URL: {export.download_uri}")
        
        # Download the file
        import requests
        response = requests.get(export.download_uri)
        
        output_dir = Path(__file__).parent.parent / 'ml' / 'models'
        output_dir.mkdir(exist_ok=True)
        
        zip_path = output_dir / "custom_vision_export.zip"
        with open(zip_path, "wb") as f:
            f.write(response.content)
        
        print(f"✅ Downloaded to: {zip_path}")
        
        # Extract
        import zipfile
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(output_dir)
        
        # Rename model file
        for tflite_file in output_dir.glob("*.tflite"):
            target = output_dir / "chainsaw_classifier.tflite"
            tflite_file.rename(target)
            print(f"✅ Model saved to: {target}")
            break
        
        return export
        
    except Exception as e:
        print(f"❌ Export error: {e}")
        return None


def show_performance(client, project, iteration):
    """Show model performance metrics"""
    print("\n📊 Model Performance:")
    
    try:
        performance = client.get_iteration_performance(project.id, iteration.id)
        
        print(f"  Precision: {performance.precision * 100:.1f}%")
        print(f"  Recall: {performance.recall * 100:.1f}%")
        print(f"  Average Precision: {performance.average_precision * 100:.1f}%")
        
        print("\n  Per-class performance:")
        for tag_perf in performance.per_tag_performance:
            print(f"    {tag_perf.name}:")
            print(f"      Precision: {tag_perf.precision * 100:.1f}%")
            print(f"      Recall: {tag_perf.recall * 100:.1f}%")
            print(f"      AP: {tag_perf.average_precision * 100:.1f}%")
            
    except Exception as e:
        print(f"  ⚠️ Could not get performance: {e}")


def main():
    print("=" * 60)
    print("🌲 Forest Guardian - Azure Custom Vision Training")
    print("=" * 60)
    
    # Check environment
    if not check_environment():
        return
    
    # Initialize client
    client = get_training_client()
    if not client:
        return
    
    # Create or get project
    project = create_project(client)
    if not project:
        return
    
    # Create tags
    tag_map = create_tags(client, project)
    
    # Check image counts
    print("\n📊 Training images available:")
    for folder_name, tag_name in CLASS_FOLDERS.items():
        images = get_images_to_upload(folder_name)
        print(f"  {tag_name}: {len(images)} images")
    
    # Upload images
    print("\n" + "=" * 60)
    response = input("Upload images to Custom Vision? (y/n): ").strip().lower()
    
    if response == 'y':
        uploaded, failed = upload_images(client, project, tag_map)
        print(f"\n📊 Upload complete: {uploaded} uploaded, {failed} failed")
    
    # Train model
    print("\n" + "=" * 60)
    response = input("Start training? (y/n): ").strip().lower()
    
    if response == 'y':
        iteration = train_model(client, project)
        
        if iteration:
            show_performance(client, project, iteration)
            
            # Export model
            print("\n" + "=" * 60)
            response = input("Export model for Raspberry Pi? (y/n): ").strip().lower()
            
            if response == 'y':
                export_model(client, project, iteration)
    
    print("\n✅ Done!")
    print("\nNext steps:")
    print("1. If you didn't export via script, export manually from customvision.ai")
    print("2. Copy model.tflite to: ml/models/chainsaw_classifier.tflite")
    print("3. Test with: python hub/local_inference.py")


if __name__ == "__main__":
    main()
