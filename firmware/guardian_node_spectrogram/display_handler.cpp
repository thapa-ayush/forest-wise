/*
 * display_handler.cpp - Forest Guardian OLED Display Handler
 * For Heltec WiFi LoRa 32 V3 built-in SSD1306 display
 */
#include "display_handler.h"
#include "config.h"
#include <Wire.h>
#include <U8g2lib.h>

// Heltec V3 OLED Display (SSD1306 128x64)
// Use software I2C with correct pins for Heltec V3
U8G2_SSD1306_128X64_NONAME_F_SW_I2C display(U8G2_R0, OLED_SCL, OLED_SDA, OLED_RST);

// Icons (8x8 bitmaps)
static const unsigned char icon_battery[] PROGMEM = {0x3C, 0x24, 0xFF, 0x81, 0x81, 0x81, 0x81, 0xFF};
static const unsigned char icon_gps[] PROGMEM = {0x18, 0x24, 0x42, 0x99, 0x99, 0x42, 0x24, 0x18};
static const unsigned char icon_lora[] PROGMEM = {0x00, 0x42, 0x24, 0x18, 0x18, 0x24, 0x42, 0x00};
static const unsigned char icon_alert[] PROGMEM = {0x18, 0x18, 0x3C, 0x3C, 0x7E, 0x7E, 0x00, 0x18};
static const unsigned char icon_tree[] PROGMEM = {0x18, 0x3C, 0x7E, 0xFF, 0x18, 0x18, 0x18, 0x3C};

void display_init()
{
    // Enable Vext power for OLED (Heltec V3 specific)
    // Vext is active LOW on Heltec V3
    pinMode(VEXT_CTRL, OUTPUT);
    digitalWrite(VEXT_CTRL, LOW); // Turn ON Vext (powers OLED)
    delay(100);                   // Wait for power to stabilize

    // Reset display
    pinMode(OLED_RST, OUTPUT);
    digitalWrite(OLED_RST, LOW);
    delay(50);
    digitalWrite(OLED_RST, HIGH);
    delay(50);

    display.begin();
    display.setFont(u8g2_font_6x10_tf);
    display.setContrast(255);
    display.enableUTF8Print();
    display_boot_screen();
}

void display_clear()
{
    display.clearBuffer();
    display.sendBuffer();
}

void display_boot_screen()
{
    display.clearBuffer();

    // Draw tree icons
    display.drawXBMP(48, 5, 8, 8, icon_tree);
    display.drawXBMP(60, 5, 8, 8, icon_tree);
    display.drawXBMP(72, 5, 8, 8, icon_tree);

    // Title
    display.setFont(u8g2_font_helvB10_tr);
    display.drawStr(8, 32, "FOREST GUARDIAN");

    // Subtitle
    display.setFont(u8g2_font_6x10_tf);
    display.drawStr(18, 46, "Chainsaw Detector");

    // Version
    display.drawStr(45, 60, "v1.0.0");

    display.sendBuffer();
}

void draw_header(int battery_percent, bool gps_fix)
{
    // Node ID
    display.setFont(u8g2_font_5x7_tf);
    display.drawStr(0, 7, NODE_ID);

    // GPS indicator
    if (gps_fix)
    {
        display.drawXBMP(78, 0, 8, 8, icon_gps);
    }
    else
    {
        display.drawFrame(78, 0, 8, 8);
        display.drawStr(80, 7, "?");
    }

    // Battery icon and percentage
    display.drawXBMP(95, 0, 8, 8, icon_battery);
    char bat_str[6];
    snprintf(bat_str, sizeof(bat_str), "%d%%", battery_percent);
    display.drawStr(105, 7, bat_str);

    // Separator line
    display.drawHLine(0, 10, 128);
}

void display_status(DisplayMode mode, int battery_percent, bool gps_fix)
{
    display.clearBuffer();
    draw_header(battery_percent, gps_fix);

    switch (mode)
    {
    case DISPLAY_BOOT:
        display.setFont(u8g2_font_helvB10_tr);
        display.drawStr(25, 38, "BOOTING...");
        break;

    case DISPLAY_READY:
        display.setFont(u8g2_font_helvB10_tr);
        display.drawStr(40, 32, "READY");
        display.setFont(u8g2_font_6x10_tf);
        display.drawStr(15, 48, "System initialized");
        display.drawStr(20, 60, "Waiting for sound");
        break;

    case DISPLAY_LISTENING:
    {
        display.setFont(u8g2_font_helvB10_tr);
        display.drawStr(20, 30, "LISTENING");
        display.setFont(u8g2_font_6x10_tf);
        display.drawStr(10, 50, "See live stats...");
        break;
    }

    case DISPLAY_HEARTBEAT:
        display.drawXBMP(60, 18, 8, 8, icon_lora);
        display.setFont(u8g2_font_helvB10_tr);
        display.drawStr(20, 42, "HEARTBEAT");
        display.setFont(u8g2_font_6x10_tf);
        display.drawStr(30, 58, "Transmitting");
        break;

    case DISPLAY_GPS_WAIT:
        display.drawXBMP(60, 18, 8, 8, icon_gps);
        display.setFont(u8g2_font_helvB10_tr);
        display.drawStr(15, 42, "GPS SEARCH");
        display.setFont(u8g2_font_6x10_tf);
        display.drawStr(15, 58, "Acquiring fix...");
        break;

    case DISPLAY_LOW_BATTERY:
        display.drawXBMP(60, 18, 8, 8, icon_battery);
        display.setFont(u8g2_font_helvB10_tr);
        display.drawStr(5, 42, "LOW BATTERY");
        display.setFont(u8g2_font_6x10_tf);
        display.drawStr(10, 58, "Entering sleep...");
        break;

    case DISPLAY_ERROR:
        display.setFont(u8g2_font_helvB10_tr);
        display.drawStr(35, 38, "ERROR");
        break;
    }

    display.sendBuffer();
}

void display_alert(float confidence, int battery_percent)
{
    display.clearBuffer();

    // Inverted display for alert effect
    display.setDrawColor(1);
    display.drawBox(0, 0, 128, 64);
    display.setDrawColor(0);

    // Alert icon
    display.drawXBMP(60, 2, 8, 8, icon_alert);

    // Alert text
    display.setFont(u8g2_font_helvB12_tr);
    display.drawStr(3, 28, "!! CHAINSAW !!");

    // Confidence
    display.setFont(u8g2_font_helvB10_tr);
    char conf_str[20];
    snprintf(conf_str, sizeof(conf_str), "CONF: %d%%", (int)(confidence * 100));
    display.drawStr(28, 45, conf_str);

    // Status
    display.setFont(u8g2_font_6x10_tf);
    display.drawStr(15, 60, "ALERT TRANSMITTED");

    display.setDrawColor(1);
    display.sendBuffer();
}

void display_message(const char *line1, const char *line2, const char *line3)
{
    display.clearBuffer();
    display.setFont(u8g2_font_6x10_tf);

    if (line1)
        display.drawStr(0, 20, line1);
    if (line2)
        display.drawStr(0, 35, line2);
    if (line3)
        display.drawStr(0, 50, line3);

    display.sendBuffer();
}

void display_progress(const char *title, int percent)
{
    display.clearBuffer();
    display.setFont(u8g2_font_6x10_tf);

    // Title
    int title_width = display.getStrWidth(title);
    display.drawStr((128 - title_width) / 2, 20, title);

    // Progress bar outline
    display.drawFrame(10, 30, 108, 16);

    // Progress bar fill
    int fill_width = (percent * 104) / 100;
    if (fill_width > 0)
    {
        display.drawBox(12, 32, fill_width, 12);
    }

    // Percentage text
    char pct_str[10];
    snprintf(pct_str, sizeof(pct_str), "%d%%", percent);
    int pct_width = display.getStrWidth(pct_str);
    display.drawStr((128 - pct_width) / 2, 60, pct_str);

    display.sendBuffer();
}

void display_detailed_status(int battery_percent, bool gps_fix, double lat, double lon, bool mic_ok, float audio_level, int alert_count)
{
    // Redirect to live stats (compatibility wrapper)
    display_live_stats(battery_percent, gps_fix, lat, lon, mic_ok, audio_level, 0, alert_count, 0, 0, 0, false);
}

// NEW: Single page with all live stats and LoRa/hub status
void display_live_stats(int battery_percent, bool gps_fix, double lat, double lon,
                        bool mic_ok, float audio_level, float energy,
                        int alert_count, int specs_sent,
                        int lora_tx_count, unsigned long last_tx_time, bool hub_ack)
{
    display.clearBuffer();
    display.setFont(u8g2_font_5x7_tf);

    // === TOP ROW: Node ID | Status | Battery ===
    display.drawStr(0, 7, NODE_ID);

    // Status indicator (filled=OK, empty=error)
    if (mic_ok && gps_fix)
    {
        display.drawDisc(70, 4, 3);
    }
    else if (mic_ok)
    {
        display.drawCircle(70, 4, 3);
        display.drawPixel(70, 4);
    }
    else
    {
        display.drawCircle(70, 4, 3);
    }

    // Battery
    char bat_str[8];
    snprintf(bat_str, sizeof(bat_str), "%d%%", battery_percent);
    display.drawStr(108, 7, bat_str);

    // Battery icon mini
    display.drawFrame(95, 1, 10, 6);
    display.drawBox(105, 2, 2, 4);
    int bat_fill = (battery_percent * 8) / 100;
    if (bat_fill > 0)
        display.drawBox(96, 2, bat_fill, 4);

    display.drawHLine(0, 9, 128);

    // === ROW 2: GPS coordinates or status ===
    display.drawStr(0, 18, "GPS:");
    if (gps_fix)
    {
        char coord_str[24];
        snprintf(coord_str, sizeof(coord_str), "%.4f,%.4f", lat, lon);
        display.drawStr(22, 18, coord_str);
    }
    else
    {
        display.drawStr(22, 18, "No Fix");
    }

    // === ROW 3: Audio level bar ===
    display.drawStr(0, 27, "AUD:");
    display.drawFrame(22, 21, 60, 7);
    int level_width = (int)(audio_level * 56);
    if (level_width > 56)
        level_width = 56;
    if (level_width > 0)
        display.drawBox(24, 23, level_width, 3);

    // Energy value
    char energy_str[10];
    snprintf(energy_str, sizeof(energy_str), "E:%.2f", energy);
    display.drawStr(85, 27, energy_str);

    // === ROW 4: Alerts & Specs sent ===
    display.drawStr(0, 36, "ALT:");
    char alert_str[6];
    snprintf(alert_str, sizeof(alert_str), "%d", alert_count);
    display.drawStr(22, 36, alert_str);

    display.drawStr(45, 36, "TX:");
    char tx_str[6];
    snprintf(tx_str, sizeof(tx_str), "%d", specs_sent);
    display.drawStr(62, 36, tx_str);

    // Mic status
    display.drawStr(85, 36, mic_ok ? "MIC:OK" : "MIC:!!");

    display.drawHLine(0, 38, 128);

    // === BOTTOM: LoRa & Hub Status ===
    display.setFont(u8g2_font_5x7_tf);

    // LoRa TX count
    display.drawStr(0, 48, "LORA TX:");
    char lora_str[8];
    snprintf(lora_str, sizeof(lora_str), "%d", lora_tx_count);
    display.drawStr(45, 48, lora_str);

    // Last TX time
    display.drawStr(65, 48, "Last:");
    if (last_tx_time > 0)
    {
        unsigned long ago = (millis() - last_tx_time) / 1000;
        char time_str[10];
        if (ago < 60)
        {
            snprintf(time_str, sizeof(time_str), "%lus", ago);
        }
        else
        {
            snprintf(time_str, sizeof(time_str), "%lum", ago / 60);
        }
        display.drawStr(95, 48, time_str);
    }
    else
    {
        display.drawStr(95, 48, "--");
    }

    // Hub connection status row
    display.drawStr(0, 58, "HUB:");
    if (hub_ack)
    {
        display.drawStr(25, 58, "CONNECTED");
        display.drawDisc(95, 55, 4); // Filled = connected
    }
    else
    {
        display.drawStr(25, 58, "WAITING");
        display.drawCircle(95, 55, 4); // Empty = not yet
    }

    // Hopping indicator (blinking shows system is active)
    static bool hop_blink = false;
    static unsigned long last_hop_blink = 0;
    if (millis() - last_hop_blink > 500)
    {
        hop_blink = !hop_blink;
        last_hop_blink = millis();
    }

    // Node active indicator
    display.setFont(u8g2_font_4x6_tf);
    if (hop_blink)
    {
        display.drawDisc(120, 55, 4);
    }
    else
    {
        display.drawCircle(120, 55, 4);
    }

    display.sendBuffer();
}
