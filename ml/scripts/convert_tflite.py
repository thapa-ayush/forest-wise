"""
convert_tflite.py - Convert Keras model to quantized TFLite and C header (Forest Guardian)
"""
import numpy as np
import tensorflow as tf
from pathlib import Path

MODEL_PATH = Path(__file__).parent.parent / 'models' / 'chainsaw_cnn.h5'
TFLITE_PATH = Path(__file__).parent.parent / 'models' / 'chainsaw_cnn_int8.tflite'
HEADER_PATH = Path(__file__).parent.parent / '..' / 'firmware' / 'guardian_node' / 'chainsaw_model.h'


def representative_dataset():
    # Dummy data for quantization (replace with real data for best results)
    for _ in range(100):
        data = np.random.rand(1, 40, 32, 1).astype(np.float32)
        yield [data]

def convert():
    model = tf.keras.models.load_model(MODEL_PATH)
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    converter.representative_dataset = representative_dataset
    converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
    converter.inference_input_type = tf.int8
    converter.inference_output_type = tf.int8
    tflite_model = converter.convert()
    with open(TFLITE_PATH, 'wb') as f:
        f.write(tflite_model)
    print(f"TFLite model saved: {TFLITE_PATH}")
    # Write as C array
    arr = np.frombuffer(tflite_model, dtype=np.uint8)
    with open(HEADER_PATH, 'w') as f:
        f.write('#ifndef CHAINSAW_MODEL_H\n#define CHAINSAW_MODEL_H\n\n')
        f.write(f'const unsigned char chainsaw_model[] = {{\n')
        for i, b in enumerate(arr):
            if i % 12 == 0:
                f.write('\n    ')
            f.write(f'0x{b:02x}, ')
        f.write('\n};\n')
        f.write(f'const unsigned int chainsaw_model_len = {len(arr)};\n')
        f.write('#endif // CHAINSAW_MODEL_H\n')
    print(f"C header saved: {HEADER_PATH}")

if __name__ == "__main__":
    convert()
