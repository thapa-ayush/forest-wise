/*
 * lora_comms.cpp - Forest Guardian LoRa Communication Handler
 * For Heltec WiFi LoRa 32 V3 with SX1262
 */
#include "lora_comms.h"
#include "config.h"
#include <RadioLib.h>

// SX1262 module connections for Heltec V3
// NSS, DIO1, NRST, BUSY
SX1262 lora = new Module(LORA_SS, LORA_DIO1, LORA_RST, LORA_BUSY);

static bool lora_ready = false;
static int tx_count = 0;
static int tx_fail_count = 0;

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
