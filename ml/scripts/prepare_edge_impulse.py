"""
Edge Impulse Data Preparation Script
Prepares audio files for Edge Impulse upload

This script:
1. Converts audio to proper format (16kHz mono WAV)
2. Splits long files into 1-second segments
3. Organizes by label for easy upload
"""

import os
import sys
from pathlib import Path

# Check for required library
try:
    from pydub import AudioSegment
except ImportError:
    print("Installing pydub...")
    os.system(f"{sys.executable} -m pip install pydub")
    from pydub import AudioSegment

# Configuration
SAMPLE_RATE = 16000
SEGMENT_LENGTH_MS = 1000  # 1 second segments
OVERLAP_MS = 500  # 50% overlap for more training data

# Paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "edge_impulse_data"

def convert_and_segment(input_file: Path, label: str, output_dir: Path):
    """Convert audio file to 16kHz mono WAV segments"""
    try:
        # Load audio
        audio = AudioSegment.from_file(str(input_file))
        
        # Convert to mono 16kHz
        audio = audio.set_frame_rate(SAMPLE_RATE).set_channels(1)
        
        # Get base name without extension
        base_name = input_file.stem.replace(" ", "_").replace(".", "_")[:30]
        
        # Split into segments
        duration_ms = len(audio)
        segment_count = 0
        
        for start_ms in range(0, duration_ms - SEGMENT_LENGTH_MS + 1, OVERLAP_MS):
            segment = audio[start_ms:start_ms + SEGMENT_LENGTH_MS]
            
            # Normalize volume
            segment = segment.normalize()
            
            # Skip if too quiet (likely silence)
            if segment.dBFS < -40:
                continue
            
            # Save segment
            output_file = output_dir / f"{label}.{base_name}_{segment_count:03d}.wav"
            segment.export(str(output_file), format="wav")
            segment_count += 1
        
        return segment_count
    except Exception as e:
        print(f"  Error processing {input_file.name}: {e}")
        return 0

def main():
    print("=" * 50)
    print("Edge Impulse Data Preparation")
    print("=" * 50)
    
    # Create output directory
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    # Process each category
    categories = {
        "chainsaw": DATA_DIR / "chainsaw",
        "noise": DATA_DIR / "forest",
    }
    
    total_segments = 0
    
    for label, source_dir in categories.items():
        if not source_dir.exists():
            print(f"\nWarning: {source_dir} not found, skipping...")
            continue
        
        print(f"\nProcessing '{label}' from {source_dir}...")
        
        # Get all audio files
        audio_files = list(source_dir.glob("*.mp3")) + \
                     list(source_dir.glob("*.wav")) + \
                     list(source_dir.glob("*.flac"))
        
        print(f"  Found {len(audio_files)} audio files")
        
        label_segments = 0
        for i, audio_file in enumerate(audio_files):
            segments = convert_and_segment(audio_file, label, OUTPUT_DIR)
            label_segments += segments
            
            # Progress indicator
            if (i + 1) % 10 == 0:
                print(f"  Processed {i + 1}/{len(audio_files)} files...")
        
        print(f"  Created {label_segments} segments for '{label}'")
        total_segments += label_segments
    
    print("\n" + "=" * 50)
    print(f"Done! Created {total_segments} training segments")
    print(f"Output directory: {OUTPUT_DIR}")
    print("\nNext steps:")
    print("1. Go to Edge Impulse Studio")
    print("2. Data acquisition → Upload data")
    print(f"3. Upload all files from: {OUTPUT_DIR}")
    print("   (Filenames are prefixed with labels)")
    print("=" * 50)

if __name__ == "__main__":
    main()
