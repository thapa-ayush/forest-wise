/*
 * Forest Guardian - guardian_node.ino (Spectrogram Version)
 * Main firmware for Heltec WiFi LoRa 32 V3 (ESP32-S3 + SX1262)
 *
 * NEW APPROACH: Instead of Edge Impulse ML classification on device,
 * this version generates spectrograms and sends them to Azure AI
 * for intelligent classification via GPT-4o Vision.
 *
 * Benefits:
 * - Higher accuracy (~95% vs ~50-60% with Edge Impulse)
 * - Visual evidence stored for each alert
 * - No retraining needed - Azure AI adapts to descriptions
 * - Better false positive rejection
 *
 * Hardware: Heltec WiFi LoRa 32 V3
 *   - ESP32-S3 MCU
 *   - SX1262 LoRa transceiver (915 MHz)
 *   - SSD1306 0.96" OLED display
 *   - INMP441 I2S MEMS microphone (external)
 *   - GY-NEO6MV2 GPS module (external)
 *
 * Libraries required:
 *   - RadioLib (LoRa SX1262)
 *   - TinyGPSPlus (GPS parsing)
 *   - U8g2 (OLED display)
 *   - arduinoFFT (spectrogram generation)
 *   - ArduinoJson (message formatting)
 */
#include <Arduino.h>
#include "config.h"
#include "audio_capture.h"
#include "gps_handler.h"
#include "spectrogram.h"  // NEW: Spectrogram generator
#include "lora_comms.h"
#include "display_handler.h"
#include "power_manager.h"
#include <ArduinoJson.h>

// State machine
enum SystemState {
    STATE_BOOT,
    STATE_INIT,
    STATE_GPS_WAIT,
    STATE_READY,
    STATE_LISTENING,
    STATE_ANOMALY_DETECTED,  // NEW: When unusual sound detected
    STATE_SENDING_SPECTROGRAM,  // NEW: Transmitting spectrogram
    STATE_ALERT,
    STATE_HEARTBEAT,
    STATE_LOW_BATTERY,
    STATE_ERROR,
    STATE_SLEEP
};

SystemState current_state = STATE_BOOT;
unsigned long state_start_time = 0;
unsigned long last_heartbeat = 0;
unsigned long last_alert = 0;
unsigned long last_gps_update = 0;
unsigned long last_display_update = 0;

// GPS cache
double cached_lat = 0.0;
double cached_lon = 0.0;
bool has_gps_fix = false;

// Audio buffer (1 second at 16kHz)
static int16_t audio_buf[AUDIO_BUFFER_SIZE];

// Spectrogram buffers
static uint8_t spectrogram[SPEC_SIZE];           // 64x64 = 4096 bytes
static uint8_t spectrogram_compressed[1200];     // Compressed output

// Statistics
int total_anomalies = 0;
int total_spectrograms_sent = 0;
int total_heartbeats = 0;

// Audio monitoring
bool mic_is_working = false;
float current_audio_level = 0.0;
float current_energy = 0.0;
unsigned long last_detail_display = 0;

// Anomaly detection state
int consecutive_anomalies = 0;
unsigned long last_anomaly_time = 0;

void change_state(SystemState new_state) {
    Serial.print("[FSM] State: ");
    Serial.print(current_state);
    Serial.print(" -> ");
    Serial.println(new_state);
    current_state = new_state;
    state_start_time = millis();
}

void send_json_message(const char* type, float confidence) {
    StaticJsonDocument<256> doc;
    doc["node_id"] = NODE_ID;
    doc["type"] = type;
    doc["confidence"] = (int)(confidence * 100);
    doc["lat"] = has_gps_fix ? cached_lat : 0.0;
    doc["lon"] = has_gps_fix ? cached_lon : 0.0;
    doc["battery"] = (int)read_battery_percent();
    doc["timestamp"] = millis() / 1000;
    doc["anomalies"] = total_anomalies;
    doc["tx_count"] = lora_get_tx_count();

    String msg;
    serializeJson(doc, msg);

    if (lora_send(msg)) {
        Serial.print("[TX] Sent ");
        Serial.print(type);
        Serial.print(": ");
        Serial.println(msg);
    } else {
        Serial.println("[TX] Failed to send message");
    }
}

// LED flash helper for alerts
void flash_led(int times, int on_ms, int off_ms) {
    for (int i = 0; i < times; i++) {
        digitalWrite(LED_PIN, HIGH);
        delay(on_ms);
        digitalWrite(LED_PIN, LOW);
        delay(off_ms);
    }
}

void setup() {
    // Initialize LED first for immediate feedback
    pinMode(LED_PIN, OUTPUT);
    digitalWrite(LED_PIN, HIGH);

    // Initialize serial for debugging
    Serial.begin(115200);
    delay(1000);
    Serial.println();
    Serial.println("========================================");
    Serial.println("  FOREST GUARDIAN - Spectrogram Mode");
    Serial.println("========================================");
    Serial.print("Node ID: ");
    Serial.println(NODE_ID);
    Serial.println("Firmware: v2.0.0-spectrogram");
    Serial.println();

    digitalWrite(LED_PIN, LOW);

    // Initialize display first for visual feedback
    Serial.println("[INIT] Display...");
    display_init();
    delay(2000);

    display_progress("Initializing...", 0);

    // Initialize power manager
    Serial.println("[INIT] Power manager...");
    display_progress("Power system", 10);
    power_manager_init();

    float battery = read_battery_percent();
    Serial.print("[INIT] Battery: ");
    Serial.print(battery);
    Serial.println("%");

    if (battery < 10.0) {
        Serial.println("[ERROR] Battery critically low!");
        display_message("CRITICAL", "Battery too low", "Shutting down...");
        delay(3000);
        esp_deep_sleep_start();
    }

    // Initialize audio capture
    Serial.println("[INIT] Audio capture...");
    display_progress("Audio system", 25);
    if (!audio_capture_init()) {
        Serial.println("[ERROR] Audio init failed!");
        display_message("ERROR", "Audio init failed", "Check microphone");
        delay(3000);
    }

    // Initialize GPS
    Serial.println("[INIT] GPS...");
    display_progress("GPS module", 40);
    if (!gps_init()) {
        Serial.println("[WARNING] GPS init failed, continuing without GPS");
    }

    // Initialize spectrogram generator (NEW - replaces ML inference)
    Serial.println("[INIT] Spectrogram generator...");
    display_progress("Spectrogram Gen", 55);
    if (!spectrogram_init()) {
        Serial.println("[ERROR] Spectrogram init failed!");
        display_message("ERROR", "FFT init failed", "Check memory");
        delay(3000);
    }

    // Initialize LoRa
    Serial.println("[INIT] LoRa transceiver...");
    display_progress("LoRa radio", 75);
    if (!lora_init()) {
        Serial.println("[ERROR] LoRa init failed!");
        display_message("ERROR", "LoRa init failed", "Check antenna");
        delay(3000);
    }

    display_progress("Complete!", 100);
    delay(1000);

    // Send boot message
    Serial.println("[INIT] Sending boot notification...");
    send_json_message("boot", 0);

    Serial.println();
    Serial.println("========================================");
    Serial.println("   Spectrogram Mode Initialized!");
    Serial.println("   Anomaly -> Generate Spec -> LoRa TX");
    Serial.println("   Hub verifies with Azure AI");
    Serial.println("========================================");
    Serial.println();

    change_state(STATE_READY);
    last_heartbeat = millis();
}

void update_gps() {
    gps_update();

    if (millis() - last_gps_update < 5000)
        return;
    last_gps_update = millis();

    double lat, lon;
    if (gps_get_location(lat, lon)) {
        cached_lat = lat;
        cached_lon = lon;
        has_gps_fix = true;
        Serial.print("[GPS] Fix: ");
        Serial.print(lat, 6);
        Serial.print(", ");
        Serial.println(lon, 6);
    } else {
        has_gps_fix = false;
    }
}

void update_display() {
    if (millis() - last_display_update < 500)
        return;
    last_display_update = millis();

    int battery = (int)read_battery_percent();

    // Show detailed view every other 8 seconds
    unsigned long cycle_time = millis() % 16000;
    bool show_detail = (cycle_time >= 8000);

    if (show_detail) {
        display_detailed_status(battery, has_gps_fix, cached_lat, cached_lon,
                                mic_is_working, current_audio_level, total_anomalies);
        return;
    }

    switch (current_state) {
    case STATE_READY:
        display_status(DISPLAY_READY, battery, has_gps_fix);
        break;
    case STATE_LISTENING:
        display_status(DISPLAY_LISTENING, battery, has_gps_fix);
        break;
    case STATE_ANOMALY_DETECTED:
    case STATE_SENDING_SPECTROGRAM:
        display_status(DISPLAY_ALERT, battery, has_gps_fix);
        break;
    case STATE_GPS_WAIT:
        display_status(DISPLAY_GPS_WAIT, battery, has_gps_fix);
        break;
    case STATE_HEARTBEAT:
        display_status(DISPLAY_HEARTBEAT, battery, has_gps_fix);
        break;
    case STATE_LOW_BATTERY:
        display_status(DISPLAY_LOW_BATTERY, battery, has_gps_fix);
        break;
    case STATE_ERROR:
        display_status(DISPLAY_ERROR, battery, has_gps_fix);
        break;
    default:
        break;
    }
}

void handle_audio_anomaly_detection() {
    static unsigned long last_audio_debug = 0;

    // Capture audio
    if (!audio_capture_read(audio_buf, AUDIO_CHUNK_SIZE)) {
        mic_is_working = false;
        current_audio_level = 0.0;

        if (millis() - last_audio_debug > 2000) {
            Serial.println("[Audio] Read failed - mic not working");
            last_audio_debug = millis();
        }
        return;
    }

    mic_is_working = true;
    
    // Calculate audio level for display
    int16_t max_sample = 0;
    int32_t sum = 0;
    for (int i = 0; i < AUDIO_CHUNK_SIZE; i++) {
        int16_t sample = abs(audio_buf[i]);
        sum += sample;
        if (sample > max_sample) max_sample = sample;
    }

    current_audio_level = (float)max_sample / 1000.0;
    if (current_audio_level > 1.0) current_audio_level = 1.0;

    // Debug output every 2 seconds
    if (millis() - last_audio_debug > 2000) {
        Serial.print("[Audio] Max: ");
        Serial.print(max_sample);
        Serial.print(", Avg: ");
        Serial.println(sum / AUDIO_CHUNK_SIZE);
        last_audio_debug = millis();
    }

    // Generate spectrogram for anomaly detection
    if (!spectrogram_generate(audio_buf, AUDIO_CHUNK_SIZE, spectrogram)) {
        return;  // Not enough audio
    }

    current_energy = spectrogram_get_energy(spectrogram);

    // Check if this is an anomaly (unusual sound detected)
    // Threshold is lower than actual chainsaw detection - let Azure AI decide
    bool is_anomaly = spectrogram_is_anomaly(spectrogram, ANOMALY_THRESHOLD);

    if (is_anomaly) {
        unsigned long now = millis();

        // Require consecutive anomalies to avoid single spikes
        if (now - last_anomaly_time < 3000) {  // Within 3 seconds
            consecutive_anomalies++;
        } else {
            consecutive_anomalies = 1;
        }
        last_anomaly_time = now;

        Serial.print("[Anomaly] Detected! Energy: ");
        Serial.print(current_energy, 3);
        Serial.print(", Consecutive: ");
        Serial.println(consecutive_anomalies);

        // After CONSECUTIVE_REQUIRED anomalies, send spectrogram
        if (consecutive_anomalies >= CONSECUTIVE_REQUIRED) {
            // Cooldown check
            if (now - last_alert > LORA_COOLDOWN_MS) {
                Serial.println();
                Serial.println("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!");
                Serial.println("!!   ANOMALY CONFIRMED - SENDING   !!");
                Serial.println("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!");

                change_state(STATE_SENDING_SPECTROGRAM);
                
                // Flash LED
                flash_led(3, 100, 100);

                // Compress spectrogram
                size_t compressed_len = spectrogram_to_jpeg(spectrogram, 
                                                            spectrogram_compressed, 
                                                            sizeof(spectrogram_compressed));

                if (compressed_len > 0) {
                    Serial.print("[TX] Sending spectrogram: ");
                    Serial.print(compressed_len);
                    Serial.println(" bytes");

                    // Show alert on display
                    display_alert(current_energy, (int)read_battery_percent());

                    // Send spectrogram via multi-packet LoRa
                    int packets = lora_send_spectrogram(
                        spectrogram_compressed, compressed_len,
                        NODE_ID, current_energy,
                        has_gps_fix ? cached_lat : 0.0,
                        has_gps_fix ? cached_lon : 0.0,
                        (int)read_battery_percent()
                    );

                    if (packets > 0) {
                        total_spectrograms_sent++;
                        Serial.print("[TX] Spectrogram sent in ");
                        Serial.print(packets);
                        Serial.println(" packets");
                    }
                } else {
                    // Fallback: send JSON alert without spectrogram
                    Serial.println("[TX] Compression failed, sending JSON alert");
                    send_json_message("alert", current_energy);
                }

                total_anomalies++;
                last_alert = now;
                consecutive_anomalies = 0;

                // Visual feedback
                for (int i = 0; i < 6; i++) {
                    digitalWrite(LED_PIN, (i % 2) ? HIGH : LOW);
                    delay(500);
                }
                digitalWrite(LED_PIN, LOW);

                change_state(STATE_LISTENING);
            }
        }
    }
}

void handle_heartbeat() {
    unsigned long now = millis();

    if (now - last_heartbeat > HEARTBEAT_INTERVAL_MS) {
        Serial.println("[HEARTBEAT] Sending periodic update...");

        SystemState prev_state = current_state;
        change_state(STATE_HEARTBEAT);
        update_display();

        send_json_message("heartbeat", 0);
        total_heartbeats++;

        last_heartbeat = now;
        delay(500);

        change_state(prev_state);
    }
}

void check_battery() {
    float battery = read_battery_percent();

    if (battery < 5.0) {
        Serial.println("[POWER] Critical battery! Entering deep sleep...");
        change_state(STATE_LOW_BATTERY);
        update_display();

        send_json_message("low_battery", 0);
        delay(3000);

        lora_sleep();
        esp_deep_sleep(10 * 60 * 1000000ULL);
    }
}

void loop() {
    static unsigned long last_loop_debug = 0;
    static unsigned long loop_count = 0;
    loop_count++;

    // Debug every 5 seconds
    if (millis() - last_loop_debug > 5000) {
        Serial.print("[LOOP] mic=");
        Serial.print(mic_is_working ? "OK" : "FAIL");
        Serial.print(", energy=");
        Serial.print(current_energy, 3);
        Serial.print(", GPS=");
        Serial.print(has_gps_fix ? "FIX" : "NO");
        Serial.print(", anomalies=");
        Serial.print(total_anomalies);
        Serial.print(", specs_sent=");
        Serial.println(total_spectrograms_sent);
        last_loop_debug = millis();
    }

    update_gps();
    update_display();
    check_battery();

    switch (current_state) {
    case STATE_READY:
        change_state(STATE_LISTENING);
        break;

    case STATE_LISTENING:
        handle_audio_anomaly_detection();
        handle_heartbeat();
        break;

    case STATE_ERROR:
        delay(5000);
        ESP.restart();
        break;

    default:
        change_state(STATE_LISTENING);
        break;
    }

    delay(10);  // Prevent watchdog issues
}
