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
        display.drawStr(10, 45, "Monitoring audio...");

        // Draw animated sound bars
        static uint8_t bar_anim = 0;
        bar_anim = (bar_anim + 1) % 8;
        for (int i = 0; i < 7; i++)
        {
            int h = 4 + ((i + bar_anim) % 5) * 3;
            display.drawBox(25 + i * 12, 62 - h, 8, h);
        }
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
    display.clearBuffer();
    display.setFont(u8g2_font_5x7_tf);

    // Header with clear status indicator
    display.drawStr(0, 7, "FOREST GUARDIAN");
    char bat_str[10];
    snprintf(bat_str, sizeof(bat_str), "%d%%", battery_percent);
    display.drawStr(105, 7, bat_str);

    // Status indicator box - shows system is ACTIVE
    if (mic_ok)
    {
        display.drawBox(85, 0, 15, 8); // Filled = OK
        display.setDrawColor(0);
        display.drawStr(87, 7, "OK");
        display.setDrawColor(1);
    }
    else
    {
        display.drawFrame(85, 0, 15, 8);
        display.drawStr(87, 7, "!!");
    }
    display.drawHLine(0, 9, 128);

    // GPS Section
    display.drawStr(0, 18, "GPS:");
    if (gps_fix)
    {
        char lat_str[16], lon_str[16];
        snprintf(lat_str, sizeof(lat_str), "%.4f", lat);
        snprintf(lon_str, sizeof(lon_str), "%.4f", lon);
        display.drawStr(22, 18, lat_str);
        display.drawStr(68, 18, lon_str);
    }
    else
    {
        display.drawStr(22, 18, "Searching...");
    }

    // Mic Section with audio bar
    display.drawStr(0, 28, "MIC:");
    if (mic_ok)
    {
        // Audio level bar
        display.drawFrame(22, 22, 80, 8);
        int level_width = (int)(audio_level * 76);
        if (level_width > 76)
            level_width = 76;
        if (level_width < 2 && audio_level > 0)
            level_width = 2;
        display.drawBox(24, 24, level_width, 4);

        char lvl_str[8];
        snprintf(lvl_str, sizeof(lvl_str), "%d%%", (int)(audio_level * 100));
        display.drawStr(105, 28, lvl_str);
    }
    else
    {
        display.drawStr(22, 28, "ERROR!");
    }

    // Alert counter - important for user to see detections
    display.drawHLine(0, 32, 128);
    display.setFont(u8g2_font_6x10_tf);
    char alert_str[24];
    snprintf(alert_str, sizeof(alert_str), "DETECTIONS: %d", alert_count);
    display.drawStr(25, 44, alert_str);

    // Status line - animated to show system is active
    display.drawHLine(0, 50, 128);
    display.setFont(u8g2_font_5x7_tf);

    // Blinking indicator dot
    static unsigned long last_blink = 0;
    static bool blink_on = true;
    if (millis() - last_blink > 500)
    {
        blink_on = !blink_on;
        last_blink = millis();
    }

    if (blink_on)
    {
        display.drawDisc(10, 58, 3); // Filled circle when "on"
    }
    else
    {
        display.drawCircle(10, 58, 3); // Empty circle when "off"
    }
    display.drawStr(18, 60, "MONITORING ACTIVE");

    display.sendBuffer();
}
