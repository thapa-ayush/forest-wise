#!/usr/bin/env python3
"""
upload_custom_vision.py - Upload training images to Azure Custom Vision

This script uploads spectrogram images to Azure Custom Vision for training.
Organize your images into folders by class:
  training_images/chainsaw/*.png
  training_images/vehicle/*.png  
  training_images/nature/*.png

Usage:
    python scripts/upload_custom_vision.py

Requirements:
    pip install azure-cognitiveservices-vision-customvision
"""

import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration from environment
TRAINING_ENDPOINT = os.getenv('AZURE_CUSTOM_VISION_TRAINING_ENDPOINT')
TRAINING_KEY = os.getenv('AZURE_CUSTOM_VISION_TRAINING_KEY')
PROJECT_ID = os.getenv('AZURE_CUSTOM_VISION_PROJECT_ID')

# Default training images directory
TRAINING_DIR = Path(__file__).parent.parent.parent / "ml" / "training_images"

# Tags to create
TAGS = ["chainsaw", "vehicle", "nature"]


def main():
    print("=" * 60)
    print("Azure Custom Vision - Training Image Upload")
    print("=" * 60)
    
    # Check configuration
    if not TRAINING_ENDPOINT:
        print("\n❌ AZURE_CUSTOM_VISION_TRAINING_ENDPOINT not set")
        print("   Add to your .env file:")
        print("   AZURE_CUSTOM_VISION_TRAINING_ENDPOINT=https://eastus.api.cognitive.microsoft.com/")
        sys.exit(1)
    
    if not TRAINING_KEY:
        print("\n❌ AZURE_CUSTOM_VISION_TRAINING_KEY not set")
        print("   Add to your .env file:")
        print("   AZURE_CUSTOM_VISION_TRAINING_KEY=your-training-key")
        sys.exit(1)
    
    if not PROJECT_ID:
        print("\n❌ AZURE_CUSTOM_VISION_PROJECT_ID not set")
        print("   Create a project at https://www.customvision.ai/")
        print("   Then add to your .env:")
        print("   AZURE_CUSTOM_VISION_PROJECT_ID=your-project-id")
        sys.exit(1)
    
    print(f"\n✓ Endpoint: {TRAINING_ENDPOINT}")
    print(f"✓ Project ID: {PROJECT_ID[:8]}...")
    
    # Import Azure SDK
    try:
        from azure.cognitiveservices.vision.customvision.training import CustomVisionTrainingClient
        from azure.cognitiveservices.vision.customvision.training.models import ImageFileCreateBatch, ImageFileCreateEntry
        from msrest.authentication import ApiKeyCredentials
    except ImportError:
        print("\n❌ Azure Custom Vision SDK not installed")
        print("   Run: pip install azure-cognitiveservices-vision-customvision")
        sys.exit(1)
    
    # Create client
    credentials = ApiKeyCredentials(in_headers={"Training-key": TRAINING_KEY})
    trainer = CustomVisionTrainingClient(TRAINING_ENDPOINT, credentials)
    
    print(f"\n✓ Connected to Custom Vision")
    
    # Get or create tags
    print(f"\n📁 Setting up tags...")
    existing_tags = trainer.get_tags(PROJECT_ID)
    tag_map = {tag.name.lower(): tag for tag in existing_tags}
    
    for tag_name in TAGS:
        if tag_name.lower() not in tag_map:
            print(f"   Creating tag: {tag_name}")
            tag = trainer.create_tag(PROJECT_ID, tag_name)
            tag_map[tag_name.lower()] = tag
        else:
            print(f"   Tag exists: {tag_name}")
    
    # Check training images directory
    if not TRAINING_DIR.exists():
        print(f"\n❌ Training images directory not found: {TRAINING_DIR}")
        print(f"\n   Create the directory structure:")
        print(f"   {TRAINING_DIR}/")
        print(f"   ├── chainsaw/   (put chainsaw spectrogram images here)")
        print(f"   ├── vehicle/    (put vehicle spectrogram images here)")
        print(f"   └── nature/     (put nature spectrogram images here)")
        
        # Create directories
        create = input("\n   Create directories? (y/n): ").lower().strip()
        if create == 'y':
            for tag in TAGS:
                (TRAINING_DIR / tag).mkdir(parents=True, exist_ok=True)
            print(f"\n   ✓ Created directories. Add images and run again.")
        sys.exit(1)
    
    # Upload images for each tag
    print(f"\n📤 Uploading images...")
    total_uploaded = 0
    
    for tag_name in TAGS:
        tag_dir = TRAINING_DIR / tag_name
        if not tag_dir.exists():
            print(f"\n   ⚠️  Directory not found: {tag_dir}")
            continue
        
        # Get image files
        image_files = list(tag_dir.glob("*.png")) + list(tag_dir.glob("*.jpg")) + list(tag_dir.glob("*.jpeg"))
        
        if not image_files:
            print(f"\n   ⚠️  No images in {tag_dir}")
            continue
        
        print(f"\n   📁 {tag_name}: {len(image_files)} images")
        
        tag_id = tag_map[tag_name.lower()].id
        
        # Upload in batches of 64 (API limit)
        batch_size = 64
        for i in range(0, len(image_files), batch_size):
            batch = image_files[i:i + batch_size]
            
            image_entries = []
            for img_path in batch:
                with open(img_path, "rb") as f:
                    image_entries.append(ImageFileCreateEntry(
                        name=img_path.name,
                        contents=f.read(),
                        tag_ids=[tag_id]
                    ))
            
            try:
                upload_result = trainer.create_images_from_files(
                    PROJECT_ID,
                    ImageFileCreateBatch(images=image_entries)
                )
                
                success = len([img for img in upload_result.images if img.status == "OK"])
                duplicate = len([img for img in upload_result.images if img.status == "OKDuplicate"])
                failed = len([img for img in upload_result.images if img.status not in ["OK", "OKDuplicate"]])
                
                print(f"      Batch {i//batch_size + 1}: {success} uploaded, {duplicate} duplicates, {failed} failed")
                total_uploaded += success
                
            except Exception as e:
                print(f"      ❌ Batch upload failed: {e}")
            
            # Rate limiting
            time.sleep(1)
    
    print(f"\n" + "=" * 60)
    print(f"✅ Upload complete! {total_uploaded} images uploaded")
    print("=" * 60)
    
    # Offer to train
    print(f"\n📊 Next steps:")
    print(f"   1. Go to https://www.customvision.ai/")
    print(f"   2. Open your project")
    print(f"   3. Click 'Train' button")
    print(f"   4. After training, click 'Publish'")
    print(f"   5. Note the iteration name (e.g., 'Iteration1' or 'production')")
    
    train_now = input("\n   Start training via API? (y/n): ").lower().strip()
    if train_now == 'y':
        print("\n   🚀 Starting training...")
        try:
            iteration = trainer.train_project(PROJECT_ID)
            print(f"   ✓ Training started: {iteration.name}")
            print(f"   ⏳ This may take 5-15 minutes...")
            
            # Wait for training
            while iteration.status != "Completed":
                iteration = trainer.get_iteration(PROJECT_ID, iteration.id)
                print(f"      Status: {iteration.status}")
                if iteration.status == "Failed":
                    print(f"   ❌ Training failed!")
                    break
                time.sleep(10)
            
            if iteration.status == "Completed":
                print(f"\n   ✅ Training complete!")
                
                # Publish
                publish = input("\n   Publish as 'production'? (y/n): ").lower().strip()
                if publish == 'y':
                    prediction_resource_id = os.getenv('AZURE_CUSTOM_VISION_PREDICTION_RESOURCE_ID')
                    if prediction_resource_id:
                        trainer.publish_iteration(
                            PROJECT_ID,
                            iteration.id,
                            "production",
                            prediction_resource_id
                        )
                        print(f"   ✓ Published as 'production'")
                    else:
                        print(f"   ⚠️  Set AZURE_CUSTOM_VISION_PREDICTION_RESOURCE_ID to publish via API")
                        print(f"   Or publish manually in the portal")
                        
        except Exception as e:
            print(f"   ❌ Training error: {e}")
            print(f"   Train manually at https://www.customvision.ai/")


if __name__ == "__main__":
    main()
