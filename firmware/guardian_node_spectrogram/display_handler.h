#ifndef DISPLAY_HANDLER_H
#define DISPLAY_HANDLER_H

#include <Arduino.h>

// Display status modes
enum DisplayMode
{
    DISPLAY_BOOT,
    DISPLAY_READY,
    DISPLAY_LISTENING,
    DISPLAY_ALERT,
    DISPLAY_HEARTBEAT,
    DISPLAY_LOW_BATTERY,
    DISPLAY_GPS_WAIT,
    DISPLAY_ERROR,
    DISPLAY_STATUS_DETAIL
};

void display_init();
void display_clear();
void display_boot_screen();
void display_status(DisplayMode mode, int battery_percent, bool gps_fix);
void display_alert(float confidence, int battery_percent);
void display_message(const char *line1, const char *line2 = nullptr, const char *line3 = nullptr);
void display_progress(const char *title, int percent);
void display_detailed_status(int battery_percent, bool gps_fix, double lat, double lon, bool mic_ok, float audio_level, int alert_count = 0);

// NEW: Single page live stats with LoRa/hub status
void display_live_stats(int battery_percent, bool gps_fix, double lat, double lon,
                        bool mic_ok, float audio_level, float energy,
                        int alert_count, int specs_sent,
                        int lora_tx_count = 0, unsigned long last_tx_time = 0, bool hub_ack = false);

#endif // DISPLAY_HANDLER_H
