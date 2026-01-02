/*
 * gps_handler.h - Forest Guardian GPS Handler
 * For GY-NEO6MV2 GPS Module
 */
#ifndef GPS_HANDLER_H
#define GPS_HANDLER_H

#include <Arduino.h>

// Initialize GPS module
bool gps_init();

// Get current location
bool gps_get_location(double &lat, double &lon);

// Get GPS fix quality info
bool gps_has_fix();
int gps_get_satellites();
float gps_get_hdop();

// Update GPS (call frequently in loop)
void gps_update();

#endif // GPS_HANDLER_H
