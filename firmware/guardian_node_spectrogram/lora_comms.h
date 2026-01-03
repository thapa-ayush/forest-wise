/*
 * lora_comms.h - Forest Guardian LoRa Communication Handler
 * For Heltec WiFi LoRa 32 V3 with SX1262
 * 
 * Supports multi-packet transmission for spectrogram images
 */
#ifndef LORA_COMMS_H
#define LORA_COMMS_H

#include <Arduino.h>

// Multi-packet protocol constants
#define LORA_MAX_PAYLOAD 200      // Max bytes per packet (conservative for reliability)
#define LORA_PACKET_HEADER 8      // Header: magic(2) + node_id_hash(2) + seq(1) + total(1) + len(2)
#define LORA_PACKET_DATA (LORA_MAX_PAYLOAD - LORA_PACKET_HEADER)  // ~192 bytes data per packet

// Packet types
#define PKT_TYPE_JSON     0x01    // JSON message (alert, heartbeat)
#define PKT_TYPE_SPEC_START 0x10  // Start of spectrogram transmission
#define PKT_TYPE_SPEC_DATA  0x11  // Spectrogram data chunk
#define PKT_TYPE_SPEC_END   0x12  // End of spectrogram (with metadata)

// Initialize LoRa module
bool lora_init();

// Send string message via LoRa (JSON alerts/heartbeats)
bool lora_send(const String &msg);

// Send raw bytes via LoRa
bool lora_send_bytes(const uint8_t *data, size_t len);

// Send multi-packet spectrogram
// Returns number of packets sent, 0 on failure
int lora_send_spectrogram(const uint8_t* spec_data, size_t spec_len, 
                          const char* node_id, float confidence,
                          double lat, double lon, int battery);

// Get transmission statistics
int lora_get_tx_count();
int lora_get_fail_count();

// Get signal quality info
int lora_get_rssi();
float lora_get_snr();

// Check if LoRa is ready
bool lora_is_ready();

// Receive data (non-blocking)
// Returns number of bytes received, 0 if none, -1 on error
int lora_receive(uint8_t* buffer, size_t max_len);

// Check for hub ACK (returns true if ACK received from hub)
bool lora_check_for_ack();

// Power management
void lora_sleep();
void lora_wake();

#endif // LORA_COMMS_H
