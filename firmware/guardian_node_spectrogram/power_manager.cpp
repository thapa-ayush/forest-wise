/*
 * power_manager.cpp - Forest Guardian Power Management Handler
 * For Heltec WiFi LoRa 32 V3 battery monitoring and power control
 *
 * The Heltec V3 has built-in battery management with:
 * - Battery voltage reading via ADC
 * - Vext control for external power
 * - LED indicator
 */
#include "power_manager.h"
#include "config.h"
#include <esp_sleep.h>
#include <esp_wifi.h>

// Battery voltage calibration for Heltec V3
// The battery voltage is read through a voltage divider
const float VOLTAGE_DIVIDER_RATIO = 2.0; // R1 = R2 = 220K
const float ADC_REFERENCE = 3.3;
const int ADC_RESOLUTION = 4095;

// LiPo discharge curve approximation points
const float BATTERY_CURVE[][2] = {
    {4.20, 100.0}, // Full charge
    {4.10, 95.0},
    {4.00, 85.0},
    {3.90, 75.0},
    {3.80, 65.0},
    {3.70, 50.0},
    {3.60, 35.0},
    {3.50, 20.0},
    {3.40, 10.0},
    {3.30, 5.0},
    {3.00, 0.0} // Empty (cutoff)
};
const int CURVE_POINTS = sizeof(BATTERY_CURVE) / sizeof(BATTERY_CURVE[0]);

// Moving average filter for battery readings
const int FILTER_SIZE = 10;
static float voltage_readings[FILTER_SIZE];
static int reading_index = 0;
static bool filter_initialized = false;

void power_manager_init()
{
    Serial.println("[Power] Initializing power manager...");

    // Configure ADC for battery reading
    analogReadResolution(12);
    analogSetAttenuation(ADC_11db); // Full scale 3.3V
    pinMode(BATTERY_PIN, INPUT);

    // Initialize Vext control (external power for peripherals)
    pinMode(VEXT_CTRL, OUTPUT);
    digitalWrite(VEXT_CTRL, LOW); // Enable Vext (active low on Heltec V3)

    // Configure LED
    pinMode(LED_PIN, OUTPUT);
    digitalWrite(LED_PIN, LOW);

    // Initialize filter with current reading
    float initial_voltage = read_battery_voltage();
    for (int i = 0; i < FILTER_SIZE; i++)
    {
        voltage_readings[i] = initial_voltage;
    }
    filter_initialized = true;

    Serial.print("[Power] Initial battery: ");
    Serial.print(read_battery_percent());
    Serial.println("%");
}

float read_battery_voltage()
{
    // Take multiple readings and average
    uint32_t sum = 0;
    for (int i = 0; i < 10; i++)
    {
        sum += analogRead(BATTERY_PIN);
        delayMicroseconds(100);
    }
    float adc_value = sum / 10.0;

    // Convert ADC to voltage
    float voltage = (adc_value / ADC_RESOLUTION) * ADC_REFERENCE * VOLTAGE_DIVIDER_RATIO;

    // Apply moving average filter
    if (filter_initialized)
    {
        voltage_readings[reading_index] = voltage;
        reading_index = (reading_index + 1) % FILTER_SIZE;

        float filtered_voltage = 0;
        for (int i = 0; i < FILTER_SIZE; i++)
        {
            filtered_voltage += voltage_readings[i];
        }
        voltage = filtered_voltage / FILTER_SIZE;
    }

    return voltage;
}

float read_battery_percent()
{
    float voltage = read_battery_voltage();

    // If voltage is very low or zero, assume USB power (no battery)
    // Return 100% to prevent shutdown
    if (voltage < 2.5)
    {
        return 100.0; // USB powered, no battery connected
    }

    // Clamp voltage to valid range
    if (voltage >= BATTERY_CURVE[0][0])
        return 100.0;
    if (voltage <= BATTERY_CURVE[CURVE_POINTS - 1][0])
        return 0.0;

    // Linear interpolation between curve points
    for (int i = 0; i < CURVE_POINTS - 1; i++)
    {
        if (voltage >= BATTERY_CURVE[i + 1][0] && voltage <= BATTERY_CURVE[i][0])
        {
            float v_range = BATTERY_CURVE[i][0] - BATTERY_CURVE[i + 1][0];
            float p_range = BATTERY_CURVE[i][1] - BATTERY_CURVE[i + 1][1];
            float v_offset = voltage - BATTERY_CURVE[i + 1][0];
            return BATTERY_CURVE[i + 1][1] + (v_offset / v_range) * p_range;
        }
    }

    // Fallback linear calculation
    float percent = (voltage - BATTERY_EMPTY) / (BATTERY_FULL - BATTERY_EMPTY) * 100.0;
    if (percent > 100.0)
        percent = 100.0;
    if (percent < 0.0)
        percent = 0.0;
    return percent;
}

void enter_light_sleep(uint32_t sleep_ms)
{
    Serial.print("[Power] Entering light sleep for ");
    Serial.print(sleep_ms);
    Serial.println(" ms");

    // Configure wake up source
    esp_sleep_enable_timer_wakeup(sleep_ms * 1000);

    // Enter light sleep
    esp_light_sleep_start();

    Serial.println("[Power] Woke from light sleep");
}

void enter_deep_sleep(uint32_t sleep_us)
{
    Serial.print("[Power] Entering deep sleep for ");
    Serial.print(sleep_us / 1000000);
    Serial.println(" seconds");

    // Disable Vext to save power
    digitalWrite(VEXT_CTRL, HIGH);

    // Configure wake up
    esp_sleep_enable_timer_wakeup(sleep_us);

    // Enter deep sleep (will not return)
    esp_deep_sleep_start();
}

void set_charging_led(bool enabled)
{
    digitalWrite(LED_PIN, enabled ? HIGH : LOW);
}
