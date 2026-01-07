#!/usr/bin/env python3
"""
generate_training_spectrograms.py - Generate spectrograms from audio files for Custom Vision training

This script converts audio files (.wav, .mp3) into mel spectrogram images
that can be used to train Azure Custom Vision.

Usage:
    python scripts/generate_training_spectrograms.py

Directory structure expected:
    ml/audio_samples/
    ├── chainsaw/    (chainsaw audio files)
    ├── vehicle/     (vehicle audio files)
    └── nature/      (nature/forest audio files)

Output:
    ml/training_images/
    ├── chainsaw/    (spectrogram images)
    ├── vehicle/     (spectrogram images)
    └── nature/      (spectrogram images)
"""

import os
import sys
import numpy as np
from pathlib import Path

# Try to import required libraries
try:
    import librosa
    import librosa.display
    import matplotlib.pyplot as plt
except ImportError:
    print("❌ Required libraries not installed")
    print("   Run: pip install librosa matplotlib numpy")
    sys.exit(1)

# Configuration
AUDIO_DIR = Path(__file__).parent.parent / "audio_samples"
OUTPUT_DIR = Path(__file__).parent.parent / "training_images"

# Spectrogram parameters - MUST MATCH ESP32 firmware!
# See: firmware/guardian_node_spectrogram/spectrogram.h
SAMPLE_RATE = 16000  # 16kHz
N_MELS = 32          # 32 mel bins (ESP32 uses NUM_MEL_BINS = 32)
N_FFT = 128          # FFT window size (ESP32 uses FFT_SIZE = 128)
HOP_LENGTH = 64      # Hop between windows (ESP32 uses FFT_HOP = 64)
WINDOW_SECONDS = 1   # ~1 second windows (ESP32 processes ~1 sec chunks)

# Output image size (ESP32 generates 32x32)
SPEC_WIDTH = 32
SPEC_HEIGHT = 32

CLASSES = ["chainsaw", "vehicle", "nature"]


def audio_to_spectrogram(audio_path: Path, output_path: Path, window_idx: int = 0):
    """Convert an audio file to a mel spectrogram image - MUST MATCH ESP32 output exactly"""
    try:
        # Load audio
        y, sr = librosa.load(str(audio_path), sr=SAMPLE_RATE)
        
        # Skip very short files
        if len(y) < SAMPLE_RATE * 0.5:  # Less than 0.5 seconds
            return False
        
        # Calculate window size
        window_samples = int(WINDOW_SECONDS * sr)
        
        # Extract window
        start = window_idx * window_samples
        if start + window_samples > len(y):
            return False
        
        y_window = y[start:start + window_samples]
        
        # Generate mel spectrogram - MATCH ESP32 parameters exactly
        mel_spec = librosa.feature.melspectrogram(
            y=y_window,
            sr=sr,
            n_mels=N_MELS,
            n_fft=N_FFT,
            hop_length=HOP_LENGTH,
            fmin=100,    # ESP32: mel_low = hz_to_mel(100.0f)
            fmax=8000    # ESP32: mel_high = hz_to_mel(8000.0f)
        )
        
        # Convert to log scale (like ESP32: energy = logf(energy + 1e-10f))
        mel_spec_log = np.log(mel_spec + 1e-10)
        
        # Handle edge case where all values are the same (silent audio)
        spec_range = mel_spec_log.max() - mel_spec_log.min()
        if spec_range < 0.001:
            return False  # Skip silent/invalid audio
        
        # Normalize to 0-255 (like ESP32)
        mel_spec_norm = ((mel_spec_log - mel_spec_log.min()) / spec_range * 255).astype(np.uint8)
        
        # Resize to exactly 32x32 if needed
        from PIL import Image
        
        # Flip vertically so low frequencies are at bottom (like ESP32)
        mel_spec_flipped = np.flipud(mel_spec_norm)
        
        # Create PIL image in grayscale mode 'L' (matching ESP32 output)
        img = Image.fromarray(mel_spec_flipped, mode='L')
        
        # Resize to exactly SPEC_WIDTH x SPEC_HEIGHT (32x32)
        img = img.resize((SPEC_WIDTH, SPEC_HEIGHT), Image.Resampling.NEAREST)
        
        # Save as PNG in grayscale mode
        img.save(output_path, 'PNG')
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error processing {audio_path.name}: {e}")
        return False


def main():
    print("=" * 60)
    print("Spectrogram Generator for Custom Vision Training")
    print("=" * 60)
    
    # Check audio directory
    if not AUDIO_DIR.exists():
        print(f"\n❌ Audio samples directory not found: {AUDIO_DIR}")
        print(f"\n   Create the directory structure:")
        print(f"   {AUDIO_DIR}/")
        print(f"   ├── chainsaw/   (chainsaw audio files)")
        print(f"   ├── vehicle/    (vehicle audio files)")
        print(f"   └── nature/     (nature/forest audio files)")
        
        create = input("\n   Create directories? (y/n): ").lower().strip()
        if create == 'y':
            for cls in CLASSES:
                (AUDIO_DIR / cls).mkdir(parents=True, exist_ok=True)
            print(f"\n   ✓ Created directories. Add audio files and run again.")
            print(f"\n   💡 Tips for getting audio samples:")
            print(f"      - Record with your phone")
            print(f"      - Download from YouTube (chainsaw videos)")
            print(f"      - ESC-50 dataset: github.com/karolpiczak/ESC-50")
            print(f"      - Freesound.org (search 'chainsaw', 'forest')")
        sys.exit(1)
    
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    total_generated = 0
    
    for cls in CLASSES:
        cls_audio_dir = AUDIO_DIR / cls
        cls_output_dir = OUTPUT_DIR / cls
        cls_output_dir.mkdir(parents=True, exist_ok=True)
        
        if not cls_audio_dir.exists():
            print(f"\n⚠️  No directory: {cls_audio_dir}")
            continue
        
        # Find audio files
        audio_files = (
            list(cls_audio_dir.glob("*.wav")) +
            list(cls_audio_dir.glob("*.mp3")) +
            list(cls_audio_dir.glob("*.ogg")) +
            list(cls_audio_dir.glob("*.flac"))
        )
        
        if not audio_files:
            print(f"\n⚠️  No audio files in {cls_audio_dir}")
            continue
        
        print(f"\n📁 Processing {cls}: {len(audio_files)} audio files")
        
        cls_count = 0
        for audio_path in audio_files:
            # Get audio duration
            try:
                y, sr = librosa.load(str(audio_path), sr=SAMPLE_RATE)
                duration = len(y) / sr
                num_windows = int(duration / WINDOW_SECONDS)
            except Exception as e:
                print(f"   ❌ Cannot load {audio_path.name}: {e}")
                continue
            
            # Generate spectrogram for each window
            for window_idx in range(max(1, num_windows)):
                output_name = f"{audio_path.stem}_w{window_idx:03d}.png"
                output_path = cls_output_dir / output_name
                
                if output_path.exists():
                    continue
                
                if audio_to_spectrogram(audio_path, output_path, window_idx):
                    cls_count += 1
                    total_generated += 1
        
        print(f"   ✓ Generated {cls_count} spectrograms")
    
    print(f"\n" + "=" * 60)
    print(f"✅ Complete! Generated {total_generated} spectrograms")
    print(f"   Output directory: {OUTPUT_DIR}")
    print("=" * 60)
    
    # Show counts per class
    print(f"\n📊 Summary:")
    for cls in CLASSES:
        cls_dir = OUTPUT_DIR / cls
        if cls_dir.exists():
            count = len(list(cls_dir.glob("*.png")))
            status = "✓" if count >= 50 else "⚠️ Need more" if count > 0 else "❌"
            print(f"   {status} {cls}: {count} images" + (" (min 50 recommended)" if count < 50 else ""))
    
    print(f"\n📤 Next step: Upload to Custom Vision")
    print(f"   python scripts/upload_custom_vision.py")


if __name__ == "__main__":
    main()
