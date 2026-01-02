"""
preprocess.py - Convert audio files to mel spectrograms for Forest Guardian ML pipeline.
"""
import os
from pathlib import Path
import numpy as np
import librosa
import soundfile as sf
from typing import Tuple, List

SAMPLE_RATE = 16000
N_MELS = 40
N_FFT = 512
HOP_LENGTH = 256
DURATION = 1.0  # seconds
N_FRAMES = 32

# Supported audio formats
AUDIO_EXTENSIONS = ['*.wav', '*.mp3', '*.flac', '*.ogg', '*.m4a']


def audio_to_mel(file_path: Path) -> np.ndarray:
    """Convert audio file to mel spectrogram."""
    y, sr = librosa.load(file_path, sr=SAMPLE_RATE, mono=True, duration=DURATION)
    if len(y) < int(SAMPLE_RATE * DURATION):
        y = np.pad(y, (0, int(SAMPLE_RATE * DURATION) - len(y)))
    mel = librosa.feature.melspectrogram(y=y, sr=sr, n_fft=N_FFT, hop_length=HOP_LENGTH, n_mels=N_MELS)
    mel_db = librosa.power_to_db(mel, ref=np.max)
    # Resize to (N_MELS, N_FRAMES)
    if mel_db.shape[1] < N_FRAMES:
        mel_db = np.pad(mel_db, ((0,0),(0,N_FRAMES-mel_db.shape[1])), mode='constant')
    mel_db = mel_db[:,:N_FRAMES]
    return mel_db.astype(np.float32)


def get_audio_files(src_dir: Path) -> List[Path]:
    """Get all audio files from a directory."""
    files = []
    for ext in AUDIO_EXTENSIONS:
        files.extend(src_dir.glob(ext))
    return files


def process_folder(src_dir: Path, out_dir: Path, label: int):
    """Process all audio files in a folder to mel spectrograms."""
    out_dir.mkdir(parents=True, exist_ok=True)
    audio_files = get_audio_files(src_dir)
    
    if not audio_files:
        print(f"  No audio files found in {src_dir}")
        return
    
    print(f"  Found {len(audio_files)} audio files")
    processed = 0
    
    for audio_file in audio_files:
        try:
            mel = audio_to_mel(audio_file)
            out_path = out_dir / (audio_file.stem + '.npy')
            np.save(out_path, mel)
            processed += 1
            if processed % 10 == 0:
                print(f"  Processed {processed}/{len(audio_files)} files...")
        except Exception as e:
            print(f"  Error processing {audio_file.name}: {e}")
    
    print(f"  Completed: {processed}/{len(audio_files)} files saved to {out_dir}")


def main():
    base = Path(__file__).parent.parent / 'data'
    out_base = Path(__file__).parent.parent / 'processed'
    
    print("=" * 60)
    print("Forest Guardian - Audio Preprocessing")
    print("=" * 60)
    
    print("\nProcessing CHAINSAW sounds...")
    process_folder(base / 'chainsaw', out_base / 'chainsaw', 1)
    
    print("\nProcessing FOREST ambient sounds...")
    process_folder(base / 'forest', out_base / 'forest', 0)
    
    print("\nProcessing HARD NEGATIVE sounds...")
    process_folder(base / 'hard_negatives', out_base / 'hard_negatives', 0)
    
    print("\n" + "=" * 60)
    print("Preprocessing complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
    main()
