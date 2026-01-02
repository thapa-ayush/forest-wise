/*
 * ml_inference.cpp - Forest Guardian Edge AI
 *
 * Edge Impulse ML Model for Chainsaw Detection
 * Trained on 4000+ audio samples with 85.1% accuracy
 *
 * Model specs:
 * - Inference time: 3ms
 * - RAM usage: 12.5KB
 * - Flash size: 45.7KB
 */

#include "ml_inference.h"
#include "config.h"

// Edge Impulse library
#include <forest-guardian-chainsaw_inferencing.h>

namespace
{
    bool ml_ready = false;
    uint32_t last_inference_time = 0;
    float smoothed_confidence = 0.0f;
    static unsigned long last_debug = 0;

    // Consecutive detection counter for robust alerting
    // Real chainsaws produce sustained loud sounds
    int consecutive_detections = 0;

    // Inference buffer
    float features[EI_CLASSIFIER_DSP_INPUT_FRAME_SIZE];
}

// Callback function for Edge Impulse to get audio data
static int get_audio_signal_data(size_t offset, size_t length, float *out_ptr)
{
    // Data is already in features buffer, just copy
    for (size_t i = 0; i < length; i++)
    {
        out_ptr[i] = features[offset + i];
    }
    return 0;
}

bool ml_inference_init()
{
    Serial.println("[ML] Initializing Edge Impulse classifier...");
    Serial.println("[ML] Model: Forest Guardian Chainsaw Detection");
    Serial.print("[ML] DSP input size: ");
    Serial.println(EI_CLASSIFIER_DSP_INPUT_FRAME_SIZE);
    Serial.print("[ML] Label count: ");
    Serial.println(EI_CLASSIFIER_LABEL_COUNT);
    Serial.print("[ML] Labels: ");
    for (size_t i = 0; i < EI_CLASSIFIER_LABEL_COUNT; i++)
    {
        Serial.print(ei_classifier_inferencing_categories[i]);
        if (i < EI_CLASSIFIER_LABEL_COUNT - 1)
            Serial.print(", ");
    }
    Serial.println();

    ml_ready = true;
    Serial.println("[ML] Edge Impulse initialized - 85.1% accuracy model");
    return true;
}

float ml_inference_run(const int16_t *audio, size_t len)
{
    if (!ml_ready)
    {
        return 0.0f;
    }

    uint32_t start_time = millis();
    bool do_debug = (millis() - last_debug > 3000);
    if (do_debug)
        last_debug = millis();

    // Calculate stats for debug
    size_t feature_len = min(len, (size_t)EI_CLASSIFIER_DSP_INPUT_FRAME_SIZE);

    int32_t sum = 0;
    int16_t max_amp = 0;
    int16_t min_val = 32767;
    int16_t max_val = -32768;

    for (size_t i = 0; i < feature_len; i++)
    {
        sum += audio[i];
        if (audio[i] > max_val)
            max_val = audio[i];
        if (audio[i] < min_val)
            min_val = audio[i];
        if (abs(audio[i]) > max_amp)
            max_amp = abs(audio[i]);
    }
    int16_t dc_offset = sum / feature_len;

    // Convert audio to floats in -1.0 to 1.0 range
    // Remove DC offset since INMP441 has significant bias (~18%)
    // Training data (normalized WAVs) were centered around zero
    for (size_t i = 0; i < feature_len; i++)
    {
        features[i] = (float)(audio[i] - dc_offset) / 32768.0f;
    }

    // Debug: Print sample of feature values
    if (do_debug)
    {
        Serial.print("[ML] Feature samples: ");
        for (int i = 0; i < 10; i++)
        {
            Serial.print(features[i * 1600], 4); // Print every 1600th sample
            Serial.print(" ");
        }
        Serial.println();

        // Show DC-corrected range
        float feat_min = 1.0f, feat_max = -1.0f;
        for (size_t i = 0; i < feature_len; i++)
        {
            if (features[i] < feat_min)
                feat_min = features[i];
            if (features[i] > feat_max)
                feat_max = features[i];
        }
        Serial.print("[ML] Feature range: ");
        Serial.print(feat_min, 4);
        Serial.print(" to ");
        Serial.println(feat_max, 4);
    }
    // Zero-pad if needed
    for (size_t i = feature_len; i < EI_CLASSIFIER_DSP_INPUT_FRAME_SIZE; i++)
    {
        features[i] = 0.0f;
    }

    // Create signal from features buffer
    signal_t signal;
    signal.total_length = EI_CLASSIFIER_DSP_INPUT_FRAME_SIZE;
    signal.get_data = &get_audio_signal_data;

    // Run the classifier - enable debug every 5 seconds to see DSP output
    ei_impulse_result_t result = {0};
    static unsigned long last_ei_debug = 0;
    bool debug_classifier = (millis() - last_ei_debug > 5000);
    if (debug_classifier)
        last_ei_debug = millis();

    EI_IMPULSE_ERROR err = run_classifier(&signal, &result, debug_classifier);

    if (err != EI_IMPULSE_OK)
    {
        Serial.print("[ML] Classifier error: ");
        Serial.println(err);
        return 0.0f;
    }

    last_inference_time = millis() - start_time;

    // Find chainsaw confidence
    float chainsaw_confidence = 0.0f;
    float noise_confidence = 0.0f;

    for (size_t i = 0; i < EI_CLASSIFIER_LABEL_COUNT; i++)
    {
        if (strcmp(result.classification[i].label, "chainsaw") == 0)
        {
            chainsaw_confidence = result.classification[i].value;
        }
        else if (strcmp(result.classification[i].label, "noise") == 0)
        {
            noise_confidence = result.classification[i].value;
        }
    }

    // Robust detection: require consecutive detections to reduce false positives
    // TV sounds might trigger 1-2 detections but chainsaws are sustained
    if (chainsaw_confidence >= DETECTION_RAW_MIN) // Detection above threshold
    {
        consecutive_detections++;
        // Build up smoothed confidence when we have consecutive detections
        if (consecutive_detections >= CONSECUTIVE_REQUIRED)
        {
            smoothed_confidence = 0.8f * chainsaw_confidence + 0.2f * smoothed_confidence;
        }
        else
        {
            // Not enough consecutive yet - moderate buildup
            smoothed_confidence = 0.4f * chainsaw_confidence + 0.6f * smoothed_confidence;
        }
    }
    else // Weak or no detection - reset counter and decay
    {
        consecutive_detections = 0;
        smoothed_confidence = smoothed_confidence * 0.5f; // Fast decay
    }

    // Clamp consecutive to prevent overflow
    if (consecutive_detections > 10)
        consecutive_detections = 10;

    // Debug output
    if (do_debug)
    {
        Serial.print("[ML] Min:");
        Serial.print(min_val);
        Serial.print(" Max:");
        Serial.print(max_val);
        Serial.print(" DC:");
        Serial.print(dc_offset);
        Serial.print(" Saw:");
        Serial.print((int)(chainsaw_confidence * 100));
        Serial.print("% Cons:");
        Serial.print(consecutive_detections);
        Serial.print(" Smooth:");
        Serial.print((int)(smoothed_confidence * 100));
        Serial.print("% T:");
        Serial.print(last_inference_time);
        Serial.println("ms");
    }

    return smoothed_confidence;
}

uint32_t ml_get_inference_time()
{
    return last_inference_time;
}

bool ml_is_ready()
{
    return ml_ready;
}

void ml_get_spectral_features(float *out_features, int max_features)
{
    // Return recent features for Azure cloud verification if needed
    int num = min(max_features, (int)EI_CLASSIFIER_DSP_INPUT_FRAME_SIZE);
    for (int i = 0; i < num; i++)
    {
        out_features[i] = features[i];
    }
}
