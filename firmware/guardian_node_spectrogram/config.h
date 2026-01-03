#ifndef CONFIG_H
#define CONFIG_H

// ============================================
// Forest Guardian - Configuration
// Heltec WiFi LoRa 32 V3 (ESP32-S3 + SX1262)
// ============================================

// Node identity - Change this for each node!
#define NODE_ID "GUARDIAN_001"

// ============================================
// LoRa Configuration (SX1262)
// ============================================
#define LORA_FREQ 915.0          // MHz (915 for US/Canada, 868 for EU)
#define LORA_BANDWIDTH 125.0     // kHz
#define LORA_SPREADING_FACTOR 10 // SF10 for long range (7-12)
#define LORA_CODING_RATE 5       // 4/5
#define LORA_TX_POWER 14         // dBm (max 22)
#define LORA_PREAMBLE 8          // Preamble length
#define LORA_SYNC_WORD 0x12      // Private network (MUST MATCH HUB!)

// Heltec V3 LoRa Pins (SX1262)
#define LORA_SS 8    // NSS/CS
#define LORA_RST 12  // Reset
#define LORA_BUSY 13 // Busy
#define LORA_DIO1 14 // DIO1/IRQ
#define LORA_SCK 9   // SPI Clock
#define LORA_MOSI 10 // SPI MOSI
#define LORA_MISO 11 // SPI MISO

// ============================================
// I2S Microphone (INMP441)
// ============================================
#define I2S_SCK 7 // Serial Clock (BCK) - GPIO7, Pin 18 left
#define I2S_WS 6  // Word Select (LRCK) - GPIO6, Pin 17 left
#define I2S_SD 5  // Serial Data (DOUT) - GPIO5, Pin 16 left
#define I2S_PORT I2S_NUM_0
#define SAMPLE_RATE 16000       // 16kHz
#define AUDIO_BUFFER_SIZE 17000 // ~1 second + margin for TFLite (32 frames × 512 hop + 512 FFT)
#define AUDIO_CHUNK_SIZE 17000  // Full buffer for TFLite inference

// ============================================
// GPS Module (GY-NEO6MV2)
// ============================================
// Using GPIO 19 (RX) and GPIO 20 (TX) - accessible on Header J2
#define GPS_RX 19 // ESP32 receives on this pin (connect to GPS TX) - Pin 18 right
#define GPS_TX 20 // ESP32 transmits on this pin (connect to GPS RX) - Pin 17 right
#define GPS_BAUD 9600

// ============================================
// OLED Display (Heltec Built-in SSD1306)
// ============================================
#define OLED_SDA 17
#define OLED_SCL 18
#define OLED_RST 21
#define OLED_WIDTH 128
#define OLED_HEIGHT 64

// ============================================
// Battery Monitoring (Heltec V3 Built-in)
// ============================================
#define BATTERY_PIN 1      // ADC1 CH0 for battery voltage
#define VEXT_CTRL 36       // Vext power control (active LOW)
#define BATTERY_FACTOR 4.9 // Voltage divider factor
#define BATTERY_FULL 4.2f  // Full charge voltage
#define BATTERY_EMPTY 3.2f // Empty voltage

// ============================================
// LED (Heltec V3)
// ============================================
#define LED_PIN 35 // Built-in white LED

// ============================================
// Detection & Timing Settings
// ============================================
// DEMO MODE: Set to 1 for Imagine Cup demo (phone/laptop speakers)
//            Set to 0 for real deployment (actual chainsaws)
#define DEMO_MODE 1

#if DEMO_MODE
// Demo settings - more sensitive for phone/laptop speakers
// Phone speakers can't reproduce chainsaw's low frequencies well
#define DETECTION_THRESHOLD 0.18f // 18% smoothed confidence (for Edge Impulse mode)
#define DETECTION_RAW_MIN 0.15f   // 15% raw detection counts
#define ANOMALY_THRESHOLD 0.15f   // 15% energy threshold for spectrogram anomaly
#define CONSECUTIVE_REQUIRED 2    // 2 consecutive hits
#define LORA_COOLDOWN_MS 5000     // 5s cooldown for demo
#else
// Production settings - for real chainsaws in forest
// Real chainsaws produce 50-90% confidence (loud, sustained)
#define DETECTION_THRESHOLD 0.35f // 35% smoothed confidence
#define DETECTION_RAW_MIN 0.25f   // 25% raw detection counts
#define ANOMALY_THRESHOLD 0.25f   // 25% energy threshold for spectrogram anomaly
#define CONSECUTIVE_REQUIRED 3    // 3 consecutive hits
#define LORA_COOLDOWN_MS 30000    // 30s cooldown
#endif

#define HEARTBEAT_INTERVAL_MS 300000 // 5 minute heartbeat

// ============================================
// Spectrogram Settings (for Azure AI Vision mode)
// ============================================
#define SPEC_SAMPLE_RATE 16000    // Match audio sample rate
#define SPEC_FFT_SIZE 256         // FFT window size
#define SPEC_HOP_SIZE 128         // FFT hop size
#define SPEC_NUM_FRAMES 64        // Spectrogram width (time)
#define SPEC_NUM_BINS 64          // Spectrogram height (frequency)

// ============================================
// Power Management
// ============================================
#define LOW_BATTERY_THRESHOLD 20 // % battery for low power warning
#define DEEP_SLEEP_DURATION 60   // Seconds to sleep when critical

#endif // CONFIG_H
