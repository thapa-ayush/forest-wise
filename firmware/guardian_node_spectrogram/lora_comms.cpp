/*
 * lora_comms.cpp - Forest Guardian LoRa Communication Handler
 * For Heltec WiFi LoRa 32 V3 with SX1262
 * 
 * Supports multi-packet transmission for spectrogram images
 */
#include "lora_comms.h"
#include "config.h"
#include <RadioLib.h>
#include <ArduinoJson.h>

// SX1262 module connections for Heltec V3
// NSS, DIO1, NRST, BUSY
SX1262 lora = new Module(LORA_SS, LORA_DIO1, LORA_RST, LORA_BUSY);

static bool lora_ready = false;
static int tx_count = 0;
static int tx_fail_count = 0;
static uint16_t packet_sequence = 0;  // Rolling sequence for multi-packet

// Simple hash for node ID (to include in packet headers)
uint16_t hash_node_id(const char* node_id) {
    uint16_t hash = 0;
    while (*node_id) {
        hash = hash * 31 + *node_id++;
    }
    return hash;
}

bool lora_init()
{
    Serial.println("[LoRa] Initializing SX1262...");

    // Initialize SPI for LoRa
    SPI.begin(LORA_SCK, LORA_MISO, LORA_MOSI, LORA_SS);

    // Initialize SX1262 with parameters
    // Heltec V3 uses TCXO at 1.8V - CRITICAL for proper operation!
    int state = lora.begin(
        LORA_FREQ,             // Frequency (915 MHz for Canada)
        LORA_BANDWIDTH,        // Bandwidth (125 kHz)
        LORA_SPREADING_FACTOR, // Spreading factor (10)
        LORA_CODING_RATE,      // Coding rate 4/5
        LORA_SYNC_WORD,        // Sync word (0x12 private - MUST MATCH HUB!)
        LORA_TX_POWER,         // TX power (14 dBm)
        LORA_PREAMBLE,         // Preamble length
        1.8,                   // TCXO voltage - Heltec V3 requires 1.8V!
        false                  // Use DC-DC regulator
    );

    if (state != RADIOLIB_ERR_NONE)
    {
        Serial.print("[LoRa] Init failed, code: ");
        Serial.println(state);
        lora_ready = false;
        return false;
    }

    // Set current limit
    lora.setCurrentLimit(140.0);

    // Enable CRC
    lora.setCRC(true);

    // Set DIO2 as RF switch control
    lora.setDio2AsRfSwitch(true);

    Serial.println("[LoRa] SX1262 initialized successfully!");
    Serial.print("[LoRa] Frequency: ");
    Serial.print(LORA_FREQ);
    Serial.println(" MHz");

    lora_ready = true;
    return true;
}

bool lora_send(const String &msg)
{
    if (!lora_ready)
    {
        Serial.println("[LoRa] Not ready, reinitializing...");
        if (!lora_init())
            return false;
    }

    Serial.print("[LoRa] Transmitting ");
    Serial.print(msg.length());
    Serial.println(" bytes...");

    int state = lora.transmit(msg.c_str(), msg.length());

    if (state == RADIOLIB_ERR_NONE)
    {
        tx_count++;
        Serial.print("[LoRa] TX success #");
        Serial.println(tx_count);
        return true;
    }
    else
    {
        tx_fail_count++;
        Serial.print("[LoRa] TX failed, code: ");
        Serial.print(state);
        Serial.print(", failures: ");
        Serial.println(tx_fail_count);
        return false;
    }
}

bool lora_send_bytes(const uint8_t *data, size_t len)
{
    if (!lora_ready)
    {
        if (!lora_init())
            return false;
    }

    int state = lora.transmit(data, len);

    if (state == RADIOLIB_ERR_NONE)
    {
        tx_count++;
        return true;
    }
    else
    {
        tx_fail_count++;
        return false;
    }
}

int lora_get_tx_count()
{
    return tx_count;
}

int lora_get_fail_count()
{
    return tx_fail_count;
}

int lora_get_rssi()
{
    return lora.getRSSI();
}

float lora_get_snr()
{
    return lora.getSNR();
}

bool lora_is_ready()
{
    return lora_ready;
}

void lora_sleep()
{
    if (lora_ready)
    {
        lora.sleep();
        Serial.println("[LoRa] Entered sleep mode");
    }
}

void lora_wake()
{
    if (lora_ready)
    {
        lora.standby();
        Serial.println("[LoRa] Woke from sleep");
    }
}

// Receive data with timeout - switches to RX briefly then back to standby
int lora_receive(uint8_t* buffer, size_t max_len, uint16_t timeout_ms)
{
    if (!lora_ready) return -1;
    
    // Set receive timeout (in symbols)
    // At SF10, BW125, one symbol = 8.19ms, so 100ms ~ 12 symbols
    uint16_t timeout_symbols = (timeout_ms / 8) + 1;
    lora.setRxBoostedGainMode(true);
    
    // Start receive with timeout (SX126x uses symbol timeout)
    int state = lora.receive(buffer, max_len);
    
    if (state == RADIOLIB_ERR_NONE)
    {
        int len = lora.getPacketLength();
        Serial.print("[LoRa] Received ");
        Serial.print(len);
        Serial.println(" bytes");
        return len;
    }
    else if (state == RADIOLIB_ERR_RX_TIMEOUT)
    {
        return 0;  // No data (normal)
    }
    else
    {
        // Don't spam errors for no data
        if (state != RADIOLIB_ERR_NONE)
        {
            Serial.print("[LoRa] RX state: ");
            Serial.println(state);
        }
        return -1;
    }
}

// Check for hub ACK message
// ACK format: "ACK:<node_id>" or JSON with "type":"ack"
bool lora_check_for_ack()
{
    if (!lora_ready) return false;
    
    uint8_t rx_buffer[128];
    
    // Quick check - use scanChannel to see if anything is being received
    // This is faster than waiting for full packet
    int activity = lora.scanChannel();
    if (activity == RADIOLIB_PREAMBLE_DETECTED)
    {
        Serial.println("[LoRa] Activity detected, waiting for packet...");
        
        // Something detected, wait for packet with short timeout
        unsigned long start = millis();
        while (millis() - start < 500)  // 500ms max wait
        {
            int state = lora.receive(rx_buffer, sizeof(rx_buffer) - 1);
            
            if (state == RADIOLIB_ERR_NONE)
            {
                int len = lora.getPacketLength();
                if (len > 0 && len < sizeof(rx_buffer))
                {
                    rx_buffer[len] = 0;  // Null terminate
                    String msg = String((char*)rx_buffer);
                    
                    Serial.print("[LoRa] RX: ");
                    Serial.println(msg);
                    
                    // Check for ACK message - look for any ACK indicator
                    if (msg.indexOf("ack") >= 0 || msg.indexOf("ACK") >= 0 || 
                        msg.indexOf(NODE_ID) >= 0 || msg.indexOf("hub") >= 0)
                    {
                        Serial.println("[LoRa] ✅ Hub ACK received!");
                        return true;
                    }
                }
                break;  // Got a packet, exit loop
            }
            else if (state == RADIOLIB_ERR_RX_TIMEOUT)
            {
                break;  // Timeout, exit
            }
            delay(10);
        }
    }
    
    return false;
}

// Multi-packet spectrogram transmission
// Sends spectrogram data split across multiple LoRa packets
int lora_send_spectrogram(const uint8_t* spec_data, size_t spec_len,
                          const char* node_id, float confidence,
                          double lat, double lon, int battery) {
    if (!lora_ready) {
        if (!lora_init()) return 0;
    }
    
    uint16_t node_hash = hash_node_id(node_id);
    uint16_t session_id = packet_sequence++;  // Unique ID for this transmission
    
    // Calculate number of packets needed
    int num_packets = (spec_len + LORA_PACKET_DATA - 1) / LORA_PACKET_DATA;
    num_packets += 2;  // +1 for START, +1 for END with metadata
    
    Serial.print("[LoRa] Sending spectrogram: ");
    Serial.print(spec_len);
    Serial.print(" bytes in ");
    Serial.print(num_packets);
    Serial.println(" packets");
    
    uint8_t packet[LORA_MAX_PAYLOAD];
    int packets_sent = 0;
    
    // Packet 1: START packet with basic info
    packet[0] = 0x46;  // 'F' for Forest
    packet[1] = 0x47;  // 'G' for Guardian
    packet[2] = (node_hash >> 8) & 0xFF;
    packet[3] = node_hash & 0xFF;
    packet[4] = PKT_TYPE_SPEC_START;
    packet[5] = (session_id >> 8) & 0xFF;
    packet[6] = session_id & 0xFF;
    packet[7] = num_packets - 2;  // Number of data packets to follow
    packet[8] = (spec_len >> 8) & 0xFF;
    packet[9] = spec_len & 0xFF;
    
    // Add node_id as null-terminated string
    size_t node_id_len = strlen(node_id);
    if (node_id_len > 20) node_id_len = 20;
    memcpy(&packet[10], node_id, node_id_len);
    packet[10 + node_id_len] = 0;
    
    if (lora.transmit(packet, 11 + node_id_len) == RADIOLIB_ERR_NONE) {
        packets_sent++;
        tx_count++;
        Serial.println("[LoRa] START packet sent");
    } else {
        tx_fail_count++;
        Serial.println("[LoRa] START packet failed!");
        return 0;
    }
    
    delay(100);  // Brief delay between packets
    
    // Data packets
    size_t offset = 0;
    uint8_t seq = 0;
    while (offset < spec_len) {
        size_t chunk_len = spec_len - offset;
        if (chunk_len > LORA_PACKET_DATA) chunk_len = LORA_PACKET_DATA;
        
        packet[0] = 0x46;
        packet[1] = 0x47;
        packet[2] = (node_hash >> 8) & 0xFF;
        packet[3] = node_hash & 0xFF;
        packet[4] = PKT_TYPE_SPEC_DATA;
        packet[5] = (session_id >> 8) & 0xFF;
        packet[6] = session_id & 0xFF;
        packet[7] = seq++;  // Sequence within this transmission
        
        memcpy(&packet[8], &spec_data[offset], chunk_len);
        
        if (lora.transmit(packet, 8 + chunk_len) == RADIOLIB_ERR_NONE) {
            packets_sent++;
            tx_count++;
            Serial.print("[LoRa] DATA packet ");
            Serial.print(seq);
            Serial.print("/");
            Serial.print(num_packets - 2);
            Serial.println(" sent");
        } else {
            tx_fail_count++;
            Serial.print("[LoRa] DATA packet ");
            Serial.print(seq);
            Serial.println(" failed!");
            // Continue trying remaining packets
        }
        
        offset += chunk_len;
        delay(100);  // Brief delay between packets
    }
    
    // END packet with metadata
    packet[0] = 0x46;
    packet[1] = 0x47;
    packet[2] = (node_hash >> 8) & 0xFF;
    packet[3] = node_hash & 0xFF;
    packet[4] = PKT_TYPE_SPEC_END;
    packet[5] = (session_id >> 8) & 0xFF;
    packet[6] = session_id & 0xFF;
    packet[7] = packets_sent - 1;  // Actual data packets sent
    
    // Pack metadata as simple JSON in the payload
    StaticJsonDocument<128> meta;
    meta["conf"] = (int)(confidence * 100);
    meta["lat"] = lat;
    meta["lon"] = lon;
    meta["bat"] = battery;
    
    String meta_str;
    serializeJson(meta, meta_str);
    size_t meta_len = meta_str.length();
    if (meta_len > LORA_PACKET_DATA) meta_len = LORA_PACKET_DATA;
    memcpy(&packet[8], meta_str.c_str(), meta_len);
    
    if (lora.transmit(packet, 8 + meta_len) == RADIOLIB_ERR_NONE) {
        packets_sent++;
        tx_count++;
        Serial.println("[LoRa] END packet sent");
    } else {
        tx_fail_count++;
        Serial.println("[LoRa] END packet failed!");
    }
    
    Serial.print("[LoRa] Spectrogram transmission complete: ");
    Serial.print(packets_sent);
    Serial.print("/");
    Serial.print(num_packets);
    Serial.println(" packets");
    
    return packets_sent;
}
