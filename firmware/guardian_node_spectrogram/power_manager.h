/*
 * power_manager.h - Forest Guardian Power Management Handler
 * For Heltec WiFi LoRa 32 V3 battery monitoring
 */
#ifndef POWER_MANAGER_H
#define POWER_MANAGER_H

#include <Arduino.h>

// Initialize power manager
void power_manager_init();

// Read battery percentage (0-100)
float read_battery_percent();

// Read raw battery voltage
float read_battery_voltage();

// Enter light sleep mode
void enter_light_sleep(uint32_t sleep_ms);

// Enter deep sleep mode
void enter_deep_sleep(uint32_t sleep_us);

// Enable/disable charging LED indicator
void set_charging_led(bool enabled);

#endif // POWER_MANAGER_H
