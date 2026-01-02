"""
download_data.py - Download audio datasets from Freesound.org for Forest Guardian ML pipeline.

Freesound.org API Documentation: https://freesound.org/docs/api/

To use this script:
1. Create an account at https://freesound.org
2. Go to https://freesound.org/apiv2/apply/ to get an API key
3. Add your API key to ml/.env file
"""
import os
import requests
from pathlib import Path
from typing import List, Optional
import time
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

# ============================================
# API key loaded from .env file
# ============================================
FREESOUND_API_KEY = os.getenv("FREESOUND_API_KEY", "")
# ============================================

FREESOUND_BASE_URL = "https://freesound.org/apiv2"

# Search queries for each category
CHAINSAW_QUERIES = ["chainsaw", "chainsaw cutting", "chainsaw wood", "logging chainsaw"]
FOREST_QUERIES = ["forest ambience", "forest birds", "jungle ambient", "nature forest", "woodland birds"]
HARD_NEGATIVE_QUERIES = ["motorcycle engine", "lawn mower", "power tools", "drill", "angle grinder", "car engine"]

# Number of samples to download per query
SAMPLES_PER_QUERY = 25


def search_sounds(query: str, page_size: int = 15) -> List[dict]:
    """Search Freesound for sounds matching the query."""
    url = f"{FREESOUND_BASE_URL}/search/text/"
    params = {
        "query": query,
        "token": FREESOUND_API_KEY,
        "fields": "id,name,previews,duration,license",
        "page_size": page_size,
        "filter": "duration:[1 TO 30]",  # 1-30 second clips
        "sort": "rating_desc"
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        return data.get("results", [])
    except requests.RequestException as e:
        print(f"Error searching for '{query}': {e}")
        return []


def download_sound(sound: dict, dest_dir: Path) -> Optional[Path]:
    """Download a sound preview to the destination directory."""
    sound_id = sound["id"]
    name = sound["name"].replace("/", "-").replace("\\", "-")[:50]
    
    # Use the HQ MP3 preview (or LQ if not available)
    previews = sound.get("previews", {})
    preview_url = previews.get("preview-hq-mp3") or previews.get("preview-lq-mp3")
    
    if not preview_url:
        print(f"  No preview available for {name}")
        return None
    
    dest_path = dest_dir / f"{sound_id}_{name}.mp3"
    
    if dest_path.exists():
        print(f"  Already exists: {dest_path.name}")
        return dest_path
    
    try:
        response = requests.get(preview_url, stream=True)
        response.raise_for_status()
        
        with open(dest_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print(f"  Downloaded: {dest_path.name}")
        return dest_path
    except requests.RequestException as e:
        print(f"  Error downloading {name}: {e}")
        return None


def download_category(queries: List[str], dest_dir: Path, samples_per_query: int = SAMPLES_PER_QUERY):
    """Download sounds for a category using multiple search queries."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    downloaded = 0
    
    for query in queries:
        print(f"\nSearching for: '{query}'")
        sounds = search_sounds(query, page_size=samples_per_query)
        
        for sound in sounds:
            result = download_sound(sound, dest_dir)
            if result:
                downloaded += 1
            
            # Rate limiting - be nice to the API
            time.sleep(0.5)
    
    print(f"\nTotal downloaded for {dest_dir.name}: {downloaded} files")
    return downloaded


def convert_mp3_to_wav(src_dir: Path):
    """Convert all MP3 files in a directory to WAV format (16kHz mono)."""
    try:
        from pydub import AudioSegment
    except ImportError:
        print("\nInstall pydub for MP3 to WAV conversion: pip install pydub")
        print("You also need ffmpeg installed on your system.")
        return
    
    for mp3_file in src_dir.glob("*.mp3"):
        wav_file = mp3_file.with_suffix(".wav")
        if wav_file.exists():
            continue
        
        try:
            audio = AudioSegment.from_mp3(mp3_file)
            audio = audio.set_frame_rate(16000).set_channels(1)
            audio.export(wav_file, format="wav")
            print(f"Converted: {wav_file.name}")
        except Exception as e:
            print(f"Error converting {mp3_file.name}: {e}")


def main():
    if not FREESOUND_API_KEY:
        print("=" * 60)
        print("ERROR: Please set your Freesound API key!")
        print()
        print("1. Create an account at https://freesound.org")
        print("2. Get an API key at https://freesound.org/apiv2/apply/")
        print(f"3. Add your key to: {env_path}")
        print("   FREESOUND_API_KEY=your_key_here")
        print("=" * 60)
        return
    
    base = Path(__file__).parent.parent / "data"
    
    print("=" * 60)
    print("Forest Guardian - Audio Dataset Downloader")
    print("Using Freesound.org API")
    print("=" * 60)
    
    # Download chainsaw sounds
    print("\n" + "=" * 40)
    print("Downloading CHAINSAW sounds...")
    print("=" * 40)
    download_category(CHAINSAW_QUERIES, base / "chainsaw")
    
    # Download forest ambient sounds
    print("\n" + "=" * 40)
    print("Downloading FOREST ambient sounds...")
    print("=" * 40)
    download_category(FOREST_QUERIES, base / "forest")
    
    # Download hard negatives (similar but not chainsaw)
    print("\n" + "=" * 40)
    print("Downloading HARD NEGATIVE sounds...")
    print("=" * 40)
    download_category(HARD_NEGATIVE_QUERIES, base / "hard_negatives")
    
    # Convert to WAV
    print("\n" + "=" * 40)
    print("Converting MP3 to WAV (16kHz mono)...")
    print("=" * 40)
    convert_mp3_to_wav(base / "chainsaw")
    convert_mp3_to_wav(base / "forest")
    convert_mp3_to_wav(base / "hard_negatives")
    
    print("\n" + "=" * 60)
    print("Download complete!")
    print(f"Data saved to: {base}")
    print("=" * 60)


if __name__ == "__main__":
    main()

