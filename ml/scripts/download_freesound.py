#!/usr/bin/env python3
"""
download_freesound.py - Download audio samples from Freesound.org API

This script downloads audio samples for training Custom Vision:
- Chainsaw sounds
- Vehicle sounds (trucks, engines)
- Nature sounds (forest, birds, wind)

Setup:
1. Create account at https://freesound.org/
2. Go to https://freesound.org/apiv2/apply/
3. Create an API application to get your API key
4. Set FREESOUND_API_KEY in your .env file

Usage:
    python scripts/download_freesound.py
"""

import os
import sys
import time
import requests
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
FREESOUND_API_KEY = os.getenv('FREESOUND_API_KEY')
BASE_URL = "https://freesound.org/apiv2"

# Output directory
OUTPUT_DIR = Path(__file__).parent.parent / "audio_samples"

# Search queries for each class
SEARCH_QUERIES = {
    "chainsaw": [
        "chainsaw",
        "chainsaw cutting",
        "chainsaw engine",
        "power saw",
        "tree cutting chainsaw",
    ],
    "vehicle": [
        "truck engine",
        "diesel engine",
        "vehicle engine idle",
        "logging truck",
        "heavy machinery",
        "tractor engine",
    ],
    "nature": [
        "forest ambience",
        "forest birds",
        "rainforest",
        "jungle sounds",
        "wind trees",
        "river forest",
        "woodland birds",
        "nature ambience",
    ]
}

# How many samples to download per class
SAMPLES_PER_CLASS = 50
MAX_DURATION_SECONDS = 30  # Skip very long files
MIN_DURATION_SECONDS = 2   # Skip very short files


def get_api_key():
    """Get or prompt for API key"""
    global FREESOUND_API_KEY
    
    if FREESOUND_API_KEY:
        return FREESOUND_API_KEY
    
    print("\n" + "=" * 60)
    print("Freesound API Key Required")
    print("=" * 60)
    print("\n1. Create account at https://freesound.org/")
    print("2. Go to https://freesound.org/apiv2/apply/")
    print("3. Create an API application")
    print("4. Copy your API key")
    print("\nAdd to your .env file:")
    print("   FREESOUND_API_KEY=your-api-key-here")
    
    key = input("\nOr enter API key now: ").strip()
    if key:
        FREESOUND_API_KEY = key
        return key
    
    return None


def search_sounds(query: str, page_size: int = 15) -> list:
    """Search for sounds on Freesound"""
    url = f"{BASE_URL}/search/text/"
    params = {
        "query": query,
        "token": FREESOUND_API_KEY,
        "fields": "id,name,duration,previews,license,username",
        "page_size": page_size,
        "filter": f"duration:[{MIN_DURATION_SECONDS} TO {MAX_DURATION_SECONDS}]",
        "sort": "downloads_desc"  # Get popular/quality sounds first
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get("results", [])
    except Exception as e:
        print(f"   ❌ Search error: {e}")
        return []


def download_sound(sound: dict, output_path: Path) -> bool:
    """Download a sound file"""
    try:
        # Get preview URL (MP3 format, doesn't require OAuth)
        preview_url = sound.get("previews", {}).get("preview-hq-mp3")
        if not preview_url:
            preview_url = sound.get("previews", {}).get("preview-lq-mp3")
        
        if not preview_url:
            return False
        
        # Download
        response = requests.get(preview_url, timeout=30)
        response.raise_for_status()
        
        # Save
        with open(output_path, "wb") as f:
            f.write(response.content)
        
        return True
        
    except Exception as e:
        print(f"   ❌ Download error: {e}")
        return False


def download_class_samples(class_name: str, queries: list, target_count: int):
    """Download samples for a single class"""
    output_dir = OUTPUT_DIR / class_name
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Count existing files
    existing = list(output_dir.glob("*.mp3")) + list(output_dir.glob("*.wav"))
    downloaded_count = len(existing)
    
    print(f"\n📁 {class_name.upper()}")
    print(f"   Existing: {downloaded_count} files")
    
    if downloaded_count >= target_count:
        print(f"   ✓ Already have {target_count}+ samples")
        return downloaded_count
    
    needed = target_count - downloaded_count
    print(f"   Need: {needed} more samples")
    
    # Track downloaded sound IDs to avoid duplicates
    downloaded_ids = set()
    
    for query in queries:
        if downloaded_count >= target_count:
            break
        
        print(f"\n   🔍 Searching: '{query}'")
        sounds = search_sounds(query, page_size=20)
        
        for sound in sounds:
            if downloaded_count >= target_count:
                break
            
            sound_id = sound.get("id")
            if sound_id in downloaded_ids:
                continue
            
            # Create filename
            safe_name = "".join(c if c.isalnum() or c in "._- " else "_" for c in sound.get("name", "unknown"))
            filename = f"fs_{sound_id}_{safe_name[:50]}.mp3"
            output_path = output_dir / filename
            
            if output_path.exists():
                downloaded_ids.add(sound_id)
                continue
            
            # Download
            duration = sound.get("duration", 0)
            print(f"      ↓ {sound.get('name', 'Unknown')[:40]}... ({duration:.1f}s)")
            
            if download_sound(sound, output_path):
                downloaded_count += 1
                downloaded_ids.add(sound_id)
            
            # Rate limiting - be nice to the API
            time.sleep(0.5)
    
    print(f"\n   ✓ Total {class_name}: {downloaded_count} samples")
    return downloaded_count


def main():
    print("=" * 60)
    print("Freesound Audio Sample Downloader")
    print("For Forest Guardian Custom Vision Training")
    print("=" * 60)
    
    # Get API key
    api_key = get_api_key()
    if not api_key:
        print("\n❌ No API key provided. Exiting.")
        sys.exit(1)
    
    print(f"\n✓ API Key: {api_key[:8]}...")
    
    # Test API connection
    print("\n🔌 Testing API connection...")
    test_results = search_sounds("test", page_size=1)
    if not test_results:
        print("❌ API connection failed. Check your API key.")
        sys.exit(1)
    print("✓ API connection successful")
    
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"\n📂 Output directory: {OUTPUT_DIR}")
    
    # Download samples for each class
    total_downloaded = 0
    
    for class_name, queries in SEARCH_QUERIES.items():
        count = download_class_samples(class_name, queries, SAMPLES_PER_CLASS)
        total_downloaded += count
    
    # Summary
    print("\n" + "=" * 60)
    print("Download Complete!")
    print("=" * 60)
    
    print(f"\n📊 Summary:")
    for class_name in SEARCH_QUERIES.keys():
        class_dir = OUTPUT_DIR / class_name
        if class_dir.exists():
            files = list(class_dir.glob("*.mp3")) + list(class_dir.glob("*.wav"))
            status = "✓" if len(files) >= 50 else "⚠️"
            print(f"   {status} {class_name}: {len(files)} samples")
    
    print(f"\n📤 Next steps:")
    print(f"   1. Generate spectrograms:")
    print(f"      python scripts/generate_training_spectrograms.py")
    print(f"   2. Upload to Custom Vision:")
    print(f"      python scripts/upload_custom_vision.py")
    
    # Save API key hint
    if not os.getenv('FREESOUND_API_KEY'):
        print(f"\n💡 Tip: Add to .env to save your API key:")
        print(f"   FREESOUND_API_KEY={api_key}")


if __name__ == "__main__":
    main()
