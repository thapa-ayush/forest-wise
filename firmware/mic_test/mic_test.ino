/*
 * INMP441 Microphone Test for Heltec WiFi LoRa 32 V3
 *
 * This simple sketch tests if the INMP441 is wired correctly.
 *
 * WIRING:
 *   INMP441     Heltec V3
 *   -------     ---------
 *   VDD    ->   3.3V (Pin 3-4 left side)
 *   GND    ->   GND (Pin 1 left side)
 *   SCK    ->   GPIO7 (Pin 18 left side, top)
 *   WS     ->   GPIO6 (Pin 17 left side)
 *   SD     ->   GPIO5 (Pin 16 left side)
 *   L/R    ->   GND (or try 3.3V if no signal)
 */

#include <driver/i2s.h>

// Pin definitions - MATCH YOUR WIRING!
#define I2S_SCK 7 // Clock - GPIO7, Pin 18 left
#define I2S_WS 6  // Word Select - GPIO6, Pin 17 left
#define I2S_SD 5  // Data - GPIO5, Pin 16 left
#define I2S_PORT I2S_NUM_0

void setup()
{
    Serial.begin(115200);
    delay(2000);

    Serial.println("\n\n=== INMP441 Microphone Test ===");
    Serial.print("Pins: SCK=GPIO");
    Serial.print(I2S_SCK);
    Serial.print(", WS=GPIO");
    Serial.print(I2S_WS);
    Serial.print(", SD=GPIO");
    Serial.println(I2S_SD);
    Serial.println();

    // I2S configuration
    i2s_config_t i2s_config = {
        .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX),
        .sample_rate = 16000,
        .bits_per_sample = I2S_BITS_PER_SAMPLE_32BIT,
        .channel_format = I2S_CHANNEL_FMT_RIGHT_LEFT,
        .communication_format = I2S_COMM_FORMAT_STAND_I2S,
        .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
        .dma_buf_count = 4,
        .dma_buf_len = 256,
        .use_apll = false,
        .tx_desc_auto_clear = false,
        .fixed_mclk = 0};

    esp_err_t result = i2s_driver_install(I2S_PORT, &i2s_config, 0, NULL);
    Serial.print("I2S driver install: ");
    Serial.println(result == ESP_OK ? "OK" : esp_err_to_name(result));

    i2s_pin_config_t pin_config = {
        .mck_io_num = I2S_PIN_NO_CHANGE,
        .bck_io_num = I2S_SCK,
        .ws_io_num = I2S_WS,
        .data_out_num = I2S_PIN_NO_CHANGE,
        .data_in_num = I2S_SD};

    result = i2s_set_pin(I2S_PORT, &pin_config);
    Serial.print("I2S set pins: ");
    Serial.println(result == ESP_OK ? "OK" : esp_err_to_name(result));

    i2s_start(I2S_PORT);
    delay(500);

    Serial.println("\nListening for audio...\n");
    Serial.println("If all values are 0, check wiring!");
    Serial.println("Tap the mic or make noise to test.\n");
}

void loop()
{
    int32_t buffer[64]; // 32 stereo pairs
    size_t bytes_read = 0;

    esp_err_t result = i2s_read(I2S_PORT, buffer, sizeof(buffer), &bytes_read, pdMS_TO_TICKS(100));

    if (result != ESP_OK)
    {
        Serial.print("Read error: ");
        Serial.println(esp_err_to_name(result));
        delay(1000);
        return;
    }

    // Find max values in each channel
    int32_t max_left = 0, max_right = 0;
    for (int i = 0; i < 32; i++)
    {
        int32_t left = buffer[i * 2];
        int32_t right = buffer[i * 2 + 1];
        if (abs(left) > max_left)
            max_left = abs(left);
        if (abs(right) > max_right)
            max_right = abs(right);
    }

    // Print raw values
    Serial.print("RAW L: ");
    Serial.print(buffer[0], HEX);
    Serial.print("  R: ");
    Serial.print(buffer[1], HEX);

    // Print max values
    Serial.print("  |  MAX L: ");
    Serial.print(max_left);
    Serial.print("  R: ");
    Serial.print(max_right);

    // Visual indicator
    if (max_left > 100000 || max_right > 100000)
    {
        Serial.print("  <<< SOUND DETECTED!");
    }
    else if (max_left == 0 && max_right == 0)
    {
        Serial.print("  (no signal - check wiring)");
    }

    Serial.println();
    delay(200);
}
