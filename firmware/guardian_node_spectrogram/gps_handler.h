/*
 * gps_handler.h - Forest Guardian GPS Handler
 * For GY-NEO6MV2 GPS Module
 * Uses TinyGPSPlus library (v1.0.3+)
 */
#ifndef GPS_HANDLER_H
#define GPS_HANDLER_H

#include <Arduino.h>

// Initialize GPS module
bool gps_init();

// Get current location (returns true if valid fix)
bool gps_get_location(double &lat, double &lon);

// Get GPS fix status
bool gps_has_fix();

// Get satellite count (0 if none visible)
int gps_get_satellites();

// Get HDOP (horizontal dilution of precision, lower is better, 99.9 if invalid)
float gps_get_hdop();

// Update GPS (call frequently in loop to process incoming data)
void gps_update();

// Check if GPS is receiving any data at all
bool gps_is_receiving();

#endif // GPS_HANDLER_H
