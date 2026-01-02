/*
 * gps_handler.cpp - Forest Guardian GPS Handler
 * For GY-NEO6MV2 GPS Module on ESP32-S3
 *
 * Communicates via UART at 9600 baud
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

bool gps_init()
{
    Serial.println("[GPS] Initializing GPS module...");
    Serial.print("[GPS] Pins: RX=GPIO");
    Serial.print(GPS_RX);
    Serial.print(", TX=GPIO");
    Serial.println(GPS_TX);
    Serial.flush(); // Wait for serial to complete before GPS init

    // Initialize serial port for GPS
    gps_serial.begin(GPS_BAUD, SERIAL_8N1, GPS_RX, GPS_TX);
    delay(500); // Give GPS time to stabilize

    // Try to get some data to verify connection
    Serial.println("[GPS] Checking for NMEA data...");
    Serial.flush();

    unsigned long start = millis();
    bool got_data = false;
    int char_count = 0;
    bool found_dollar = false;

    while (millis() - start < 2000)
    {
        while (gps_serial.available())
        {
            char c = gps_serial.read();
            gps.encode(c);
            got_data = true;
            char_count++;
            if (c == '$')
                found_dollar = true;
        }
        delay(10);
    }

    Serial.print("[GPS] Received ");
    Serial.print(char_count);
    Serial.print(" chars, NMEA: ");
    Serial.println(found_dollar ? "YES" : "NO");
    Serial.flush();

    if (got_data && found_dollar)
    {
        Serial.println("[GPS] GPS module OK!");
        gps_initialized = true;
        return true;
    }
    else if (got_data)
    {
        Serial.println("[GPS] Got data but no NMEA - continuing anyway");
        gps_initialized = true;
        return true;
    }
    else
    {
        Serial.println("[GPS] WARNING: No GPS data!");
        gps_initialized = false;
        return false;
    }
}

void gps_update()
{
    if (!gps_initialized)
        return;

    // Process all available GPS data
    static unsigned long last_gps_debug = 0;
    int chars_processed = 0;

    while (gps_serial.available())
    {
        char c = gps_serial.read();
        gps.encode(c);
        chars_processed++;
    }

    // Debug every 5 seconds
    if (millis() - last_gps_debug > 5000)
    {
        last_gps_debug = millis();
        Serial.print("[GPS] Chars: ");
        Serial.print(chars_processed);
        Serial.print(", Sats: ");
        Serial.print(gps.satellites.value());
        Serial.print(", Valid: ");
        Serial.println(gps.location.isValid() ? "YES" : "NO");
    }

    // Check for valid fix
    if (gps.location.isValid() && gps.location.isUpdated())
    {
        last_lat = gps.location.lat();
        last_lon = gps.location.lng();
        has_valid_fix = true;
        last_fix_time = millis();
    }

    // Invalidate fix if no update for 10 seconds
    if (has_valid_fix && (millis() - last_fix_time > 10000))
    {
        has_valid_fix = false;
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
    if (gps.satellites.isValid())
    {
        return gps.satellites.value();
    }
    return 0;
}

float gps_get_hdop()
{
    if (gps.hdop.isValid())
    {
        return gps.hdop.hdop();
    }
    return 99.9; // Invalid/unknown
}
