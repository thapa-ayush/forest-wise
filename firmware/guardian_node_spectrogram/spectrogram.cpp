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

// Use PSRAM or heap for large buffers on ESP32-S3
namespace
{
    // FFT buffers (smaller now: 128 floats each = 512 bytes)
    float vReal[FFT_SIZE];
    float vImag[FFT_SIZE];

    // Mel filterbank (reduced: 32 bins x 64 = 8KB instead of 32KB)
    // Allocate on heap to avoid stack overflow
    float *mel_filterbank_flat = nullptr; // NUM_MEL_BINS * (FFT_SIZE/2)
    bool filterbank_initialized = false;

    // ArduinoFFT instance
    ArduinoFFT<float> FFT = ArduinoFFT<float>(vReal, vImag, FFT_SIZE, SAMPLE_RATE);

    // Hanning window
    float hanning_window[FFT_SIZE];
}

// Helper macro to access flat filterbank as 2D array
#define MEL_FB(m, k) mel_filterbank_flat[(m) * (FFT_SIZE / 2) + (k)]

// Convert frequency to mel scale
float hz_to_mel(float hz)
{
    return 2595.0f * log10f(1.0f + hz / 700.0f);
}

// Convert mel to frequency
float mel_to_hz(float mel)
{
    return 700.0f * (powf(10.0f, mel / 2595.0f) - 1.0f);
}

// Initialize mel filterbank
void init_mel_filterbank()
{
    if (filterbank_initialized)
        return;

    // Allocate filterbank on heap (NUM_MEL_BINS * FFT_SIZE/2 floats)
    size_t fb_size = NUM_MEL_BINS * (FFT_SIZE / 2) * sizeof(float);
    mel_filterbank_flat = (float *)malloc(fb_size);
    if (!mel_filterbank_flat)
    {
        Serial.println("[Spec] ERROR: Failed to allocate filterbank!");
        return;
    }
    memset(mel_filterbank_flat, 0, fb_size);
    Serial.print("[Spec] Allocated filterbank: ");
    Serial.print(fb_size);
    Serial.println(" bytes");

    float mel_low = hz_to_mel(100.0f);   // 100 Hz lower bound
    float mel_high = hz_to_mel(8000.0f); // 8kHz upper bound (Nyquist for 16kHz)

    // Create mel points (use heap for temp arrays too)
    float *mel_points = (float *)malloc((NUM_MEL_BINS + 2) * sizeof(float));
    float *hz_points = (float *)malloc((NUM_MEL_BINS + 2) * sizeof(float));
    int *bin_points = (int *)malloc((NUM_MEL_BINS + 2) * sizeof(int));

    if (!mel_points || !hz_points || !bin_points)
    {
        Serial.println("[Spec] ERROR: Failed to allocate temp arrays!");
        return;
    }

    for (int i = 0; i < NUM_MEL_BINS + 2; i++)
    {
        mel_points[i] = mel_low + (mel_high - mel_low) * i / (NUM_MEL_BINS + 1);
    }

    // Convert to Hz and then to FFT bins
    for (int i = 0; i < NUM_MEL_BINS + 2; i++)
    {
        hz_points[i] = mel_to_hz(mel_points[i]);
        bin_points[i] = (int)((FFT_SIZE + 1) * hz_points[i] / SAMPLE_RATE);
        if (bin_points[i] >= FFT_SIZE / 2)
            bin_points[i] = FFT_SIZE / 2 - 1;
    }

    // Create triangular filters
    for (int m = 0; m < NUM_MEL_BINS; m++)
    {
        for (int k = 0; k < FFT_SIZE / 2; k++)
        {
            MEL_FB(m, k) = 0.0f;

            if (k >= bin_points[m] && k <= bin_points[m + 1])
            {
                // Rising edge
                if (bin_points[m + 1] != bin_points[m])
                {
                    MEL_FB(m, k) = (float)(k - bin_points[m]) /
                                   (bin_points[m + 1] - bin_points[m]);
                }
            }
            else if (k >= bin_points[m + 1] && k <= bin_points[m + 2])
            {
                // Falling edge
                if (bin_points[m + 2] != bin_points[m + 1])
                {
                    MEL_FB(m, k) = (float)(bin_points[m + 2] - k) /
                                   (bin_points[m + 2] - bin_points[m + 1]);
                }
            }
        }
    }

    // Free temp arrays
    free(mel_points);
    free(hz_points);
    free(bin_points);

    // Initialize Hanning window
    for (int i = 0; i < FFT_SIZE; i++)
    {
        hanning_window[i] = 0.5f * (1.0f - cosf(2.0f * PI * i / (FFT_SIZE - 1)));
    }

    filterbank_initialized = true;
    Serial.println("[Spec] Mel filterbank initialized");
}

bool spectrogram_init()
{
    Serial.println("[Spec] Initializing spectrogram generator...");
    init_mel_filterbank();
    Serial.println("[Spec] Ready - 32x32 mel spectrogram");
    return true;
}

bool spectrogram_generate(const int16_t *audio, size_t audio_len, uint8_t *spec_out)
{
    if (!filterbank_initialized || !mel_filterbank_flat)
    {
        init_mel_filterbank();
        if (!mel_filterbank_flat)
            return false;
    }

    // Calculate number of frames we can extract
    int num_frames = (audio_len - FFT_SIZE) / FFT_HOP + 1;
    if (num_frames > SPEC_WIDTH)
        num_frames = SPEC_WIDTH;
    if (num_frames < 5)
    {
        Serial.println("[Spec] Not enough audio for spectrogram");
        return false;
    }

    // Allocate temporary storage on heap (not stack!)
    // SPEC_WIDTH * SPEC_HEIGHT * 4 bytes = 32*32*4 = 4KB
    float *mel_spec = (float *)malloc(SPEC_WIDTH * SPEC_HEIGHT * sizeof(float));
    if (!mel_spec)
    {
        Serial.println("[Spec] Failed to allocate mel_spec");
        return false;
    }
    memset(mel_spec, 0, SPEC_WIDTH * SPEC_HEIGHT * sizeof(float));

    float max_energy = 0.0001f; // Avoid log(0)
    float min_energy = 1e10f;

    // Process each frame
    for (int frame = 0; frame < num_frames; frame++)
    {
        int offset = frame * FFT_HOP;

        // Copy and apply window
        for (int i = 0; i < FFT_SIZE; i++)
        {
            if (offset + i < audio_len)
            {
                vReal[i] = (float)audio[offset + i] * hanning_window[i] / 32768.0f;
            }
            else
            {
                vReal[i] = 0.0f;
            }
            vImag[i] = 0.0f;
        }

        // Compute FFT
        FFT.windowing(FFTWindow::Hann, FFTDirection::Forward);
        FFT.compute(FFTDirection::Forward);
        FFT.complexToMagnitude();

        // Apply mel filterbank
        for (int m = 0; m < NUM_MEL_BINS; m++)
        {
            float energy = 0.0f;
            for (int k = 0; k < FFT_SIZE / 2; k++)
            {
                energy += vReal[k] * MEL_FB(m, k);
            }

            // Log scale (dB-like)
            energy = logf(energy + 1e-10f);
            mel_spec[frame * SPEC_HEIGHT + m] = energy;

            if (energy > max_energy)
                max_energy = energy;
            if (energy < min_energy)
                min_energy = energy;
        }

        // Yield to prevent watchdog
        if (frame % 8 == 0)
            yield();
    }

    // Pad remaining frames if needed
    for (int frame = num_frames; frame < SPEC_WIDTH; frame++)
    {
        for (int m = 0; m < SPEC_HEIGHT; m++)
        {
            mel_spec[frame * SPEC_HEIGHT + m] = min_energy;
        }
    }

    // Normalize to 0-255 range
    float range = max_energy - min_energy;
    if (range < 0.001f)
        range = 0.001f;

    for (int frame = 0; frame < SPEC_WIDTH; frame++)
    {
        for (int m = 0; m < SPEC_HEIGHT; m++)
        {
            float normalized = (mel_spec[frame * SPEC_HEIGHT + m] - min_energy) / range;
            // Flip vertically so low frequencies are at bottom (like standard spectrograms)
            int y = SPEC_HEIGHT - 1 - m;
            spec_out[y * SPEC_WIDTH + frame] = (uint8_t)(normalized * 255.0f);
        }
    }

    // Free the temp buffer
    free(mel_spec);

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
size_t spectrogram_to_jpeg(const uint8_t *spec_in, uint8_t *jpeg_out, size_t max_out_size)
{
    // For now, use simple 4-bit quantization + RLE
    // This gets ~4KB down to ~800-1200 bytes typically

    size_t out_idx = 0;

    // Header: magic bytes + dimensions
    if (out_idx + 4 > max_out_size)
        return 0;
    jpeg_out[out_idx++] = 0x53; // 'S' for spectrogram
    jpeg_out[out_idx++] = 0x50; // 'P'
    jpeg_out[out_idx++] = SPEC_WIDTH;
    jpeg_out[out_idx++] = SPEC_HEIGHT;

    // Quantize to 4-bit (16 levels) and pack pairs
    uint8_t quantized[SPEC_SIZE / 2];
    for (size_t i = 0; i < SPEC_SIZE; i += 2)
    {
        uint8_t high = (spec_in[i] >> 4) & 0x0F;
        uint8_t low = (spec_in[i + 1] >> 4) & 0x0F;
        quantized[i / 2] = (high << 4) | low;
    }

    // Simple RLE on quantized data
    size_t q_idx = 0;
    while (q_idx < SPEC_SIZE / 2 && out_idx < max_out_size - 2)
    {
        uint8_t current = quantized[q_idx];
        size_t run = 1;

        // Count consecutive same bytes
        while (q_idx + run < SPEC_SIZE / 2 &&
               quantized[q_idx + run] == current &&
               run < 127)
        {
            run++;
        }

        if (run >= 3)
        {
            // RLE: length + value
            jpeg_out[out_idx++] = (uint8_t)run;
            jpeg_out[out_idx++] = current;
            q_idx += run;
        }
        else
        {
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

String spectrogram_to_base64(const uint8_t *spec, size_t len)
{
    // Simple base64 encoding for debug transmission
    static const char *b64 = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    String result;
    result.reserve((len * 4) / 3 + 4);

    for (size_t i = 0; i < len; i += 3)
    {
        uint32_t n = (spec[i] << 16);
        if (i + 1 < len)
            n |= (spec[i + 1] << 8);
        if (i + 2 < len)
            n |= spec[i + 2];

        result += b64[(n >> 18) & 0x3F];
        result += b64[(n >> 12) & 0x3F];
        result += (i + 1 < len) ? b64[(n >> 6) & 0x3F] : '=';
        result += (i + 2 < len) ? b64[n & 0x3F] : '=';
    }

    return result;
}

float spectrogram_get_energy(const uint8_t *spec)
{
    uint32_t sum = 0;
    for (size_t i = 0; i < SPEC_SIZE; i++)
    {
        sum += spec[i];
    }
    return (float)sum / (SPEC_SIZE * 255.0f);
}

bool spectrogram_is_anomaly(const uint8_t *spec, float threshold)
{
    // Calculate energy in different frequency bands
    float low_band = 0, mid_band = 0, high_band = 0;

    // Calculate per-frame energies for variance analysis
    float frame_energies[SPEC_WIDTH];
    float sum_energy = 0;

    for (int frame = 0; frame < SPEC_WIDTH; frame++)
    {
        float frame_sum = 0;
        float frame_low = 0, frame_mid = 0, frame_high = 0;

        // High frequencies (top of spectrogram after flip)
        for (int y = 0; y < SPEC_HEIGHT / 4; y++)
        {
            float val = spec[y * SPEC_WIDTH + frame];
            high_band += val;
            frame_high += val;
            frame_sum += val;
        }
        // Mid frequencies
        for (int y = SPEC_HEIGHT / 4; y < SPEC_HEIGHT * 3 / 4; y++)
        {
            float val = spec[y * SPEC_WIDTH + frame];
            mid_band += val;
            frame_mid += val;
            frame_sum += val;
        }
        // Low frequencies (bottom = low freq after flip)
        for (int y = SPEC_HEIGHT * 3 / 4; y < SPEC_HEIGHT; y++)
        {
            float val = spec[y * SPEC_WIDTH + frame];
            low_band += val;
            frame_low += val;
            frame_sum += val;
        }
        frame_energies[frame] = frame_sum;
        sum_energy += frame_sum;
    }

    // Calculate variance of frame energies
    float mean_energy = sum_energy / SPEC_WIDTH;
    float variance = 0;
    for (int frame = 0; frame < SPEC_WIDTH; frame++)
    {
        float diff = frame_energies[frame] - mean_energy;
        variance += diff * diff;
    }
    variance /= SPEC_WIDTH;
    float std_dev = sqrtf(variance);
    float coef_var = (mean_energy > 0.001f) ? (std_dev / mean_energy) : 1.0f;

    // Normalize bands
    float total = low_band + mid_band + high_band + 0.001f;
    float low_ratio = low_band / total;
    float mid_ratio = mid_band / total;
    float high_ratio = high_band / total;

    // Overall energy
    float energy = spectrogram_get_energy(spec);

    Serial.print("[Spec] E:");
    Serial.print(energy, 3);
    Serial.print(" L:");
    Serial.print(low_ratio, 2);
    Serial.print(" M:");
    Serial.print(mid_ratio, 2);
    Serial.print(" H:");
    Serial.print(high_ratio, 2);
    Serial.print(" CV:");
    Serial.print(coef_var, 2);

#if DEMO_MODE
    // ============================================
    // DEMO MODE - Mobile/laptop speaker playback
    // ============================================
    // Voices: 70-76% energy (avg 71-72%)
    // Phone chainsaw: 80-84% energy
    // Threshold: 80% to reject voices, accept chainsaw

    bool is_loud = energy > 0.80f;             // 80% threshold - voices are below this
    bool has_some_high = high_ratio > 0.22f;   // Some high frequency (>22%)
    bool is_very_sustained = coef_var < 0.05f; // VERY constant (CV < 5%)
    bool is_bright = high_ratio >= low_ratio;  // More high than low

    Serial.print(" [DEMO ");
    Serial.print(is_loud ? "LOUD " : "quiet ");
    Serial.print(has_some_high ? "HIGH " : "noHi ");
    Serial.print(is_very_sustained ? "CONST " : "vary ");
    Serial.print(is_bright ? "BRIGHT" : "dull");
    Serial.println("]");

    // Demo mode: 80%+ energy + some high freq + EXTREMELY constant (CV<5%)
    return is_loud && has_some_high && is_very_sustained && is_bright;

#else
    // ============================================
    // PRODUCTION MODE - Real chainsaws in forest
    // ============================================
    // Real chainsaws have:
    // 1. VERY high energy (they're LOUD)
    // 2. Strong LOW frequency (engine rumble 50-300Hz)
    // 3. BROADBAND spectrum (energy across all frequencies)
    // 4. Very sustained (constant motor)

    bool is_very_loud = energy > threshold;
    bool has_low_rumble = low_ratio > 0.20f;
    bool is_broadband = (low_ratio > 0.15f) && (mid_ratio > 0.30f) && (high_ratio > 0.10f);
    bool is_sustained = coef_var < 0.3f;

    Serial.print(" [PROD ");
    Serial.print(is_very_loud ? "LOUD " : "quiet ");
    Serial.print(has_low_rumble ? "LOW " : "noLow ");
    Serial.print(is_broadband ? "BROAD " : "narrow ");
    Serial.print(is_sustained ? "SUST" : "vary");
    Serial.println("]");

    return is_very_loud && has_low_rumble && is_broadband && is_sustained;
#endif
}
