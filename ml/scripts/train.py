"""
train.py - Train CNN model for chainsaw detection (Forest Guardian)
"""
import os
from pathlib import Path
import numpy as np
import tensorflow as tf
from tensorflow import keras
from sklearn.model_selection import train_test_split
from typing import Tuple

DATA_DIR = Path(__file__).parent.parent / 'processed'
MODEL_DIR = Path(__file__).parent.parent / 'models'
MODEL_DIR.mkdir(exist_ok=True)

N_MELS = 40
N_FRAMES = 32
BATCH_SIZE = 32
EPOCHS = 30


def load_data() -> Tuple[np.ndarray, np.ndarray]:
    X, y = [], []
    for label, folder in [(1, 'chainsaw'), (0, 'forest'), (0, 'hard_negatives')]:
        for npy in (DATA_DIR / folder).glob('*.npy'):
            X.append(np.load(npy))
            y.append(label)
    X = np.array(X)
    y = np.array(y)
    X = X[..., np.newaxis]  # (samples, 40, 32, 1)
    return X, y

def augment(X, y):
    # Simple augmentation: add Gaussian noise
    noise = np.random.normal(0, 0.1, X.shape)
    X_aug = X + noise
    return np.concatenate([X, X_aug]), np.concatenate([y, y])

def build_model():
    model = keras.Sequential([
        keras.layers.Input(shape=(N_MELS, N_FRAMES, 1)),
        keras.layers.Conv2D(8, (3,3), activation='relu', padding='same'),
        keras.layers.MaxPooling2D((2,2)),
        keras.layers.Conv2D(16, (3,3), activation='relu', padding='same'),
        keras.layers.MaxPooling2D((2,2)),
        keras.layers.Conv2D(32, (3,3), activation='relu', padding='same'),
        keras.layers.GlobalAveragePooling2D(),
        keras.layers.Dense(16, activation='relu'),
        keras.layers.Dense(1, activation='sigmoid')
    ])
    model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])
    return model

def main():
    X, y = load_data()
    X, y = augment(X, y)
    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42)
    model = build_model()
    callbacks = [keras.callbacks.EarlyStopping(patience=5, restore_best_weights=True)]
    model.fit(X_train, y_train, validation_data=(X_val, y_val), batch_size=BATCH_SIZE, epochs=EPOCHS, callbacks=callbacks)
    model.save(MODEL_DIR / 'chainsaw_cnn.h5')
    print(f"Model saved to {MODEL_DIR / 'chainsaw_cnn.h5'}")

if __name__ == "__main__":
    main()
