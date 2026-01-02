/*
 * audio_capture.h - Forest Guardian Audio Capture Handler
 * For INMP441 I2S MEMS Microphone
 */
#ifndef AUDIO_CAPTURE_H
#define AUDIO_CAPTURE_H

#include <Arduino.h>

// Initialize audio capture
bool audio_capture_init();

// Read audio samples into buffer
bool audio_capture_read(int16_t *buffer, size_t len);

// Get audio statistics
float audio_get_rms();
float audio_get_peak();

// Check if audio system is ready
bool audio_is_ready();

#endif // AUDIO_CAPTURE_H
