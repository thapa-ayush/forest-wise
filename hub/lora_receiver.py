#!/usr/bin/env python3
"""
Forest Guardian Hub - LoRa Receiver
===================================
Receives alerts and spectrograms from Guardian nodes via LoRa.

Supports:
- JSON messages (alerts, heartbeats, boot)
- Multi-packet spectrogram transmissions for Azure AI analysis

This runs as a background thread alongside the Flask web app.

Hardware: Raspberry Pi + RFM95W/SX1276 LoRa module
"""

import json
import time
import threading
import logging
import os
import base64
from datetime import datetime
from queue import Queue
from collections import defaultdict

# Flag to enable/disable actual hardware (for development)
HARDWARE_ENABLED = False

try:
    import spidev
    import RPi.GPIO as GPIO
    HARDWARE_ENABLED = True
except ImportError:
    logging.warning("RPi.GPIO/spidev not available - running in simulation mode")

# LoRa Configuration - MUST MATCH NODE SETTINGS!
LORA_CONFIG = {
    'frequency': 915.0,       # MHz - same as node
    'bandwidth': 125.0,       # kHz - same as node
    'spreading_factor': 10,   # SF10 - same as node (LORA_SPREADING_FACTOR)
    'coding_rate': 5,         # 4/5 - same as node
    'sync_word': 0x12,        # Private network - same as node (MUST MATCH!)
    'tx_power': 14,           # dBm
}

# RFM95W GPIO Pins (BCM numbering)
LORA_NSS = 8      # CE0 - Chip Select
LORA_RST = 22     # Reset
LORA_DIO0 = 25    # Interrupt on RX done

# RFM95W Registers
REG_FIFO = 0x00
REG_OP_MODE = 0x01
REG_FRF_MSB = 0x06
REG_FRF_MID = 0x07
REG_FRF_LSB = 0x08
REG_PA_CONFIG = 0x09
REG_FIFO_ADDR_PTR = 0x0D
REG_FIFO_RX_BASE_ADDR = 0x0F
REG_IRQ_FLAGS = 0x12
REG_RX_NB_BYTES = 0x13
REG_MODEM_CONFIG_1 = 0x1D
REG_MODEM_CONFIG_2 = 0x1E
REG_PAYLOAD_LENGTH = 0x22
REG_MODEM_CONFIG_3 = 0x26
REG_SYNC_WORD = 0x39
REG_DIO_MAPPING_1 = 0x40
REG_VERSION = 0x42

# Operating modes
MODE_SLEEP = 0x00
MODE_STDBY = 0x01
MODE_TX = 0x03
MODE_RX_CONTINUOUS = 0x05
MODE_LORA = 0x80

# Multi-packet protocol constants (MUST MATCH NODE!)
PKT_TYPE_JSON = 0x01
PKT_TYPE_SPEC_START = 0x10
PKT_TYPE_SPEC_DATA = 0x11
PKT_TYPE_SPEC_END = 0x12

# Message queue for received packets
message_queue = Queue()

# Spectrogram assembly storage
# Key: (node_hash, session_id) -> {'start_time': ..., 'data': bytearray, 'metadata': ..., 'packets': set()}
spectrogram_sessions = {}
SPECTROGRAM_TIMEOUT = 30  # seconds

# Statistics
stats = {
    'packets_received': 0,
    'alerts_received': 0,
    'heartbeats_received': 0,
    'spectrograms_received': 0,
    'last_packet_time': None,
    'connected_nodes': set(),
    'rssi_last': 0,
    'snr_last': 0,
    'crc_errors': 0,
    'start_time': datetime.now(),
}


class LoRaReceiver:
    """RFM95W LoRa receiver for Raspberry Pi"""
    
    def __init__(self):
        self.spi = None
        self.running = False
        self.thread = None
        
        if HARDWARE_ENABLED:
            self._init_hardware()
    
    def _init_hardware(self):
        """Initialize SPI and GPIO"""
        try:
            # Setup GPIO
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            GPIO.setup(LORA_NSS, GPIO.OUT, initial=GPIO.HIGH)
            GPIO.setup(LORA_RST, GPIO.OUT, initial=GPIO.HIGH)
            GPIO.setup(LORA_DIO0, GPIO.IN)
            
            # Setup SPI
            self.spi = spidev.SpiDev()
            self.spi.open(0, 0)
            self.spi.max_speed_hz = 5000000
            self.spi.mode = 0
            
            # Reset module
            self._reset()
            
            # Verify chip
            version = self._read_register(REG_VERSION)
            if version != 0x12:
                logging.error(f"RFM95W not found! Version: {hex(version)}")
                return False
            
            logging.info("RFM95W detected, initializing...")
            
            # Configure for LoRa mode
            self._configure_lora()
            
            logging.info("LoRa receiver initialized successfully!")
            return True
            
        except Exception as e:
            logging.error(f"Failed to initialize LoRa hardware: {e}")
            return False
    
    def _reset(self):
        """Hardware reset"""
        GPIO.output(LORA_RST, GPIO.LOW)
        time.sleep(0.01)
        GPIO.output(LORA_RST, GPIO.HIGH)
        time.sleep(0.01)
    
    def _write_register(self, reg, value):
        """Write to RFM95W register"""
        GPIO.output(LORA_NSS, GPIO.LOW)
        self.spi.xfer2([reg | 0x80, value])
        GPIO.output(LORA_NSS, GPIO.HIGH)
    
    def _read_register(self, reg):
        """Read from RFM95W register"""
        GPIO.output(LORA_NSS, GPIO.LOW)
        result = self.spi.xfer2([reg & 0x7F, 0x00])
        GPIO.output(LORA_NSS, GPIO.HIGH)
        return result[1]
    
    def _configure_lora(self):
        """Configure LoRa parameters to match nodes"""
        # Sleep mode to change settings
        self._write_register(REG_OP_MODE, MODE_SLEEP)
        time.sleep(0.01)
        
        # LoRa mode
        self._write_register(REG_OP_MODE, MODE_LORA | MODE_SLEEP)
        time.sleep(0.01)
        
        # Set frequency (915 MHz)
        freq = int(LORA_CONFIG['frequency'] * 1000000)
        frf = int(freq / 61.035)
        self._write_register(REG_FRF_MSB, (frf >> 16) & 0xFF)
        self._write_register(REG_FRF_MID, (frf >> 8) & 0xFF)
        self._write_register(REG_FRF_LSB, frf & 0xFF)
        
        # Modem config 1: bandwidth + coding rate
        # BW=125kHz (0111), CR=4/5 (001), implicit header=0
        bw_cr = 0x72  # 125kHz, 4/5
        self._write_register(REG_MODEM_CONFIG_1, bw_cr)
        
        # Modem config 2: spreading factor + CRC
        # SF10 (1010), CRC on (1)
        sf = LORA_CONFIG['spreading_factor']
        self._write_register(REG_MODEM_CONFIG_2, (sf << 4) | 0x04)
        
        # Modem config 3: AGC auto on
        self._write_register(REG_MODEM_CONFIG_3, 0x04)
        
        # Sync word (must match nodes!)
        self._write_register(REG_SYNC_WORD, LORA_CONFIG['sync_word'])
        
        # TX power
        self._write_register(REG_PA_CONFIG, 0x8F)  # PA_BOOST, max power
        
        # FIFO pointers
        self._write_register(REG_FIFO_RX_BASE_ADDR, 0x00)
        
        # DIO0 = RX done interrupt
        self._write_register(REG_DIO_MAPPING_1, 0x00)
        
        # Standby mode
        self._write_register(REG_OP_MODE, MODE_LORA | MODE_STDBY)
        
        logging.info(f"LoRa configured: {LORA_CONFIG['frequency']}MHz, SF{sf}, 125kHz")
    
    def _start_receive(self):
        """Start continuous receive mode"""
        # Clear IRQ flags
        self._write_register(REG_IRQ_FLAGS, 0xFF)
        # FIFO pointer to RX base
        self._write_register(REG_FIFO_ADDR_PTR, 0x00)
        # RX continuous mode
        self._write_register(REG_OP_MODE, MODE_LORA | MODE_RX_CONTINUOUS)
    
    def _read_packet(self):
        """Read received packet from FIFO"""
        # Check IRQ flags
        irq = self._read_register(REG_IRQ_FLAGS)
        
        # RX done (bit 6)?
        if not (irq & 0x40):
            return None
        
        # CRC error?
        if irq & 0x20:
            logging.warning("CRC error in received packet")
            self._write_register(REG_IRQ_FLAGS, 0xFF)
            return None
        
        # Read packet length
        length = self._read_register(REG_RX_NB_BYTES)
        
        # Set FIFO address to last packet
        current_addr = self._read_register(0x10)  # FIFO_RX_CURRENT_ADDR
        self._write_register(REG_FIFO_ADDR_PTR, current_addr)
        
        # Read packet
        packet = []
        for _ in range(length):
            packet.append(self._read_register(REG_FIFO))
        
        # Get RSSI
        rssi = self._read_register(0x1A) - 137  # REG_PKT_RSSI_VALUE
        
        # Clear IRQ flags
        self._write_register(REG_IRQ_FLAGS, 0xFF)
        
        return bytes(packet), rssi
    
    def receive_loop(self):
        """Main receive loop (runs in thread)"""
        logging.info("LoRa receive loop started")
        
        if HARDWARE_ENABLED and self.spi:
            self._start_receive()
        
        while self.running:
            try:
                if HARDWARE_ENABLED and self.spi:
                    # Check for received packet
                    result = self._read_packet()
                    if result:
                        packet, rssi = result
                        self._process_packet(packet, rssi)
                else:
                    # Simulation mode - generate test packets
                    time.sleep(30)  # Simulate occasional packets
                    self._generate_test_packet()
                
                time.sleep(0.01)  # Small delay to prevent CPU spinning
                
            except Exception as e:
                logging.error(f"Error in receive loop: {e}")
                time.sleep(1)
        
        logging.info("LoRa receive loop stopped")
    
    def _process_packet(self, packet, rssi):
        """Process received LoRa packet"""
        try:
            timestamp = datetime.now()
            stats['packets_received'] += 1
            stats['last_packet_time'] = timestamp
            stats['rssi_last'] = rssi
            
            # Check if it's a multi-packet spectrogram (starts with 'FG' magic)
            if len(packet) >= 8 and packet[0] == 0x46 and packet[1] == 0x47:
                self._process_spectrogram_packet(packet, rssi, timestamp)
                return
            
            # Otherwise, try to parse as JSON
            data = packet.decode('utf-8')
            message = json.loads(data)
            
            logging.info(f"[LoRa RX] RSSI: {rssi} dBm")
            logging.info(f"  Node: {message.get('node_id', 'Unknown')}")
            logging.info(f"  Type: {message.get('type', 'Unknown')}")
            
            stats['connected_nodes'].add(message.get('node_id', 'Unknown'))
            
            if message.get('type') == 'alert':
                stats['alerts_received'] += 1
                logging.info(f"  🚨 ALERT! Confidence: {message.get('confidence')}%")
            elif message.get('type') == 'heartbeat':
                stats['heartbeats_received'] += 1
            
            # Add to queue for database/web processing
            message_queue.put({
                'data': message,
                'rssi': rssi,
                'timestamp': timestamp.isoformat()
            })
            
        except json.JSONDecodeError:
            logging.warning(f"Non-JSON packet received: {packet[:50]}...")
        except Exception as e:
            logging.error(f"Error processing packet: {e}")
    
    def _process_spectrogram_packet(self, packet, rssi, timestamp):
        """Process multi-packet spectrogram transmission"""
        try:
            # Parse header
            node_hash = (packet[2] << 8) | packet[3]
            pkt_type = packet[4]
            session_id = (packet[5] << 8) | packet[6]
            
            session_key = (node_hash, session_id)
            
            if pkt_type == PKT_TYPE_SPEC_START:
                # Start of new spectrogram
                expected_packets = packet[7]
                total_size = (packet[8] << 8) | packet[9]
                
                # Extract node_id (null-terminated string starting at byte 10)
                node_id_bytes = packet[10:]
                null_idx = node_id_bytes.find(0)
                if null_idx > 0:
                    node_id = node_id_bytes[:null_idx].decode('utf-8')
                else:
                    node_id = node_id_bytes.decode('utf-8', errors='ignore').strip('\x00')
                
                spectrogram_sessions[session_key] = {
                    'start_time': timestamp,
                    'node_id': node_id,
                    'expected_packets': expected_packets,
                    'total_size': total_size,
                    'data': bytearray(),
                    'packets_received': set(),
                    'metadata': None,
                    'rssi': rssi
                }
                
                logging.info(f"[Spec] START session {session_id} from {node_id}: expecting {expected_packets} packets, {total_size} bytes")
                stats['connected_nodes'].add(node_id)
                
            elif pkt_type == PKT_TYPE_SPEC_DATA:
                # Data chunk
                seq = packet[7]
                data = packet[8:]
                
                if session_key in spectrogram_sessions:
                    session = spectrogram_sessions[session_key]
                    if seq not in session['packets_received']:
                        session['data'].extend(data)
                        session['packets_received'].add(seq)
                        logging.info(f"[Spec] DATA packet {seq + 1}/{session['expected_packets']} received ({len(data)} bytes)")
                else:
                    logging.warning(f"[Spec] DATA packet for unknown session {session_id}")
                
            elif pkt_type == PKT_TYPE_SPEC_END:
                # End of transmission with metadata
                packets_sent = packet[7]
                metadata_json = packet[8:].decode('utf-8', errors='ignore').strip('\x00')
                
                if session_key in spectrogram_sessions:
                    session = spectrogram_sessions[session_key]
                    
                    try:
                        session['metadata'] = json.loads(metadata_json)
                    except:
                        session['metadata'] = {'conf': 0, 'lat': 0, 'lon': 0, 'bat': 100}
                    
                    # Complete - assemble and queue
                    received = len(session['packets_received'])
                    expected = session['expected_packets']
                    
                    logging.info(f"[Spec] END session {session_id}: {received}/{expected} packets received")
                    
                    if received >= expected * 0.8:  # Allow 20% packet loss
                        self._complete_spectrogram(session_key, rssi, timestamp)
                    else:
                        logging.warning(f"[Spec] Too many packets lost ({expected - received}), discarding")
                    
                    # Clean up session
                    del spectrogram_sessions[session_key]
                    stats['spectrograms_received'] += 1
                else:
                    logging.warning(f"[Spec] END packet for unknown session {session_id}")
            
            # Clean up old sessions
            self._cleanup_old_sessions()
            
        except Exception as e:
            logging.error(f"Error processing spectrogram packet: {e}")
            import traceback
            traceback.print_exc()
    
    def _complete_spectrogram(self, session_key, rssi, timestamp):
        """Complete spectrogram assembly and queue for Azure AI analysis"""
        session = spectrogram_sessions[session_key]
        
        # Decompress spectrogram data
        spec_data = self._decompress_spectrogram(bytes(session['data']))
        
        if spec_data is None:
            logging.warning("[Spec] Failed to decompress spectrogram")
            return
        
        # Save spectrogram to file
        spec_dir = os.path.join(os.path.dirname(__file__), 'static', 'spectrograms')
        os.makedirs(spec_dir, exist_ok=True)
        
        filename = f"{session['node_id']}_{timestamp.strftime('%Y%m%d_%H%M%S')}.png"
        filepath = os.path.join(spec_dir, filename)
        
        # Save as PNG using simple PGM format (can upgrade to PNG with PIL)
        self._save_spectrogram_image(spec_data, filepath)
        
        # Queue for Azure AI analysis
        metadata = session['metadata'] or {}
        message = {
            'node_id': session['node_id'],
            'type': 'spectrogram',
            'spectrogram_file': filename,
            'spectrogram_data': base64.b64encode(spec_data).decode('ascii'),
            'confidence': metadata.get('conf', 0),
            'lat': metadata.get('lat', 0),
            'lon': metadata.get('lon', 0),
            'battery': metadata.get('bat', 100),
            'timestamp': timestamp.isoformat(),
        }
        
        message_queue.put({
            'data': message,
            'rssi': rssi,
            'timestamp': timestamp.isoformat()
        })
        
        logging.info(f"[Spec] Complete spectrogram from {session['node_id']} saved to {filename}")
        stats['alerts_received'] += 1
    
    def _decompress_spectrogram(self, compressed):
        """Decompress spectrogram data (RLE + 4-bit quantization)"""
        try:
            # Check header
            if len(compressed) < 4 or compressed[0] != 0x53 or compressed[1] != 0x50:
                logging.warning("[Spec] Invalid spectrogram header")
                return None
            
            width = compressed[2]
            height = compressed[3]
            
            # Decode RLE
            quantized = bytearray()
            idx = 4
            while idx < len(compressed):
                byte = compressed[idx]
                idx += 1
                
                if byte & 0x80:  # Raw byte
                    quantized.append(byte & 0x7F)
                else:  # RLE run
                    if idx < len(compressed):
                        run_len = byte
                        value = compressed[idx]
                        idx += 1
                        quantized.extend([value] * run_len)
            
            # Unpack 4-bit quantized data to 8-bit
            spec_data = bytearray()
            for byte in quantized:
                high = ((byte >> 4) & 0x0F) * 17  # Scale 0-15 to 0-255
                low = (byte & 0x0F) * 17
                spec_data.append(high)
                spec_data.append(low)
            
            # Ensure correct size (64x64 = 4096)
            expected_size = width * height
            if len(spec_data) < expected_size:
                spec_data.extend([0] * (expected_size - len(spec_data)))
            elif len(spec_data) > expected_size:
                spec_data = spec_data[:expected_size]
            
            return bytes(spec_data)
            
        except Exception as e:
            logging.error(f"Spectrogram decompression error: {e}")
            return None
    
    def _save_spectrogram_image(self, spec_data, filepath):
        """Save spectrogram as image file"""
        try:
            # Try to use PIL if available for PNG
            from PIL import Image
            import numpy as np
            
            width = height = 64
            img_array = np.frombuffer(spec_data, dtype=np.uint8).reshape((height, width))
            img = Image.fromarray(img_array, mode='L')
            img.save(filepath)
            logging.info(f"[Spec] Saved PNG image: {filepath}")
            
        except ImportError:
            # Fallback to PGM format (portable graymap)
            filepath = filepath.replace('.png', '.pgm')
            with open(filepath, 'wb') as f:
                f.write(f"P5\n64 64\n255\n".encode())
                f.write(spec_data)
            logging.info(f"[Spec] Saved PGM image (PIL not available): {filepath}")
    
    def _cleanup_old_sessions(self):
        """Remove timed-out spectrogram sessions"""
        now = datetime.now()
        expired = []
        
        for key, session in spectrogram_sessions.items():
            age = (now - session['start_time']).total_seconds()
            if age > SPECTROGRAM_TIMEOUT:
                expired.append(key)
                logging.warning(f"[Spec] Session {key} timed out after {age:.1f}s")
        
        for key in expired:
            del spectrogram_sessions[key]
    
    def _generate_test_packet(self):
        """Generate test packet for simulation mode"""
        import random
        
        test_message = {
            'node_id': f'GUARDIAN_{random.randint(1,3):03d}',
            'type': random.choice(['heartbeat', 'heartbeat', 'heartbeat', 'alert']),
            'confidence': random.randint(60, 95),
            'lat': 43.65 + random.uniform(-0.1, 0.1),
            'lon': -79.38 + random.uniform(-0.1, 0.1),
            'battery': random.randint(50, 100),
            'timestamp': int(time.time()),
        }
        
        self._process_packet(
            json.dumps(test_message).encode(),
            random.randint(-120, -60)
        )
    
    def start(self):
        """Start receiver thread"""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self.receive_loop, daemon=True)
        self.thread.start()
        logging.info("LoRa receiver started")
    
    def stop(self):
        """Stop receiver thread"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
        
        if HARDWARE_ENABLED:
            if self.spi:
                self.spi.close()
            GPIO.cleanup()
        
        logging.info("LoRa receiver stopped")
    
    def get_stats(self):
        """Get receiver statistics"""
        uptime = (datetime.now() - stats['start_time']).total_seconds()
        return {
            'packets_received': stats['packets_received'],
            'alerts_received': stats['alerts_received'],
            'heartbeats_received': stats['heartbeats_received'],
            'spectrograms_received': stats['spectrograms_received'],
            'last_packet_time': stats['last_packet_time'].isoformat() if stats['last_packet_time'] else None,
            'connected_nodes': list(stats['connected_nodes']),
            'rssi_last': stats['rssi_last'],
            'snr_last': stats.get('snr_last', 0),
            'crc_errors': stats.get('crc_errors', 0),
            'uptime': int(uptime),
            'hardware_enabled': HARDWARE_ENABLED,
            'pending_spectrograms': len(spectrogram_sessions),
        }


# Global receiver instance
receiver = None


def init_receiver():
    """Initialize global receiver"""
    global receiver
    receiver = LoRaReceiver()
    return receiver


def get_receiver():
    """Get global receiver instance"""
    global receiver
    if receiver is None:
        receiver = LoRaReceiver()
    return receiver


def get_message_queue():
    """Get message queue"""
    return message_queue


# Test mode
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    print("=" * 50)
    print("Forest Guardian - LoRa Receiver Test")
    print("=" * 50)
    
    rx = LoRaReceiver()
    rx.start()
    
    try:
        while True:
            # Check for messages
            while not message_queue.empty():
                msg = message_queue.get()
                print(f"\nReceived: {json.dumps(msg, indent=2)}")
            
            # Print stats every 10 seconds
            time.sleep(10)
            print(f"\nStats: {rx.get_stats()}")
            
    except KeyboardInterrupt:
        print("\nShutting down...")
        rx.stop()
