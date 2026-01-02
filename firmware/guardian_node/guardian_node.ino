/*
 * Forest Guardian - guardian_node.ino
 * Main firmware for Heltec WiFi LoRa 32 V3 (ESP32-S3 + SX1262)
 *
 * Detects chainsaw sounds using FFT spectral analysis, sends alerts via LoRa,
 * displays status on built-in OLED, manages power efficiently.
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
 *   - arduinoFFT (spectral analysis)
 *   - ArduinoJson (message formatting)
 */
#include <Arduino.h>
#include "config.h"
#include "audio_capture.h"
#include "gps_handler.h"
#include "ml_inference.h"
#include "lora_comms.h"
#include "display_handler.h"
#include "power_manager.h"
#include <ArduinoJson.h>

// State machine
enum SystemState
{
    STATE_BOOT,
    STATE_INIT,
    STATE_GPS_WAIT,
    STATE_READY,
    STATE_LISTENING,
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

// Audio buffer
static int16_t audio_buf[AUDIO_BUFFER_SIZE];

// Statistics
int total_alerts = 0;
int total_heartbeats = 0;

// Audio monitoring
bool mic_is_working = false;
float current_audio_level = 0.0;
unsigned long last_detail_display = 0;

void change_state(SystemState new_state)
{
    Serial.print("[FSM] State: ");
    Serial.print(current_state);
    Serial.print(" -> ");
    Serial.println(new_state);
    current_state = new_state;
    state_start_time = millis();
}

void send_message(const char *type, float confidence)
{
    StaticJsonDocument<256> doc;
    doc["node_id"] = NODE_ID;
    doc["type"] = type;
    doc["confidence"] = (int)(confidence * 100);
    doc["lat"] = has_gps_fix ? cached_lat : 0.0;
    doc["lon"] = has_gps_fix ? cached_lon : 0.0;
    doc["battery"] = (int)read_battery_percent();
    doc["timestamp"] = millis() / 1000;
    doc["alerts"] = total_alerts;
    doc["tx_count"] = lora_get_tx_count();

    String msg;
    serializeJson(doc, msg);

    if (lora_send(msg))
    {
        Serial.print("[TX] Sent ");
        Serial.print(type);
        Serial.print(": ");
        Serial.println(msg);
    }
    else
    {
        Serial.println("[TX] Failed to send message");
    }
}

// LED flash helper for alerts
void flash_led(int times, int on_ms, int off_ms)
{
    for (int i = 0; i < times; i++)
    {
        digitalWrite(LED_PIN, HIGH);
        delay(on_ms);
        digitalWrite(LED_PIN, LOW);
        delay(off_ms);
    }
}

void setup()
{
    // Initialize LED first for immediate feedback
    pinMode(LED_PIN, OUTPUT);
    digitalWrite(LED_PIN, HIGH); // LED on during boot

    // Initialize serial for debugging
    Serial.begin(115200);
    delay(1000);
    Serial.println();
    Serial.println("========================================");
    Serial.println("    FOREST GUARDIAN - Node Startup");
    Serial.println("========================================");
    Serial.print("Node ID: ");
    Serial.println(NODE_ID);
    Serial.print("Firmware: v1.0.0");
    Serial.println();

    digitalWrite(LED_PIN, LOW); // LED off after serial init

    // Initialize display first for visual feedback
    Serial.println("[INIT] Display...");
    display_init();
    delay(2000); // Show boot screen

    // Show initialization progress
    display_progress("Initializing...", 0);

    // Initialize power manager
    Serial.println("[INIT] Power manager...");
    display_progress("Power system", 10);
    power_manager_init();

    float battery = read_battery_percent();
    Serial.print("[INIT] Battery: ");
    Serial.print(battery);
    Serial.println("%");

    if (battery < 10.0)
    {
        Serial.println("[ERROR] Battery critically low!");
        display_message("CRITICAL", "Battery too low", "Shutting down...");
        delay(3000);
        esp_deep_sleep_start();
    }

    // Initialize audio capture
    Serial.println("[INIT] Audio capture...");
    display_progress("Audio system", 25);
    if (!audio_capture_init())
    {
        Serial.println("[ERROR] Audio init failed!");
        display_message("ERROR", "Audio init failed", "Check microphone");
        delay(3000);
    }

    // Initialize GPS
    Serial.println("[INIT] GPS...");
    display_progress("GPS module", 45);
    if (!gps_init())
    {
        Serial.println("[WARNING] GPS init failed, continuing without GPS");
    }

    // Initialize ML inference
    Serial.println("[INIT] ML inference engine...");
    display_progress("AI Engine", 65);
    if (!ml_inference_init())
    {
        Serial.println("[ERROR] ML init failed!");
        display_message("ERROR", "ML init failed", "Check model");
        delay(3000);
    }

    // Initialize LoRa
    Serial.println("[INIT] LoRa transceiver...");
    display_progress("LoRa radio", 85);
    if (!lora_init())
    {
        Serial.println("[ERROR] LoRa init failed!");
        display_message("ERROR", "LoRa init failed", "Check antenna");
        delay(3000);
    }

    display_progress("Complete!", 100);
    delay(1000);

    // Send boot message
    Serial.println("[INIT] Sending boot notification...");
    send_message("boot", 0);

    // Initialization complete
    Serial.println();
    Serial.println("========================================");
    Serial.println("       Initialization Complete!");
    Serial.println("========================================");
    Serial.println();

    change_state(STATE_READY);
    last_heartbeat = millis();
}

void update_gps()
{
    // Call gps_update every loop iteration to process incoming data
    gps_update();

    // Only check for fix every 5 seconds
    if (millis() - last_gps_update < 5000)
        return;
    last_gps_update = millis();

    double lat, lon;
    if (gps_get_location(lat, lon))
    {
        cached_lat = lat;
        cached_lon = lon;
        has_gps_fix = true;
        Serial.print("[GPS] Fix: ");
        Serial.print(lat, 6);
        Serial.print(", ");
        Serial.println(lon, 6);
    }
    else
    {
        has_gps_fix = false;
    }
}

void update_display()
{
    if (millis() - last_display_update < 500)
        return; // Update every 500ms
    last_display_update = millis();

    int battery = (int)read_battery_percent();

    // Show detailed view: 8 seconds normal, 8 seconds detailed (16 sec cycle)
    unsigned long cycle_time = millis() % 16000;
    bool show_detail = (cycle_time >= 8000);

    if (show_detail)
    {
        // Show detailed GPS, mic status, and alert count
        display_detailed_status(battery, has_gps_fix, cached_lat, cached_lon,
                                mic_is_working, current_audio_level, total_alerts);
        return;
    }

    switch (current_state)
    {
    case STATE_READY:
        display_status(DISPLAY_READY, battery, has_gps_fix);
        break;
    case STATE_LISTENING:
        display_status(DISPLAY_LISTENING, battery, has_gps_fix);
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

void handle_audio_detection()
{
    // Capture audio - read only a small chunk for quick response
    static unsigned long last_audio_debug = 0;

    if (!audio_capture_read(audio_buf, AUDIO_CHUNK_SIZE))
    {
        mic_is_working = false;
        current_audio_level = 0.0;

        // Debug output every 2 seconds
        if (millis() - last_audio_debug > 2000)
        {
            Serial.println("[Audio] Read failed - mic not working");
            last_audio_debug = millis();
        }
        return;
    }

    // Mic is working, calculate audio level from chunk
    mic_is_working = true;
    int16_t max_sample = 0;
    int32_t sum = 0;

    for (int i = 0; i < AUDIO_CHUNK_SIZE; i++)
    {
        int16_t sample = abs(audio_buf[i]);
        sum += sample;
        if (sample > max_sample)
            max_sample = sample;
    }

    // Debug output every 2 seconds
    if (millis() - last_audio_debug > 2000)
    {
        Serial.print("[Audio] Max sample: ");
        Serial.print(max_sample);
        Serial.print(", Avg: ");
        Serial.println(sum / AUDIO_CHUNK_SIZE);
        last_audio_debug = millis();
    }

    // Use peak value for visualization - very sensitive scaling
    current_audio_level = (float)max_sample / 1000.0;
    if (current_audio_level > 1.0)
        current_audio_level = 1.0;
    if (current_audio_level < 0.05 && max_sample > 10)
        current_audio_level = 0.05; // Show minimum bar if any sound detected

    // Run ML inference (use chunk size, not full buffer)
    float confidence = ml_inference_run(audio_buf, AUDIO_CHUNK_SIZE);

    // Check for detection
    if (confidence >= DETECTION_THRESHOLD)
    {
        unsigned long now = millis();

        // Cooldown check to avoid spam
        if (now - last_alert > LORA_COOLDOWN_MS)
        {
            Serial.println();
            Serial.println("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!");
            Serial.println("!!     CHAINSAW DETECTED!!!         !!");
            Serial.println("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!");
            Serial.print("Confidence: ");
            Serial.print(confidence * 100);
            Serial.println("%");

            // VISUAL ALERT: Flash LED rapidly
            flash_led(5, 100, 100); // 5 quick flashes

            // Show alert on display (inverted screen)
            display_alert(confidence, (int)read_battery_percent());

            // Send alert via LoRa
            send_message("alert", confidence);

            total_alerts++;
            last_alert = now;

            // Keep alert visible and flash LED for 5 seconds
            for (int i = 0; i < 10; i++)
            {
                digitalWrite(LED_PIN, (i % 2) ? HIGH : LOW);
                delay(500);
            }
            digitalWrite(LED_PIN, LOW);
        }
    }
}

void handle_heartbeat()
{
    unsigned long now = millis();

    if (now - last_heartbeat > HEARTBEAT_INTERVAL_MS)
    {
        Serial.println("[HEARTBEAT] Sending periodic update...");

        SystemState prev_state = current_state;
        change_state(STATE_HEARTBEAT);
        update_display();

        send_message("heartbeat", 0);
        total_heartbeats++;

        last_heartbeat = now;
        delay(500); // Brief display of heartbeat

        change_state(prev_state);
    }
}

void check_battery()
{
    float battery = read_battery_percent();

    if (battery < 5.0)
    {
        Serial.println("[POWER] Critical battery! Entering deep sleep...");
        change_state(STATE_LOW_BATTERY);
        update_display();

        // Send low battery alert
        send_message("low_battery", 0);

        delay(3000);

        // Enter deep sleep for 10 minutes
        lora_sleep();
        esp_deep_sleep(10 * 60 * 1000000ULL);
    }
    else if (battery < 20.0)
    {
        Serial.println("[POWER] Low battery warning");
        // Continue but reduce activity
    }
}

void loop()
{
    static unsigned long last_loop_debug = 0;
    static unsigned long loop_count = 0;
    loop_count++;

    // Debug every 5 seconds
    if (millis() - last_loop_debug > 5000)
    {
        Serial.print("[LOOP] Running, mic=");
        Serial.print(mic_is_working ? "OK" : "FAIL");
        Serial.print(", level=");
        Serial.print((int)(current_audio_level * 100));
        Serial.print("%, GPS=");
        Serial.print(has_gps_fix ? "FIX" : "NO");
        Serial.print(", loops=");
        Serial.println(loop_count);
        last_loop_debug = millis();
    }

    // Update GPS in background
    update_gps();

    // Update display
    update_display();

    // Check battery
    check_battery();

    // Main state machine
    switch (current_state)
    {
    case STATE_READY:
        change_state(STATE_LISTENING);
        break;

    case STATE_LISTENING:
        handle_audio_detection();
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

    // Small delay to prevent watchdog issues
    delay(10);
}
