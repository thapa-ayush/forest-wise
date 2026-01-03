/*
 * gps_handler.cpp - Forest Guardian GPS Handler
 * For GY-NEO6MV2 GPS Module on ESP32-S3
 *
 * Communicates via UART at 9600 baud
 * Uses TinyGPSPlus library (v1.0.3+)
 * Provides location data for alert geolocation
 */
#include "gps_handler.h"
#include "config.h"
#include <TinyGPSPlus.h>

// Use UART1 for GPS
HardwareSerial gps_serial(1);

// TinyGPS++ parser
TinyGPSPlus gps;

// GPS state
static bool gps_initialized = false;
static double last_lat = 0.0;
static double last_lon = 0.0;
static bool has_valid_fix = false;
static unsigned long last_fix_time = 0;
static unsigned long chars_total = 0;
static unsigned long sentences_total = 0;

bool gps_init()
{
    Serial.println("[GPS] Initializing GPS module...");
    Serial.print("[GPS] Pins: RX=GPIO");
    Serial.print(GPS_RX);
    Serial.print(", TX=GPIO");
    Serial.println(GPS_TX);
    Serial.println("[GPS] Using TinyGPSPlus library");
    Serial.flush();

    // Initialize serial port for GPS
    // RX pin receives data FROM GPS TX
    // TX pin sends data TO GPS RX (not usually needed for NEO-6M)
    gps_serial.begin(GPS_BAUD, SERIAL_8N1, GPS_RX, GPS_TX);
    delay(1000); // Give GPS module time to stabilize after power-up

    // Try to get some data to verify connection
    Serial.println("[GPS] Checking for NMEA data (3 seconds)...");
    Serial.flush();

    unsigned long start = millis();
    bool got_data = false;
    int char_count = 0;
    bool found_nmea = false;
    char nmea_buf[10] = {0};
    int nmea_idx = 0;

    while (millis() - start < 3000)
    {
        while (gps_serial.available())
        {
            char c = gps_serial.read();
            gps.encode(c);
            got_data = true;
            char_count++;
            
            // Look for NMEA sentence start
            if (c == '$')
            {
                found_nmea = true;
                nmea_idx = 0;
            }
            else if (found_nmea && nmea_idx < 5)
            {
                nmea_buf[nmea_idx++] = c;
            }
        }
        delay(10);
    }

    Serial.print("[GPS] Received ");
    Serial.print(char_count);
    Serial.print(" chars");
    
    if (found_nmea)
    {
        nmea_buf[5] = 0;
        Serial.print(", NMEA prefix: $");
        Serial.println(nmea_buf);
    }
    else
    {
        Serial.println(", No NMEA found");
    }
    Serial.flush();

    if (got_data && found_nmea)
    {
        Serial.println("[GPS] ✓ GPS module responding with NMEA data!");
        Serial.println("[GPS] Note: Fix may take 30s-2min outdoors");
        gps_initialized = true;
        return true;
    }
    else if (got_data)
    {
        Serial.println("[GPS] Got data but no NMEA sentences");
        Serial.println("[GPS] Check: Is GPS TX connected to ESP32 GPIO19 (RX)?");
        gps_initialized = true; // Still try to use it
        return true;
    }
    else
    {
        Serial.println("[GPS] ✗ No GPS data received!");
        Serial.println("[GPS] Check wiring:");
        Serial.println("[GPS]   GPS VCC -> 3.3V");
        Serial.println("[GPS]   GPS GND -> GND");
        Serial.println("[GPS]   GPS TX  -> ESP32 GPIO19");
        Serial.println("[GPS]   GPS RX  -> ESP32 GPIO20 (optional)");
        gps_initialized = false;
        return false;
    }
}

void gps_update()
{
    if (!gps_initialized)
        return;

    // Process all available GPS data - call this frequently!
    static unsigned long last_gps_debug = 0;
    int chars_processed = 0;

    while (gps_serial.available())
    {
        char c = gps_serial.read();
        if (gps.encode(c))
        {
            // A complete sentence was parsed
            sentences_total++;
        }
        chars_processed++;
        chars_total++;
    }

    // Debug every 5 seconds
    if (millis() - last_gps_debug > 5000)
    {
        last_gps_debug = millis();
        Serial.print("[GPS] Sats: ");
        Serial.print(gps.satellites.value());
        Serial.print(", HDOP: ");
        Serial.print(gps.hdop.hdop(), 1);
        Serial.print(", Fix: ");
        Serial.print(gps.location.isValid() ? "YES" : "NO");
        
        // Age display - show meaningful message
        unsigned long age = gps.location.age();
        Serial.print(", Age: ");
        if (age > 86400000)  // More than 1 day = never updated
        {
            Serial.println("NEVER (searching for satellites...)");
        }
        else
        {
            Serial.print(age);
            Serial.println("ms");
        }
    }

    // Check for valid fix - TinyGPSPlus considers location valid when GPGGA/GPRMC has fix
    if (gps.location.isValid())
    {
        // Only update if location is fresh (age < 2 seconds)
        if (gps.location.age() < 2000)
        {
            last_lat = gps.location.lat();
            last_lon = gps.location.lng();
            has_valid_fix = true;
            last_fix_time = millis();
        }
    }

    // Invalidate fix if no update for 10 seconds
    if (has_valid_fix && (millis() - last_fix_time > 10000))
    {
        has_valid_fix = false;
        Serial.println("[GPS] Fix lost (no update in 10s)");
    }
}

bool gps_get_location(double &lat, double &lon)
{
    // Update GPS before reading
    gps_update();

    if (has_valid_fix)
    {
        lat = last_lat;
        lon = last_lon;
        return true;
    }

    // Try to get fresh data with timeout
    unsigned long start = millis();
    while (millis() - start < 1000)
    { // 1 second timeout
        while (gps_serial.available())
        {
            gps.encode(gps_serial.read());
        }

        if (gps.location.isValid())
        {
            lat = gps.location.lat();
            lon = gps.location.lng();
            last_lat = lat;
            last_lon = lon;
            has_valid_fix = true;
            last_fix_time = millis();
            return true;
        }
        delay(10);
    }

    // Return last known position if we had one
    if (last_lat != 0.0 || last_lon != 0.0)
    {
        lat = last_lat;
        lon = last_lon;
        return false; // Return false to indicate stale data
    }

    lat = 0.0;
    lon = 0.0;
    return false;
}

bool gps_has_fix()
{
    gps_update();
    return has_valid_fix;
}

int gps_get_satellites()
{
    // Update GPS data first
    gps_update();
    
    // Return satellite count (0 if not valid)
    // TinyGPSPlus satellites.value() returns the count from $GPGGA sentence
    return gps.satellites.value();
}

float gps_get_hdop()
{
    if (gps.hdop.isValid())
    {
        return gps.hdop.hdop();
    }
    return 99.9; // Invalid/unknown
}

// Additional helper: Check if GPS is receiving data at all
bool gps_is_receiving()
{
    return chars_total > 0;
}
