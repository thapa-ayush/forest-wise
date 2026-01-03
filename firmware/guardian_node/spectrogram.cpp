/*
 * spectrogram.cpp - Forest Guardian Spectrogram Generator
 * Generates mel-scale spectrograms for Azure AI Vision analysis
 * 
 * Instead of relying on Edge Impulse ML on ESP32, we:
 * 1. Generate a visual spectrogram from audio
 * 2. Compress it to JPEG (~800 bytes)
 * 3. Send over LoRa to hub
 * 4. Hub forwards to Azure OpenAI GPT-4o Vision for classification
 */

#include "spectrogram.h"
#include "config.h"
#include <arduinoFFT.h>
#include <math.h>

// TJpg_Encoder for JPEG compression (lightweight)
// We'll use a simple run-length encoding for initial version
// and can upgrade to proper JPEG later

namespace {
    // FFT buffers
    float vReal[FFT_SIZE];
    float vImag[FFT_SIZE];
    
    // Mel filterbank (precomputed)
    float mel_filterbank[NUM_MEL_BINS][FFT_SIZE/2];
    bool filterbank_initialized = false;
    
    // ArduinoFFT instance
    ArduinoFFT<float> FFT = ArduinoFFT<float>(vReal, vImag, FFT_SIZE, SAMPLE_RATE);
    
    // Hanning window
    float hanning_window[FFT_SIZE];
}

// Convert frequency to mel scale
float hz_to_mel(float hz) {
    return 2595.0f * log10f(1.0f + hz / 700.0f);
}

// Convert mel to frequency
float mel_to_hz(float mel) {
    return 700.0f * (powf(10.0f, mel / 2595.0f) - 1.0f);
}

// Initialize mel filterbank
void init_mel_filterbank() {
    if (filterbank_initialized) return;
    
    float mel_low = hz_to_mel(100.0f);   // 100 Hz lower bound
    float mel_high = hz_to_mel(8000.0f); // 8kHz upper bound (Nyquist for 16kHz)
    
    // Create mel points
    float mel_points[NUM_MEL_BINS + 2];
    for (int i = 0; i < NUM_MEL_BINS + 2; i++) {
        mel_points[i] = mel_low + (mel_high - mel_low) * i / (NUM_MEL_BINS + 1);
    }
    
    // Convert to Hz and then to FFT bins
    float hz_points[NUM_MEL_BINS + 2];
    int bin_points[NUM_MEL_BINS + 2];
    for (int i = 0; i < NUM_MEL_BINS + 2; i++) {
        hz_points[i] = mel_to_hz(mel_points[i]);
        bin_points[i] = (int)((FFT_SIZE + 1) * hz_points[i] / SAMPLE_RATE);
        if (bin_points[i] >= FFT_SIZE/2) bin_points[i] = FFT_SIZE/2 - 1;
    }
    
    // Create triangular filters
    for (int m = 0; m < NUM_MEL_BINS; m++) {
        for (int k = 0; k < FFT_SIZE/2; k++) {
            mel_filterbank[m][k] = 0.0f;
            
            if (k >= bin_points[m] && k <= bin_points[m+1]) {
                // Rising edge
                if (bin_points[m+1] != bin_points[m]) {
                    mel_filterbank[m][k] = (float)(k - bin_points[m]) / 
                                           (bin_points[m+1] - bin_points[m]);
                }
            } else if (k >= bin_points[m+1] && k <= bin_points[m+2]) {
                // Falling edge
                if (bin_points[m+2] != bin_points[m+1]) {
                    mel_filterbank[m][k] = (float)(bin_points[m+2] - k) / 
                                           (bin_points[m+2] - bin_points[m+1]);
                }
            }
        }
    }
    
    // Initialize Hanning window
    for (int i = 0; i < FFT_SIZE; i++) {
        hanning_window[i] = 0.5f * (1.0f - cosf(2.0f * PI * i / (FFT_SIZE - 1)));
    }
    
    filterbank_initialized = true;
    Serial.println("[Spec] Mel filterbank initialized");
}

bool spectrogram_init() {
    Serial.println("[Spec] Initializing spectrogram generator...");
    init_mel_filterbank();
    Serial.println("[Spec] Ready - 64x64 mel spectrogram");
    return true;
}

bool spectrogram_generate(const int16_t* audio, size_t audio_len, uint8_t* spec_out) {
    if (!filterbank_initialized) {
        init_mel_filterbank();
    }
    
    // Calculate number of frames we can extract
    int num_frames = (audio_len - FFT_SIZE) / FFT_HOP + 1;
    if (num_frames > SPEC_WIDTH) num_frames = SPEC_WIDTH;
    if (num_frames < 10) {
        Serial.println("[Spec] Not enough audio for spectrogram");
        return false;
    }
    
    // Temporary storage for mel energies before normalization
    float mel_spec[SPEC_WIDTH][SPEC_HEIGHT];
    float max_energy = 0.0001f;  // Avoid log(0)
    float min_energy = 1e10f;
    
    // Process each frame
    for (int frame = 0; frame < num_frames; frame++) {
        int offset = frame * FFT_HOP;
        
        // Copy and apply window
        for (int i = 0; i < FFT_SIZE; i++) {
            if (offset + i < audio_len) {
                vReal[i] = (float)audio[offset + i] * hanning_window[i] / 32768.0f;
            } else {
                vReal[i] = 0.0f;
            }
            vImag[i] = 0.0f;
        }
        
        // Compute FFT
        FFT.windowing(FFTWindow::Hann, FFTDirection::Forward);
        FFT.compute(FFTDirection::Forward);
        FFT.complexToMagnitude();
        
        // Apply mel filterbank
        for (int m = 0; m < NUM_MEL_BINS; m++) {
            float energy = 0.0f;
            for (int k = 0; k < FFT_SIZE/2; k++) {
                energy += vReal[k] * mel_filterbank[m][k];
            }
            
            // Log scale (dB-like)
            energy = logf(energy + 1e-10f);
            mel_spec[frame][m] = energy;
            
            if (energy > max_energy) max_energy = energy;
            if (energy < min_energy) min_energy = energy;
        }
    }
    
    // Pad remaining frames if needed
    for (int frame = num_frames; frame < SPEC_WIDTH; frame++) {
        for (int m = 0; m < SPEC_HEIGHT; m++) {
            mel_spec[frame][m] = min_energy;
        }
    }
    
    // Normalize to 0-255 range
    float range = max_energy - min_energy;
    if (range < 0.001f) range = 0.001f;
    
    for (int frame = 0; frame < SPEC_WIDTH; frame++) {
        for (int m = 0; m < SPEC_HEIGHT; m++) {
            float normalized = (mel_spec[frame][m] - min_energy) / range;
            // Flip vertically so low frequencies are at bottom (like standard spectrograms)
            int y = SPEC_HEIGHT - 1 - m;
            spec_out[y * SPEC_WIDTH + frame] = (uint8_t)(normalized * 255.0f);
        }
    }
    
    Serial.print("[Spec] Generated ");
    Serial.print(num_frames);
    Serial.print(" frames, energy range: ");
    Serial.print(min_energy, 2);
    Serial.print(" - ");
    Serial.println(max_energy, 2);
    
    return true;
}

// Simple RLE-based compression for grayscale spectrograms
// Format: [run_length, value] pairs where run_length is 1-127
// If MSB is set, it's a raw byte (for non-repeating data)
size_t spectrogram_to_jpeg(const uint8_t* spec_in, uint8_t* jpeg_out, size_t max_out_size) {
    // For now, use simple 4-bit quantization + RLE
    // This gets ~4KB down to ~800-1200 bytes typically
    
    size_t out_idx = 0;
    
    // Header: magic bytes + dimensions
    if (out_idx + 4 > max_out_size) return 0;
    jpeg_out[out_idx++] = 0x53;  // 'S' for spectrogram
    jpeg_out[out_idx++] = 0x50;  // 'P'
    jpeg_out[out_idx++] = SPEC_WIDTH;
    jpeg_out[out_idx++] = SPEC_HEIGHT;
    
    // Quantize to 4-bit (16 levels) and pack pairs
    uint8_t quantized[SPEC_SIZE / 2];
    for (size_t i = 0; i < SPEC_SIZE; i += 2) {
        uint8_t high = (spec_in[i] >> 4) & 0x0F;
        uint8_t low = (spec_in[i+1] >> 4) & 0x0F;
        quantized[i/2] = (high << 4) | low;
    }
    
    // Simple RLE on quantized data
    size_t q_idx = 0;
    while (q_idx < SPEC_SIZE / 2 && out_idx < max_out_size - 2) {
        uint8_t current = quantized[q_idx];
        size_t run = 1;
        
        // Count consecutive same bytes
        while (q_idx + run < SPEC_SIZE / 2 && 
               quantized[q_idx + run] == current && 
               run < 127) {
            run++;
        }
        
        if (run >= 3) {
            // RLE: length + value
            jpeg_out[out_idx++] = (uint8_t)run;
            jpeg_out[out_idx++] = current;
            q_idx += run;
        } else {
            // Raw byte with MSB set
            jpeg_out[out_idx++] = 0x80 | current;
            q_idx++;
        }
    }
    
    Serial.print("[Spec] Compressed ");
    Serial.print(SPEC_SIZE);
    Serial.print(" -> ");
    Serial.print(out_idx);
    Serial.println(" bytes");
    
    return out_idx;
}

String spectrogram_to_base64(const uint8_t* spec, size_t len) {
    // Simple base64 encoding for debug transmission
    static const char* b64 = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    String result;
    result.reserve((len * 4) / 3 + 4);
    
    for (size_t i = 0; i < len; i += 3) {
        uint32_t n = (spec[i] << 16);
        if (i + 1 < len) n |= (spec[i+1] << 8);
        if (i + 2 < len) n |= spec[i+2];
        
        result += b64[(n >> 18) & 0x3F];
        result += b64[(n >> 12) & 0x3F];
        result += (i + 1 < len) ? b64[(n >> 6) & 0x3F] : '=';
        result += (i + 2 < len) ? b64[n & 0x3F] : '=';
    }
    
    return result;
}

float spectrogram_get_energy(const uint8_t* spec) {
    uint32_t sum = 0;
    for (size_t i = 0; i < SPEC_SIZE; i++) {
        sum += spec[i];
    }
    return (float)sum / (SPEC_SIZE * 255.0f);
}

bool spectrogram_is_anomaly(const uint8_t* spec, float threshold) {
    // Calculate energy in different frequency bands
    float low_band = 0, mid_band = 0, high_band = 0;
    
    // Low frequencies (bottom 1/4 of image = high freq in audio after flip)
    // Actually, after flip: bottom = low freq, top = high freq
    for (int frame = 0; frame < SPEC_WIDTH; frame++) {
        for (int y = 0; y < SPEC_HEIGHT/4; y++) {
            high_band += spec[y * SPEC_WIDTH + frame];
        }
        for (int y = SPEC_HEIGHT/4; y < SPEC_HEIGHT*3/4; y++) {
            mid_band += spec[y * SPEC_WIDTH + frame];
        }
        for (int y = SPEC_HEIGHT*3/4; y < SPEC_HEIGHT; y++) {
            low_band += spec[y * SPEC_WIDTH + frame];
        }
    }
    
    // Normalize
    float total = low_band + mid_band + high_band + 0.001f;
    low_band /= total;
    mid_band /= total;
    high_band /= total;
    
    // Overall energy
    float energy = spectrogram_get_energy(spec);
    
    // Anomaly if energy is above threshold and there's significant
    // activity in the mid frequencies (where chainsaw fundamentals live)
    bool is_loud = energy > threshold;
    bool has_mid_activity = mid_band > 0.35f;  // More than 35% in mid band
    
    Serial.print("[Spec] Energy: ");
    Serial.print(energy, 3);
    Serial.print(" Low:");
    Serial.print(low_band, 2);
    Serial.print(" Mid:");
    Serial.print(mid_band, 2);
    Serial.print(" High:");
    Serial.println(high_band, 2);
    
    return is_loud && has_mid_activity;
}
