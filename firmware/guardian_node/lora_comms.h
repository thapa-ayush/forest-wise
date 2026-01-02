/*
 * lora_comms.h - Forest Guardian LoRa Communication Handler
 * For Heltec WiFi LoRa 32 V3 with SX1262
 */
#ifndef LORA_COMMS_H
#define LORA_COMMS_H

#include <Arduino.h>

// Initialize LoRa module
bool lora_init();

// Send string message via LoRa
bool lora_send(const String &msg);

// Send raw bytes via LoRa
bool lora_send_bytes(const uint8_t *data, size_t len);

// Get transmission statistics
int lora_get_tx_count();
int lora_get_fail_count();

// Get signal quality info
int lora_get_rssi();
float lora_get_snr();

// Check if LoRa is ready
bool lora_is_ready();

// Power management
void lora_sleep();
void lora_wake();

#endif // LORA_COMMS_H
