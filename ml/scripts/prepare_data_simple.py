"""
Edge Impulse Data Preparation Script (No ffmpeg required)
Converts audio files to 16kHz mono WAV for Edge Impulse upload
"""

import os
import sys
from pathlib import Path
import soundfile as sf
import numpy as np
from scipy import signal

# Configuration
SAMPLE_RATE = 16000
SEGMENT_LENGTH = SAMPLE_RATE  # 1 second
OVERLAP = SAMPLE_RATE // 2    # 0.5 second overlap

# Paths
SCRIPT_DIR = Path(__file__).parent
ML_DIR = SCRIPT_DIR.parent
DATA_DIR = ML_DIR / "data"
OUTPUT_DIR = ML_DIR / "edge_impulse_data"

def load_audio(file_path):
    """Load audio file and convert to mono 16kHz"""
    try:
        # Try soundfile first (works with WAV, FLAC)
        data, sr = sf.read(str(file_path))
        
        # Convert to mono if stereo
        if len(data.shape) > 1:
            data = np.mean(data, axis=1)
        
        # Resample to 16kHz if needed
        if sr != SAMPLE_RATE:
            num_samples = int(len(data) * SAMPLE_RATE / sr)
            data = signal.resample(data, num_samples)
        
        return data
    except Exception as e:
        return None

def normalize_audio(data):
    """Normalize audio to -1 to 1 range"""
    max_val = np.max(np.abs(data))
    if max_val > 0:
        data = data / max_val * 0.9
    return data

def process_file(input_file, label, output_dir):
    """Process single audio file into segments"""
    data = load_audio(input_file)
    if data is None:
        return 0
    
    # Normalize
    data = normalize_audio(data)
    
    # Get base name
    base_name = input_file.stem.replace(" ", "_").replace(".", "_")[:25]
    
    # Split into segments
    segment_count = 0
    for start in range(0, len(data) - SEGMENT_LENGTH + 1, OVERLAP):
        segment = data[start:start + SEGMENT_LENGTH]
        
        # Skip quiet segments
        if np.max(np.abs(segment)) < 0.05:
            continue
        
        # Save segment
        output_file = output_dir / f"{label}.{base_name}_{segment_count:03d}.wav"
        sf.write(str(output_file), segment, SAMPLE_RATE)
        segment_count += 1
    
    return segment_count

def main():
    print("=" * 50)
    print("Edge Impulse Data Preparation")
    print("=" * 50)
    
    # Create output directory
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    # Categories
    categories = {
        "chainsaw": DATA_DIR / "chainsaw",
        "noise": DATA_DIR / "forest",
    }
    
    total = 0
    
    for label, source_dir in categories.items():
        if not source_dir.exists():
            print(f"Warning: {source_dir} not found")
            continue
        
        print(f"\nProcessing '{label}'...")
        
        # Get audio files (WAV and FLAC work, MP3 needs ffmpeg)
        files = list(source_dir.glob("*.wav")) + list(source_dir.glob("*.flac"))
        
        # Also try MP3 files that might actually be other formats
        mp3_files = list(source_dir.glob("*.mp3"))
        
        all_files = files + mp3_files
        print(f"  Found {len(all_files)} files")
        
        label_count = 0
        for i, f in enumerate(all_files):
            count = process_file(f, label, OUTPUT_DIR)
            label_count += count
            if (i + 1) % 20 == 0:
                print(f"  Processed {i+1}/{len(all_files)}...")
        
        print(f"  Created {label_count} segments")
        total += label_count
    
    print("\n" + "=" * 50)
    print(f"Total: {total} training segments")
    print(f"Output: {OUTPUT_DIR}")
    print("=" * 50)
    print("\nNext: Upload these files to Edge Impulse")

if __name__ == "__main__":
    main()
