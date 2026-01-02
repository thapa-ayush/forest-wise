/*
 * Forest Guardian - Hardware Diagnostic Test
 * Tests: GPIO, I2S Mic, GPS UART
 *
 * Upload this and share the FULL serial output!
 */

#include <driver/i2s.h>
#include <HardwareSerial.h>

// ===== PIN DEFINITIONS =====
// Heltec V3 - Header J3 (left) for Mic, Header J2 (right) for GPS
#define MIC_SCK 7 // I2S Clock - GPIO7, Pin 18 left
#define MIC_WS 6  // I2S Word Select - GPIO6, Pin 17 left
#define MIC_SD 5  // I2S Data - GPIO5, Pin 16 left

#define GPS_RX 19 // ESP RX <- GPS TX - GPIO19, Pin 18 right
#define GPS_TX 20 // ESP TX -> GPS RX - GPIO20, Pin 17 right

HardwareSerial GPSSerial(1);

void setup()
{
    Serial.begin(115200);
    delay(3000);

    Serial.println("\n");
    Serial.println("############################################");
    Serial.println("#   FOREST GUARDIAN HARDWARE DIAGNOSTIC    #");
    Serial.println("############################################\n");

    // Test 1: Basic GPIO
    testGPIO();

    // Test 2: GPS UART
    testGPS();

    // Test 3: I2S Microphone
    testMicrophone();

    Serial.println("\n============ DIAGNOSTIC COMPLETE ============\n");
}

void testGPIO()
{
    Serial.println("--- TEST 1: GPIO Pin Check ---");

    // Check if pins are valid for ESP32-S3
    int testPins[] = {MIC_SCK, MIC_WS, MIC_SD, GPS_RX, GPS_TX};
    const char *pinNames[] = {"MIC_SCK", "MIC_WS", "MIC_SD", "GPS_RX", "GPS_TX"};

    for (int i = 0; i < 5; i++)
    {
        int pin = testPins[i];
        Serial.print("  ");
        Serial.print(pinNames[i]);
        Serial.print(" (GPIO ");
        Serial.print(pin);
        Serial.print("): ");

        // Check if pin is in valid range for ESP32-S3
        if (pin >= 0 && pin <= 48)
        {
            // Try to set as input and read
            pinMode(pin, INPUT);
            int val = digitalRead(pin);
            Serial.print("OK (reading ");
            Serial.print(val);
            Serial.println(")");
        }
        else
        {
            Serial.println("INVALID PIN!");
        }
    }
    Serial.println();
}

void testGPS()
{
    Serial.println("--- TEST 2: GPS UART Check ---");
    Serial.print("  Initializing UART1 on RX=GPIO");
    Serial.print(GPS_RX);
    Serial.print(", TX=GPIO");
    Serial.println(GPS_TX);

    GPSSerial.begin(9600, SERIAL_8N1, GPS_RX, GPS_TX);
    delay(100);

    Serial.println("  Waiting 5 seconds for GPS data...");
    Serial.println("  (GPS needs 3.3V on VCC, not 5V for some modules)");
    Serial.println();

    unsigned long start = millis();
    int bytesReceived = 0;
    bool gotNMEA = false;
    char nmeaBuffer[100];
    int bufIdx = 0;

    while (millis() - start < 5000)
    {
        while (GPSSerial.available())
        {
            char c = GPSSerial.read();
            bytesReceived++;

            // Collect NMEA sentence
            if (c == '$')
            {
                bufIdx = 0;
            }
            if (bufIdx < 99)
            {
                nmeaBuffer[bufIdx++] = c;
                nmeaBuffer[bufIdx] = '\0';
            }
            if (c == '\n' && bufIdx > 5)
            {
                gotNMEA = true;
                Serial.print("  NMEA: ");
                Serial.print(nmeaBuffer);
                bufIdx = 0;
            }
        }
        delay(10);
    }

    Serial.print("  Bytes received: ");
    Serial.println(bytesReceived);

    if (bytesReceived == 0)
    {
        Serial.println("  !! NO DATA FROM GPS !!");
        Serial.println("  Check: VCC->3.3V, GND->GND, GPS_TX->GPIO47");
        Serial.println("  Note: GPS TX pin connects to ESP RX pin (GPIO47)");
    }
    else if (!gotNMEA)
    {
        Serial.println("  !! Got bytes but no valid NMEA !!");
        Serial.println("  Might be wrong baud rate or noise");
    }
    else
    {
        Serial.println("  GPS WORKING!");
    }

    GPSSerial.end();
    Serial.println();
}

void testMicrophone()
{
    Serial.println("--- TEST 3: I2S Microphone Check ---");
    Serial.print("  Pins: SCK=GPIO");
    Serial.print(MIC_SCK);
    Serial.print(", WS=GPIO");
    Serial.print(MIC_WS);
    Serial.print(", SD=GPIO");
    Serial.println(MIC_SD);

    // I2S config
    i2s_config_t i2s_config = {
        .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX),
        .sample_rate = 16000,
        .bits_per_sample = I2S_BITS_PER_SAMPLE_32BIT,
        .channel_format = I2S_CHANNEL_FMT_RIGHT_LEFT,
        .communication_format = I2S_COMM_FORMAT_STAND_I2S,
        .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
        .dma_buf_count = 4,
        .dma_buf_len = 256,
        .use_apll = false,
        .tx_desc_auto_clear = false,
        .fixed_mclk = 0};

    esp_err_t err = i2s_driver_install(I2S_NUM_0, &i2s_config, 0, NULL);
    Serial.print("  I2S driver install: ");
    if (err != ESP_OK)
    {
        Serial.println(esp_err_to_name(err));
        return;
    }
    Serial.println("OK");

    i2s_pin_config_t pin_config = {
        .mck_io_num = I2S_PIN_NO_CHANGE,
        .bck_io_num = MIC_SCK,
        .ws_io_num = MIC_WS,
        .data_out_num = I2S_PIN_NO_CHANGE,
        .data_in_num = MIC_SD};

    err = i2s_set_pin(I2S_NUM_0, &pin_config);
    Serial.print("  I2S set pins: ");
    if (err != ESP_OK)
    {
        Serial.println(esp_err_to_name(err));
        i2s_driver_uninstall(I2S_NUM_0);
        return;
    }
    Serial.println("OK");

    i2s_start(I2S_NUM_0);
    delay(500);

    // Read samples
    Serial.println("  Reading audio samples (tap the mic!)...");

    int32_t buffer[128];
    int32_t maxL = 0, maxR = 0;
    int32_t sumL = 0, sumR = 0;
    int countL = 0, countR = 0;

    for (int round = 0; round < 10; round++)
    {
        size_t bytes_read = 0;
        i2s_read(I2S_NUM_0, buffer, sizeof(buffer), &bytes_read, 100);

        int samples = bytes_read / 4;
        for (int i = 0; i < samples; i += 2)
        {
            int32_t left = buffer[i] >> 14;
            int32_t right = buffer[i + 1] >> 14;

            int32_t absL = abs(left);
            int32_t absR = abs(right);

            if (absL > maxL)
                maxL = absL;
            if (absR > maxR)
                maxR = absR;

            sumL += absL;
            sumR += absR;
            countL++;
            countR++;
        }
        delay(50);
    }

    Serial.print("  Left channel  - Max: ");
    Serial.print(maxL);
    Serial.print(", Avg: ");
    Serial.println(countL > 0 ? sumL / countL : 0);

    Serial.print("  Right channel - Max: ");
    Serial.print(maxR);
    Serial.print(", Avg: ");
    Serial.println(countR > 0 ? sumR / countR : 0);

    if (maxL == 0 && maxR == 0)
    {
        Serial.println();
        Serial.println("  !! NO AUDIO SIGNAL !!");
        Serial.println("  Check wiring:");
        Serial.println("    INMP441 VDD  -> 3.3V (NOT 5V!)");
        Serial.println("    INMP441 GND  -> GND");
        Serial.println("    INMP441 SCK  -> GPIO4");
        Serial.println("    INMP441 WS   -> GPIO5");
        Serial.println("    INMP441 SD   -> GPIO6");
        Serial.println("    INMP441 L/R  -> GND (left) or 3.3V (right)");
    }
    else if (maxL > 0 && maxR == 0)
    {
        Serial.println("  Microphone on LEFT channel");
    }
    else if (maxR > 0 && maxL == 0)
    {
        Serial.println("  Microphone on RIGHT channel");
    }
    else
    {
        Serial.println("  MICROPHONE WORKING!");
    }

    i2s_stop(I2S_NUM_0);
    i2s_driver_uninstall(I2S_NUM_0);
    Serial.println();
}

void loop()
{
    Serial.println("\n>> Press RESET to run diagnostic again <<\n");
    delay(10000);
}
