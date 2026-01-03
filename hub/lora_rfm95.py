# lora_rfm95.py - Forest Guardian Hub
# Updated for Raspberry Pi 5 using lgpio instead of RPi.GPIO
import spidev
import time
import logging

# Use lgpio for Raspberry Pi 5 compatibility
try:
    import lgpio
    GPIO_LIB = 'lgpio'
except ImportError:
    lgpio = None
    GPIO_LIB = None
    logging.warning("lgpio not available - LoRa hardware disabled")

LORA_SCK = 11
LORA_MISO = 9
LORA_MOSI = 10
LORA_NSS = 8
LORA_RST = 25
LORA_DIO0 = 24
LORA_FREQ = 915e6

class RFM95:
    def __init__(self):
        self.h = None  # GPIO handle
        self.spi = None
        
        if lgpio is None:
            raise RuntimeError("lgpio library not available")
        
        # Open GPIO chip (chip 0 for Pi 5)
        self.h = lgpio.gpiochip_open(0)
        
        # Setup pins
        lgpio.gpio_claim_output(self.h, LORA_RST)
        lgpio.gpio_claim_output(self.h, LORA_NSS)
        lgpio.gpio_claim_input(self.h, LORA_DIO0)
        
        # Set NSS high (deselect)
        lgpio.gpio_write(self.h, LORA_NSS, 1)
        
        # Setup SPI
        self.spi = spidev.SpiDev()
        self.spi.open(0, 0)
        self.spi.max_speed_hz = 5000000
        self.spi.mode = 0
        
        self.reset()
        logging.info("RFM95W initialized with lgpio (Pi 5 compatible)")

    def reset(self):
        lgpio.gpio_write(self.h, LORA_RST, 0)
        time.sleep(0.1)
        lgpio.gpio_write(self.h, LORA_RST, 1)
        time.sleep(0.1)

    def read_packet(self):
        # Placeholder: Implement RFM95W receive logic
        # For demo, return None
        return None

    def close(self):
        if self.spi:
            self.spi.close()
        if self.h is not None:
            lgpio.gpiochip_close(self.h)

lora = None
try:
    lora = RFM95()
except Exception as e:
    logging.error(f"Failed to initialize RFM95: {e}")
