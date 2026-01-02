# Hardware Assembly Guide

## Guardian Node (Forest Deployment)

### Components
- Heltec WiFi LoRa 32 V3 (ESP32-S3 + SX1262 LoRa)
- INMP441 MEMS I2S digital microphone
- GY-NEO6MV2 GPS module
- 2x 18650 Li-ion batteries
- 12V 2W solar panel
- TP4056 charger module
- Buck converter (12V → 5V)
- Waterproof enclosure

### Wiring

#### INMP441 to Heltec
| INMP441 | Heltec Pin |
|---------|------------|
| VCC     | 3.3V       |
| GND     | GND        |
| SCK     | GPIO4      |
| WS      | GPIO5      |
| SD      | GPIO6      |
| L/R     | GND        |

#### GPS to Heltec
| GPS     | Heltec Pin |
|---------|------------|
| VCC     | 3.3V       |
| GND     | GND        |
| TX      | GPIO44     |
| RX      | GPIO43     |

#### Power
- Solar panel → TP4056 IN
- TP4056 OUT → Buck converter IN
- Buck converter OUT (5V) → Heltec VIN

### Assembly Steps
1. Solder headers to all modules
2. Connect INMP441 to Heltec using jumper wires
3. Connect GPS to Heltec
4. Connect TP4056 and buck converter
5. Mount batteries
6. Mount solar panel on enclosure lid
7. Secure all modules inside enclosure
8. Drill hole for microphone (cover with waterproof membrane)

### Notes
- Test all connections before sealing enclosure
- Use silicone sealant for waterproofing
- Ensure antenna is external or enclosure is RF-transparent

---

## Hub (Ranger Station)

### Components
- Raspberry Pi 5
- RFM95W LoRa module
- Jumper wires
- Enclosure

### Wiring

#### RFM95W to Raspberry Pi 5
| RFM95W | Raspberry Pi Pin |
|--------|------------------|
| VCC    | Pin 17 (3.3V)    |
| GND    | Pin 20 (GND)     |
| SCK    | Pin 23 (GPIO11)  |
| MISO   | Pin 21 (GPIO9)   |
| MOSI   | Pin 19 (GPIO10)  |
| NSS    | Pin 24 (GPIO8)   |
| RST    | Pin 22 (GPIO25)  |
| DIO0   | Pin 18 (GPIO24)  |

### Assembly Steps
1. Connect RFM95W to Raspberry Pi GPIO header
2. Attach antenna to RFM95W
3. Connect Raspberry Pi to power and network
4. Install OS and software (see setup_guide.md)

### Notes
- Use logic level shifter if needed (RFM95W is 3.3V)
- Place hub near window or use external antenna for best range

---

## Photos
(Insert assembly photos here)

---

## Troubleshooting
- **No I2S audio:** Check SCK/WS/SD pins
- **GPS not locking:** Ensure clear sky view
- **LoRa not receiving:** Check antenna and frequency

---

## License
MIT
