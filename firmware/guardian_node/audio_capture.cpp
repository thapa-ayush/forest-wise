/*
 * audio_capture.cpp - Forest Guardian Audio Capture Handler
 * For INMP441 I2S MEMS Microphone on ESP32-S3
 * Pin configuration in config.h
 */
#include "audio_capture.h"
#include "config.h"
#include <driver/i2s.h>

static bool audio_ready = false;
static float last_rms = 0.0;
static float last_peak = 0.0;
static int read_count = 0;

bool audio_capture_init()
{
    Serial.println("[Audio] Initializing I2S for INMP441...");
    Serial.print("[Audio] Pins: SCK=");
    Serial.print(I2S_SCK);
    Serial.print(", WS=");
    Serial.print(I2S_WS);
    Serial.print(", SD=");
    Serial.println(I2S_SD);

    // Uninstall driver if already installed
    i2s_driver_uninstall(I2S_PORT);
    delay(100);

    // I2S configuration for INMP441
    // Use STEREO to capture both channels - one will have data
    i2s_config_t i2s_config = {
        .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX),
        .sample_rate = SAMPLE_RATE,
        .bits_per_sample = I2S_BITS_PER_SAMPLE_32BIT,
        .channel_format = I2S_CHANNEL_FMT_RIGHT_LEFT, // Stereo - get both channels
        .communication_format = I2S_COMM_FORMAT_STAND_I2S,
        .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
        .dma_buf_count = 8,
        .dma_buf_len = 256,
        .use_apll = false,
        .tx_desc_auto_clear = false,
        .fixed_mclk = 0};

    esp_err_t result = i2s_driver_install(I2S_PORT, &i2s_config, 0, NULL);
    if (result != ESP_OK)
    {
        Serial.print("[Audio] ERROR: I2S driver install: ");
        Serial.println(esp_err_to_name(result));
        return false;
    }

    i2s_pin_config_t pin_config = {
        .mck_io_num = I2S_PIN_NO_CHANGE,
        .bck_io_num = I2S_SCK,
        .ws_io_num = I2S_WS,
        .data_out_num = I2S_PIN_NO_CHANGE,
        .data_in_num = I2S_SD};

    result = i2s_set_pin(I2S_PORT, &pin_config);
    if (result != ESP_OK)
    {
        Serial.print("[Audio] ERROR: I2S set pin: ");
        Serial.println(esp_err_to_name(result));
        return false;
    }

    i2s_start(I2S_PORT);
    i2s_zero_dma_buffer(I2S_PORT);
    delay(200);

    Serial.println("[Audio] I2S initialized OK (stereo mode)!");
    audio_ready = true;
    return true;
}

bool audio_capture_read(int16_t *buffer, size_t len)
{
    if (!audio_ready)
        return false;

    // Read in chunks to fill the entire buffer
    static int32_t temp_buffer[512];
    size_t total_samples = 0;

    // Determine which channel has data (check once at start)
    static bool use_right = false;
    static bool channel_detected = false;

    while (total_samples < len)
    {
        size_t samples_needed = len - total_samples;
        size_t chunk_samples = (samples_needed > 256) ? 256 : samples_needed;
        size_t bytes_to_read = chunk_samples * 2 * sizeof(int32_t); // x2 for stereo
        size_t bytes_read = 0;

        esp_err_t result = i2s_read(I2S_PORT, temp_buffer,
                                    bytes_to_read, &bytes_read, pdMS_TO_TICKS(100));

        if (result != ESP_OK || bytes_read == 0)
        {
            break;
        }

        size_t samples_read = bytes_read / (2 * sizeof(int32_t)); // stereo pairs

        // Detect channel on first chunk
        if (!channel_detected && samples_read > 0)
        {
            int32_t max_left = 0, max_right = 0;
            for (size_t i = 0; i < samples_read * 2; i += 2)
            {
                if (abs(temp_buffer[i]) > max_left)
                    max_left = abs(temp_buffer[i]);
                if (abs(temp_buffer[i + 1]) > max_right)
                    max_right = abs(temp_buffer[i + 1]);
            }
            use_right = (max_right > max_left);
            channel_detected = true;
        }

        // Convert 32-bit to 16-bit from selected channel
        // INMP441 outputs 24-bit data left-aligned in 32-bit word
        // Shift right by 15 (reduced gain to prevent clipping)
        // Apply aggressive soft clipping to preserve waveform shape
        for (size_t i = 0; i < samples_read && (total_samples + i) < len; i++)
        {
            int32_t raw = temp_buffer[i * 2 + (use_right ? 1 : 0)];
            int32_t shifted = raw >> 15; // Reduced from 14 to 15 for less gain

            // Aggressive soft clipping starting at 20000 to keep signal clean
            if (shifted > 20000)
            {
                shifted = 20000 + (shifted - 20000) / 8;
            }
            else if (shifted < -20000)
            {
                shifted = -20000 + (shifted + 20000) / 8;
            }
            // Final clamp at 24000 (leaves headroom)
            if (shifted > 24000)
                shifted = 24000;
            else if (shifted < -24000)
                shifted = -24000;

            buffer[total_samples + i] = (int16_t)shifted;
        }

        total_samples += samples_read;
    }

    // Zero-fill any remaining
    for (size_t i = total_samples; i < len; i++)
    {
        buffer[i] = 0;
    }

    read_count++;

    // Calculate peak
    int16_t peak = 0;
    for (size_t i = 0; i < total_samples; i++)
    {
        if (abs(buffer[i]) > peak)
            peak = abs(buffer[i]);
    }
    last_peak = peak;

    return (total_samples > 0);
}

float audio_get_rms()
{
    return last_rms;
}

float audio_get_peak()
{
    return last_peak;
}

bool audio_is_ready()
{
    return audio_ready;
}
