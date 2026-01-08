#!/usr/bin/env python3
"""
Download Custom Vision TFLite model export
"""
import os
import sys
import time
import zipfile
import shutil
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/home/forestguardain/forest-g/hub/.env')

from azure.cognitiveservices.vision.customvision.training import CustomVisionTrainingClient
from msrest.authentication import ApiKeyCredentials

# Configuration
TRAINING_ENDPOINT = os.getenv('AZURE_CUSTOM_VISION_TRAINING_ENDPOINT')
TRAINING_KEY = os.getenv('AZURE_CUSTOM_VISION_TRAINING_KEY')
PROJECT_ID = os.getenv('AZURE_CUSTOM_VISION_PROJECT_ID')
MODEL_DIR = '/home/forestguardain/forest-g/ml/models'
EXPORT_PLATFORM = 'TensorFlow'  # TFLite export

def main():
    print("🔗 Connecting to Azure Custom Vision...")
    
    credentials = ApiKeyCredentials(in_headers={"Training-key": TRAINING_KEY})
    trainer = CustomVisionTrainingClient(TRAINING_ENDPOINT, credentials)
    
    # Get all iterations
    print("📋 Getting project iterations...")
    iterations = trainer.get_iterations(PROJECT_ID)
    
    if not iterations:
        print("❌ No iterations found!")
        sys.exit(1)
    
    # Find the latest trained iteration
    trained_iterations = [i for i in iterations if i.status == "Completed"]
    if not trained_iterations:
        print("❌ No completed iterations found!")
        sys.exit(1)
    
    # Sort by training time, get latest
    trained_iterations.sort(key=lambda x: x.trained_at, reverse=True)
    latest = trained_iterations[0]
    
    print(f"✅ Found latest iteration: {latest.name}")
    print(f"   ID: {latest.id}")
    print(f"   Trained: {latest.trained_at}")
    print(f"   Status: {latest.status}")
    
    # Check existing exports
    print("\n📦 Checking exports...")
    exports = trainer.get_exports(PROJECT_ID, latest.id)
    
    tflite_export = None
    for export in exports:
        if export.platform == EXPORT_PLATFORM and export.flavor == "TensorFlowLite":
            tflite_export = export
            break
    
    # Request new export if not exists or outdated
    if not tflite_export or tflite_export.status != "Done":
        print("🔄 Requesting TensorFlow Lite export...")
        try:
            trainer.export_iteration(PROJECT_ID, latest.id, EXPORT_PLATFORM, flavor="TensorFlowLite")
            print("   Export requested, waiting for completion...")
            
            # Wait for export to complete
            for i in range(30):
                time.sleep(5)
                exports = trainer.get_exports(PROJECT_ID, latest.id)
                for export in exports:
                    if export.platform == EXPORT_PLATFORM and export.flavor == "TensorFlowLite":
                        if export.status == "Done":
                            tflite_export = export
                            break
                if tflite_export and tflite_export.status == "Done":
                    break
                print(f"   Waiting... ({(i+1)*5}s)")
        except Exception as e:
            if "already been queued" in str(e) or "already exported" in str(e).lower():
                print("   Export already exists, refreshing...")
                exports = trainer.get_exports(PROJECT_ID, latest.id)
                for export in exports:
                    if export.platform == EXPORT_PLATFORM and export.flavor == "TensorFlowLite":
                        tflite_export = export
                        break
            else:
                raise
    
    if not tflite_export or tflite_export.status != "Done":
        print("❌ Export not ready!")
        sys.exit(1)
    
    print(f"✅ Export ready: {tflite_export.download_uri[:80]}...")
    
    # Download the export
    print("\n⬇️ Downloading model...")
    zip_path = os.path.join(MODEL_DIR, 'custom_vision_export_new.zip')
    
    response = requests.get(tflite_export.download_uri, stream=True)
    response.raise_for_status()
    
    with open(zip_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    
    print(f"   Downloaded: {os.path.getsize(zip_path) / 1024 / 1024:.2f} MB")
    
    # Backup old model
    old_model = os.path.join(MODEL_DIR, 'chainsaw_classifier.tflite')
    if os.path.exists(old_model):
        backup_path = os.path.join(MODEL_DIR, 'chainsaw_classifier_backup.tflite')
        shutil.copy(old_model, backup_path)
        print(f"   Backed up old model to: {backup_path}")
    
    # Extract new model
    print("\n📂 Extracting model...")
    extract_dir = os.path.join(MODEL_DIR, 'new_export')
    
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)
    
    # Find and copy the .tflite file
    for root, dirs, files in os.walk(extract_dir):
        for file in files:
            if file.endswith('.tflite'):
                src = os.path.join(root, file)
                shutil.copy(src, old_model)
                print(f"   ✅ Copied: {file} -> chainsaw_classifier.tflite")
            if file == 'labels.txt':
                src = os.path.join(root, file)
                dest = os.path.join(MODEL_DIR, 'labels.txt')
                shutil.copy(src, dest)
                print(f"   ✅ Copied: labels.txt")
                # Display labels
                with open(dest) as f:
                    labels = f.read().strip().split('\n')
                    print(f"   📝 Labels: {labels}")
    
    # Cleanup
    shutil.rmtree(extract_dir)
    os.remove(zip_path)
    
    print("\n🎉 Model updated successfully!")
    print("   Restart the hub to use the new model.")
    
    # Show model info
    model_size = os.path.getsize(old_model) / 1024 / 1024
    print(f"\n📊 Model Info:")
    print(f"   Size: {model_size:.2f} MB")
    print(f"   Path: {old_model}")

if __name__ == "__main__":
    main()
