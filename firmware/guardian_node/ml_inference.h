/*
 * ml_inference.h - Forest Guardian Edge AI
 * FFT-based chainsaw detection with Azure integration ready
 *
 * Architecture for Imagine Cup:
 * - EDGE: FFT spectral analysis (real-time, <50ms latency)
 * - CLOUD: Azure Custom Vision verification
 * - IOT: Azure IoT Hub for alerts & telemetry
 */
#ifndef ML_INFERENCE_H
#define ML_INFERENCE_H

#include <Arduino.h>

// Initialize Edge AI inference engine
bool ml_inference_init();

// Run inference on audio buffer, returns confidence (0.0 - 1.0)
float ml_inference_run(const int16_t *audio, size_t len);

// Get last inference time in milliseconds
uint32_t ml_get_inference_time();

// Check if ML engine is ready
bool ml_is_ready();

// Get spectral features for Azure Custom Vision cloud verification
void ml_get_spectral_features(float *features, int max_features);

#endif // ML_INFERENCE_H
