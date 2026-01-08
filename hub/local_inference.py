# local_inference.py - Forest Guardian Hub
# Offline Spectrogram Analysis using TFLite on Raspberry Pi
# Supports BOTH Azure Custom Vision exports AND local trained models

import os
import logging
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
import base64
from io import BytesIO

logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURATION
# =============================================================================
MODEL_PATH = Path(__file__).parent.parent / 'ml' / 'models' / 'chainsaw_classifier.tflite'
LABELS_PATH = Path(__file__).parent.parent / 'ml' / 'models' / 'labels.txt'

# Default labels (overridden by labels.txt if present)
DEFAULT_LABELS = ['chainsaw', 'nature', 'vehicle']

# Azure Custom Vision export uses 224x224 RGB images
# Local training may use different dimensions
AZURE_CV_INPUT_SIZE = (224, 224)  # Width, Height
AZURE_CV_CHANNELS = 3  # RGB

# Spectrogram parameters for local model (if not using Azure CV export)
N_MELS = 40
N_FRAMES = 32
SAMPLE_RATE = 16000
HOP_LENGTH = 512
N_FFT = 1024

# Detection thresholds
CHAINSAW_THRESHOLD = 0.60  # 60% confidence for chainsaw detection
VEHICLE_THRESHOLD = 0.70   # 70% confidence for vehicle detection

# Model type detection
_model_type = None  # 'azure_cv' or 'local'
_labels = None  # Loaded from labels.txt or default

# =============================================================================
# TFLITE INTERPRETER (Lazy loaded)
# =============================================================================
_interpreter = None
_input_details = None
_output_details = None

def _load_labels():
    """Load labels from labels.txt (Azure CV export) or use defaults"""
    global _labels
    
    if LABELS_PATH.exists():
        with open(LABELS_PATH, 'r') as f:
            _labels = [line.strip() for line in f.readlines() if line.strip()]
        logger.info(f"Loaded labels from {LABELS_PATH}: {_labels}")
    else:
        _labels = DEFAULT_LABELS
        logger.info(f"Using default labels: {_labels}")
    
    return _labels


def _detect_model_type():
    """Detect if model is Azure Custom Vision export or local training"""
    global _model_type
    
    if not _load_interpreter():
        return None
    
    input_shape = _input_details[0]['shape']
    
    # Azure CV exports typically have shape (1, 224, 224, 3)
    if len(input_shape) == 4 and input_shape[1] == 224 and input_shape[2] == 224 and input_shape[3] == 3:
        _model_type = 'azure_cv'
        logger.info("Detected Azure Custom Vision model (224x224 RGB)")
    else:
        _model_type = 'local'
        logger.info(f"Detected local model with shape {input_shape}")
    
    return _model_type


def _load_interpreter():
    """Load TFLite interpreter (lazy initialization)"""
    global _interpreter, _input_details, _output_details
    
    if _interpreter is not None:
        return True
    
    if not MODEL_PATH.exists():
        logger.error(f"TFLite model not found at {MODEL_PATH}")
        logger.info("Export from Azure Custom Vision or run local training")
        logger.info("See docs/AZURE_CUSTOM_VISION_TRAINING.md for instructions")
        return False
    
    try:
        # Try AI Edge LiteRT first (Google's new TFLite replacement, Python 3.13 compatible)
        try:
            from ai_edge_litert.interpreter import Interpreter
            _interpreter = Interpreter(model_path=str(MODEL_PATH))
            logger.info("Using AI Edge LiteRT for inference")
        except ImportError:
            # Try tflite_runtime
            try:
                import tflite_runtime.interpreter as tflite
                _interpreter = tflite.Interpreter(model_path=str(MODEL_PATH))
                logger.info("Using tflite_runtime for inference")
            except ImportError:
                # Fall back to full TensorFlow
                import tensorflow as tf
                _interpreter = tf.lite.Interpreter(model_path=str(MODEL_PATH))
                logger.info("Using TensorFlow for inference")
        
        _interpreter.allocate_tensors()
        _input_details = _interpreter.get_input_details()
        _output_details = _interpreter.get_output_details()
        
        logger.info(f"TFLite model loaded: {MODEL_PATH}")
        logger.info(f"Input shape: {_input_details[0]['shape']}")
        logger.info(f"Output shape: {_output_details[0]['shape']}")
        
        # Load labels and detect model type
        _load_labels()
        _detect_model_type()
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to load TFLite model: {e}")
        return False


def is_local_inference_available() -> bool:
    """Check if local inference is available"""
    return _load_interpreter()


# =============================================================================
# IMAGE PREPROCESSING FOR AZURE CUSTOM VISION
# =============================================================================
def preprocess_for_azure_cv(image_path: str) -> Optional[np.ndarray]:
    """
    Preprocess image for Azure Custom Vision TFLite model
    
    Azure CV expects:
    - 224x224 RGB image
    - RAW 0-255 pixel values (NOT normalized to 0-1)
    - Shape: (1, 224, 224, 3)
    - dtype: float32
    """
    try:
        from PIL import Image
        
        # Load and convert to RGB
        img = Image.open(image_path).convert('RGB')
        
        # Resize to 224x224
        img = img.resize(AZURE_CV_INPUT_SIZE, Image.Resampling.LANCZOS)
        
        # Convert to numpy array - Azure CV uses 0-255 range (NOT normalized)
        img_array = np.array(img, dtype=np.float32)
        
        # Add batch dimension
        img_array = np.expand_dims(img_array, axis=0)
        
        return img_array
        
    except Exception as e:
        logger.error(f"Error preprocessing image for Azure CV: {e}")
        return None


def preprocess_base64_for_azure_cv(base64_data: str) -> Optional[np.ndarray]:
    """
    Preprocess base64 image for Azure Custom Vision TFLite model
    
    Azure CV expects:
    - 224x224 RGB image
    - RAW 0-255 pixel values (NOT normalized to 0-1)
    - Shape: (1, 224, 224, 3)
    - dtype: float32
    """
    try:
        from PIL import Image
        
        # Decode base64
        image_data = base64.b64decode(base64_data)
        img = Image.open(BytesIO(image_data)).convert('RGB')
        
        # Resize to 224x224
        img = img.resize(AZURE_CV_INPUT_SIZE, Image.Resampling.LANCZOS)
        
        # Convert to numpy array - Azure CV uses 0-255 range (NOT normalized)
        img_array = np.array(img, dtype=np.float32)
        
        # Add batch dimension
        img_array = np.expand_dims(img_array, axis=0)
        
        return img_array
        
    except Exception as e:
        logger.error(f"Error preprocessing base64 for Azure CV: {e}")
        return None


def preprocess_raw_spectrogram_for_azure_cv(raw_data: bytes, width: int, height: int) -> Optional[np.ndarray]:
    """
    Preprocess raw grayscale spectrogram data from LoRa node for Azure CV model
    
    Nodes send spectrograms as raw grayscale bytes. We need to:
    1. Convert to RGB (Azure CV expects 3 channels)
    2. Resize to 224x224
    3. Use 0-255 pixel values
    
    Args:
        raw_data: Raw bytes of grayscale spectrogram
        width: Original width
        height: Original height
        
    Returns:
        Preprocessed array ready for Azure CV model
    """
    try:
        from PIL import Image
        
        # Create grayscale image from raw bytes
        img = Image.frombytes('L', (width, height), raw_data)
        
        # Convert grayscale to RGB (replicates across channels)
        img = img.convert('RGB')
        
        # Resize to 224x224
        img = img.resize(AZURE_CV_INPUT_SIZE, Image.Resampling.LANCZOS)
        
        # Convert to numpy array - Azure CV uses 0-255 range
        img_array = np.array(img, dtype=np.float32)
        
        # Add batch dimension: (1, 224, 224, 3)
        img_array = np.expand_dims(img_array, axis=0)
        
        return img_array
        
    except Exception as e:
        logger.error(f"Error preprocessing raw spectrogram for Azure CV: {e}")
        return None


def preprocess_pgm_for_azure_cv(pgm_path: str) -> Optional[np.ndarray]:
    """
    Preprocess PGM (grayscale) spectrogram file for Azure CV model
    
    Handles both proper PGM files and compressed ones from LoRa nodes.
    Azure CV model expects RGB, so converts grayscale by replicating channels.
    
    Args:
        pgm_path: Path to PGM file
        
    Returns:
        Preprocessed array ready for Azure CV model, or None on error
    """
    try:
        from PIL import Image
        
        # First try standard PIL loading
        try:
            img = Image.open(pgm_path)
            # Force load to detect errors early
            img.load()
        except (ValueError, IOError) as e:
            # File might be corrupted or compressed - try manual parsing
            logger.warning(f"Standard PGM load failed, trying manual parse: {e}")
            img = _parse_pgm_manual(pgm_path)
            if img is None:
                return None
        
        # Convert to RGB (replicates grayscale across channels)
        img = img.convert('RGB')
        
        # Resize to 224x224
        img = img.resize(AZURE_CV_INPUT_SIZE, Image.Resampling.LANCZOS)
        
        # Convert to numpy array - Azure CV uses 0-255 range
        img_array = np.array(img, dtype=np.float32)
        
        # Add batch dimension: (1, 224, 224, 3)
        img_array = np.expand_dims(img_array, axis=0)
        
        return img_array
        
    except Exception as e:
        logger.error(f"Error preprocessing PGM for Azure CV: {e}")
        return None


def _parse_pgm_manual(pgm_path: str) -> Optional['Image.Image']:
    """
    Manually parse a PGM file that PIL can't read
    Some PGM files from LoRa nodes might be compressed or malformed
    """
    try:
        from PIL import Image
        
        with open(pgm_path, 'rb') as f:
            content = f.read()
        
        # Check magic number
        if not content.startswith(b'P5'):
            logger.error("Not a P5 PGM file")
            return None
        
        # Parse header (skip comments)
        lines = content.split(b'\n')
        idx = 1
        while idx < len(lines) and lines[idx].startswith(b'#'):
            idx += 1
        
        # Get dimensions
        dims = lines[idx].decode().split()
        width, height = int(dims[0]), int(dims[1])
        
        # Get max value
        idx += 1
        max_val = int(lines[idx].decode())
        
        # Find where header ends
        header_end = content.find(b'\n', content.find(b'\n', content.find(b'\n') + 1) + 1) + 1
        
        # Get pixel data
        pixel_data = content[header_end:]
        expected_size = width * height
        
        if len(pixel_data) == expected_size:
            # Proper PGM - create image directly
            arr = np.frombuffer(pixel_data, dtype=np.uint8).reshape((height, width))
        elif len(pixel_data) < expected_size:
            # Compressed or truncated - pad with zeros
            logger.warning(f"PGM pixel data truncated: {len(pixel_data)} < {expected_size}")
            arr = np.zeros((height, width), dtype=np.uint8)
            flat = np.frombuffer(pixel_data, dtype=np.uint8)
            arr.flat[:len(flat)] = flat
        else:
            # Too much data - truncate
            arr = np.frombuffer(pixel_data[:expected_size], dtype=np.uint8).reshape((height, width))
        
        return Image.fromarray(arr, mode='L')
        
    except Exception as e:
        logger.error(f"Manual PGM parsing failed: {e}")
        return None


# =============================================================================
# SPECTROGRAM GENERATION (for local model)
# =============================================================================
def generate_spectrogram_from_audio(audio_data: np.ndarray, sr: int = SAMPLE_RATE) -> Optional[np.ndarray]:
    """
    Generate mel spectrogram from audio data
    
    Args:
        audio_data: Raw audio samples (numpy array)
        sr: Sample rate
    
    Returns:
        Mel spectrogram as numpy array (N_MELS x N_FRAMES)
    """
    try:
        import librosa
        
        # Ensure audio is the right length (~1 second)
        target_length = sr  # 1 second
        if len(audio_data) < target_length:
            # Pad with zeros
            audio_data = np.pad(audio_data, (0, target_length - len(audio_data)))
        elif len(audio_data) > target_length:
            # Take center portion
            start = (len(audio_data) - target_length) // 2
            audio_data = audio_data[start:start + target_length]
        
        # Generate mel spectrogram
        mel_spec = librosa.feature.melspectrogram(
            y=audio_data.astype(np.float32),
            sr=sr,
            n_mels=N_MELS,
            n_fft=N_FFT,
            hop_length=HOP_LENGTH
        )
        
        # Convert to dB scale
        mel_spec_db = librosa.power_to_db(mel_spec, ref=np.max)
        
        # Normalize to 0-1 range
        mel_spec_norm = (mel_spec_db - mel_spec_db.min()) / (mel_spec_db.max() - mel_spec_db.min() + 1e-8)
        
        # Resize to expected dimensions
        if mel_spec_norm.shape[1] != N_FRAMES:
            from scipy.ndimage import zoom
            zoom_factor = N_FRAMES / mel_spec_norm.shape[1]
            mel_spec_norm = zoom(mel_spec_norm, (1, zoom_factor))
        
        return mel_spec_norm[:N_MELS, :N_FRAMES]
        
    except ImportError:
        logger.error("librosa not installed. Run: pip install librosa")
        return None
    except Exception as e:
        logger.error(f"Error generating spectrogram: {e}")
        return None


def load_spectrogram_from_image(image_path: str) -> Optional[np.ndarray]:
    """
    Load spectrogram from PNG image file
    
    Args:
        image_path: Path to spectrogram PNG image
    
    Returns:
        Spectrogram as numpy array (N_MELS x N_FRAMES)
    """
    try:
        from PIL import Image
        
        img = Image.open(image_path).convert('L')  # Grayscale
        img = img.resize((N_FRAMES, N_MELS))  # Resize to expected dimensions
        
        # Convert to numpy and normalize
        spec = np.array(img, dtype=np.float32) / 255.0
        
        return spec
        
    except Exception as e:
        logger.error(f"Error loading spectrogram image: {e}")
        return None


def load_spectrogram_from_base64(base64_data: str) -> Optional[np.ndarray]:
    """
    Load spectrogram from base64-encoded image
    
    Args:
        base64_data: Base64-encoded PNG image
    
    Returns:
        Spectrogram as numpy array (N_MELS x N_FRAMES)
    """
    try:
        from PIL import Image
        
        # Decode base64
        image_data = base64.b64decode(base64_data)
        img = Image.open(BytesIO(image_data)).convert('L')
        img = img.resize((N_FRAMES, N_MELS))
        
        spec = np.array(img, dtype=np.float32) / 255.0
        return spec
        
    except Exception as e:
        logger.error(f"Error loading spectrogram from base64: {e}")
        return None


# =============================================================================
# LOCAL INFERENCE
# =============================================================================
def run_local_inference(input_data: np.ndarray) -> Dict[str, Any]:
    """
    Run inference using local TFLite model
    
    Args:
        input_data: Preprocessed input data matching model's expected shape
                   - For Azure CV: (1, 224, 224, 3) float32 in 0-255 range
                   - For local model: (1, N_MELS, N_FRAMES, 1) float32 normalized
    
    Returns:
        Dictionary with classification results
    """
    result = {
        "success": False,
        "classification": "unknown",
        "confidence": 0,
        "threat_level": "NONE",
        "service": "local_tflite",
        "all_predictions": [],
        "inference_time_ms": 0,
        "offline": True
    }
    
    if not _load_interpreter():
        result["error"] = "TFLite model not available"
        return result
    
    try:
        import time
        start_time = time.time()
        
        # Ensure correct dtype
        input_data = input_data.astype(np.float32)
        
        # Get expected input shape
        expected_shape = tuple(_input_details[0]['shape'])
        current_shape = input_data.shape
        
        # Handle shape matching
        if current_shape == expected_shape:
            # Shape already matches - good to go
            pass
        elif _model_type == 'azure_cv' and len(current_shape) == 4 and current_shape == expected_shape:
            # Azure CV input already properly shaped
            pass
        elif len(current_shape) == 2:
            # Local grayscale model - add batch and channel dimensions
            input_data = input_data[np.newaxis, ..., np.newaxis]  # (1, H, W, 1)
            if input_data.shape != expected_shape:
                try:
                    input_data = input_data.reshape(expected_shape)
                except ValueError:
                    result["error"] = f"Cannot reshape {current_shape} to {expected_shape}"
                    return result
        else:
            logger.warning(f"Input shape mismatch: {current_shape} vs expected {expected_shape}")
            try:
                input_data = input_data.reshape(expected_shape)
            except ValueError:
                result["error"] = f"Cannot reshape {current_shape} to {expected_shape}"
                return result
        
        # Run inference
        _interpreter.set_tensor(_input_details[0]['index'], input_data)
        _interpreter.invoke()
        
        # Get output
        output = _interpreter.get_tensor(_output_details[0]['index'])
        
        inference_time = (time.time() - start_time) * 1000
        result["inference_time_ms"] = round(inference_time, 2)
        result["model_type"] = _model_type
        
        # Get labels
        labels = _labels or DEFAULT_LABELS
        
        # Interpret output
        if len(output.shape) == 2 and output.shape[1] == 1:
            # Binary classification (sigmoid output)
            chainsaw_prob = float(output[0][0])
            nature_prob = 1.0 - chainsaw_prob
            
            result["all_predictions"] = [
                {"tag": "chainsaw", "confidence": int(chainsaw_prob * 100)},
                {"tag": "nature", "confidence": int(nature_prob * 100)}
            ]
            
            if chainsaw_prob >= CHAINSAW_THRESHOLD:
                result["classification"] = "chainsaw"
                result["confidence"] = int(chainsaw_prob * 100)
            else:
                result["classification"] = "nature"
                result["confidence"] = int(nature_prob * 100)
                
        elif len(output.shape) == 2 and output.shape[1] >= 2:
            # Multi-class classification (softmax output) - Azure CV format
            probs = output[0]
            
            # Apply softmax if needed (check if already normalized)
            if not np.isclose(probs.sum(), 1.0, atol=0.1):
                exp_probs = np.exp(probs - np.max(probs))
                probs = exp_probs / exp_probs.sum()
            
            # Build predictions using loaded labels
            num_classes = min(len(probs), len(labels))
            result["all_predictions"] = [
                {"tag": labels[i], "confidence": int(probs[i] * 100)}
                for i in range(num_classes)
            ]
            result["all_predictions"].sort(key=lambda x: -x["confidence"])
            
            top_idx = np.argmax(probs[:num_classes])
            result["classification"] = labels[top_idx]
            result["confidence"] = int(probs[top_idx] * 100)
        else:
            # Single value output
            chainsaw_prob = float(output.flatten()[0])
            result["classification"] = "chainsaw" if chainsaw_prob >= CHAINSAW_THRESHOLD else "nature"
            result["confidence"] = int(chainsaw_prob * 100) if chainsaw_prob >= 0.5 else int((1 - chainsaw_prob) * 100)
        
        result["success"] = True
        
        # Set threat level based on classification
        if result["classification"] == "chainsaw":
            if result["confidence"] >= 80:
                result["threat_level"] = "CRITICAL"
            elif result["confidence"] >= 60:
                result["threat_level"] = "HIGH"
            else:
                result["threat_level"] = "MEDIUM"
        elif result["classification"] == "vehicle":
            result["threat_level"] = "MEDIUM" if result["confidence"] >= 70 else "LOW"
        else:
            result["threat_level"] = "NONE"
        
        logger.info(f"Local inference ({_model_type}): {result['classification']} ({result['confidence']}%) in {inference_time:.1f}ms")
        
    except Exception as e:
        result["error"] = f"Inference error: {str(e)}"
        logger.error(result["error"])
    
    return result


def analyze_spectrogram_local(image_path: str) -> Dict[str, Any]:
    """
    Analyze spectrogram image using local TFLite model
    Handles both PNG and PGM formats from nodes
    
    Args:
        image_path: Path to spectrogram image (PNG or PGM)
    
    Returns:
        Dictionary with classification results
    """
    if not _load_interpreter():
        return {
            "success": False,
            "error": "TFLite model not available",
            "service": "local_tflite"
        }
    
    # Check if file exists
    if not os.path.exists(image_path):
        return {
            "success": False,
            "error": f"File not found: {image_path}",
            "service": "local_tflite"
        }
    
    # Use appropriate preprocessing based on model type
    if _model_type == 'azure_cv':
        # Azure CV needs RGB - use special handling for PGM files
        if image_path.lower().endswith('.pgm'):
            input_data = preprocess_pgm_for_azure_cv(image_path)
        else:
            input_data = preprocess_for_azure_cv(image_path)
            
        if input_data is None:
            return {
                "success": False,
                "error": "Failed to preprocess image for Azure CV",
                "service": "local_tflite"
            }
        return run_local_inference(input_data)
    else:
        # Local model - use grayscale spectrogram
        spectrogram = load_spectrogram_from_image(image_path)
        if spectrogram is None:
            return {
                "success": False,
                "error": "Failed to load spectrogram image",
                "service": "local_tflite"
            }
        return run_local_inference(spectrogram)


def analyze_spectrogram_base64_local(base64_data: str) -> Dict[str, Any]:
    """
    Analyze base64-encoded spectrogram using local TFLite model
    Automatically detects if Azure CV or local model format
    
    Args:
        base64_data: Base64-encoded PNG image
    
    Returns:
        Dictionary with classification results
    """
    if not _load_interpreter():
        return {
            "success": False,
            "error": "TFLite model not available",
            "service": "local_tflite"
        }
    
    # Use appropriate preprocessing based on model type
    if _model_type == 'azure_cv':
        input_data = preprocess_base64_for_azure_cv(base64_data)
        if input_data is None:
            return {
                "success": False,
                "error": "Failed to preprocess image for Azure CV",
                "service": "local_tflite"
            }
        return run_local_inference(input_data)
    else:
        # Local model - use grayscale spectrogram
        spectrogram = load_spectrogram_from_base64(base64_data)
        if spectrogram is None:
            return {
                "success": False,
                "error": "Failed to decode spectrogram image",
                "service": "local_tflite"
            }
        return run_local_inference(spectrogram)


# =============================================================================
# MODEL INFO
# =============================================================================
def get_model_info() -> Dict[str, Any]:
    """Get information about the local model"""
    info = {
        "available": False,
        "model_path": str(MODEL_PATH),
        "labels_path": str(LABELS_PATH),
        "labels": _labels or DEFAULT_LABELS,
        "model_type": _model_type,
        "input_shape": None,
        "thresholds": {
            "chainsaw": CHAINSAW_THRESHOLD,
            "vehicle": VEHICLE_THRESHOLD
        }
    }
    
    if _load_interpreter():
        info["available"] = True
        info["model_type"] = _model_type
        info["labels"] = _labels or DEFAULT_LABELS
        info["input_shape"] = list(_input_details[0]['shape'])
        info["input_dtype"] = str(_input_details[0]['dtype'])
        info["output_shape"] = list(_output_details[0]['shape'])
    
    return info


# =============================================================================
# TESTING
# =============================================================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("=" * 60)
    print("🌲 Forest Guardian - Local Inference Test")
    print("=" * 60)
    
    model_info = get_model_info()
    print(f"\nModel available: {model_info['available']}")
    print(f"Model path: {model_info['model_path']}")
    print(f"Model type: {model_info.get('model_type', 'unknown')}")
    print(f"Labels: {model_info['labels']}")
    
    if model_info['available']:
        print(f"Input shape: {model_info['input_shape']}")
        print(f"Output shape: {model_info.get('output_shape')}")
        
        # Test with sample spectrogram images
        test_dirs = [
            ('chainsaw', Path(__file__).parent.parent / 'ml' / 'training_images' / 'chainsaw'),
            ('nature', Path(__file__).parent.parent / 'ml' / 'training_images' / 'nature'),
        ]
        
        for expected_class, test_dir in test_dirs:
            if test_dir.exists():
                test_images = list(test_dir.glob('*.png'))[:2]
                print(f"\n📁 Testing {expected_class} images ({len(test_images)} samples):")
                
                for test_image in test_images:
                    result = analyze_spectrogram_local(str(test_image))
                    status = "✅" if result.get('classification') == expected_class else "❌"
                    print(f"  {status} {test_image.name[:40]}...")
                    print(f"     → {result.get('classification', 'error')} ({result.get('confidence', 0)}%)")
                    if 'inference_time_ms' in result:
                        print(f"     → {result['inference_time_ms']}ms inference time")
    else:
        print("\n⚠️ Model not available!")
        print("\nTo set up the model:")
        print("1. Train on Azure Custom Vision (see docs/AZURE_CUSTOM_VISION_TRAINING.md)")
        print("2. Export as TensorFlow Lite")
        print("3. Copy model.tflite to: ml/models/chainsaw_classifier.tflite")
        print("4. Copy labels.txt to: ml/models/labels.txt")

