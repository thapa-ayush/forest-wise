/*
 * spectrogram.h - Forest Guardian Spectrogram Generator
 * Generates 64x64 grayscale spectrogram images from audio
 * For Azure AI Vision classification
 */
#ifndef SPECTROGRAM_H
#define SPECTROGRAM_H

#include <Arduino.h>

// Spectrogram dimensions (reduced for ESP32 memory)
#define SPEC_WIDTH 32
#define SPEC_HEIGHT 32
#define SPEC_SIZE (SPEC_WIDTH * SPEC_HEIGHT) // 1024 bytes raw

// FFT parameters (reduced for memory)
#define FFT_SIZE 128
#define FFT_HOP 64
#define NUM_MEL_BINS 32

// JPEG compression target size (for LoRa transmission)
#define JPEG_TARGET_SIZE 800 // ~800 bytes compressed

// Initialize spectrogram generator
bool spectrogram_init();

// Generate spectrogram from audio buffer
// Input: 16-bit audio samples at 16kHz, ~1 second
// Output: 64x64 grayscale image in spec_out
bool spectrogram_generate(const int16_t *audio, size_t audio_len, uint8_t *spec_out);

// Compress spectrogram to JPEG
// Returns compressed size, 0 on failure
size_t spectrogram_to_jpeg(const uint8_t *spec_in, uint8_t *jpeg_out, size_t max_out_size);

// Get the last spectrogram as base64 for debug
String spectrogram_to_base64(const uint8_t *spec, size_t len);

// Calculate RMS level from spectrogram (for anomaly detection)
float spectrogram_get_energy(const uint8_t *spec);

// Simple threshold-based anomaly detection
// Returns true if spectrogram shows unusual activity
bool spectrogram_is_anomaly(const uint8_t *spec, float threshold = 0.3f);

#endif
