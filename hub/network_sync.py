# network_sync.py - Forest Guardian Hub
# Network monitoring and Azure sync when connectivity available
# Queues detections offline and syncs when network returns

import os
import logging
import sqlite3
import json
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional
import socket
import requests

logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURATION
# =============================================================================
SYNC_DB_PATH = Path(__file__).parent / 'data' / 'sync_queue.db'
NETWORK_CHECK_INTERVAL = 30  # seconds between network checks
SYNC_BATCH_SIZE = 10  # Max items to sync at once
AZURE_TIMEOUT = 10  # seconds

# Test URLs for network connectivity
CONNECTIVITY_URLS = [
    ("8.8.8.8", 53),  # Google DNS
    ("1.1.1.1", 53),  # Cloudflare DNS
]

# =============================================================================
# DATABASE SETUP
# =============================================================================
def init_sync_db():
    """Initialize the sync queue database"""
    SYNC_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(str(SYNC_DB_PATH))
    c = conn.cursor()
    
    # Detection queue table
    c.execute('''
        CREATE TABLE IF NOT EXISTS detection_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            node_id TEXT NOT NULL,
            detection_type TEXT NOT NULL,
            local_confidence INTEGER,
            local_classification TEXT,
            spectrogram_path TEXT,
            spectrogram_base64 TEXT,
            latitude REAL,
            longitude REAL,
            battery_level INTEGER,
            metadata TEXT,
            sync_status TEXT DEFAULT 'pending',
            azure_result TEXT,
            synced_at TIMESTAMP,
            retry_count INTEGER DEFAULT 0
        )
    ''')
    
    # Network status log
    c.execute('''
        CREATE TABLE IF NOT EXISTS network_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_online BOOLEAN,
            latency_ms REAL
        )
    ''')
    
    # Sync history
    c.execute('''
        CREATE TABLE IF NOT EXISTS sync_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            items_synced INTEGER,
            items_failed INTEGER,
            duration_ms REAL
        )
    ''')
    
    conn.commit()
    conn.close()
    logger.info(f"Sync database initialized at {SYNC_DB_PATH}")


# =============================================================================
# NETWORK STATUS
# =============================================================================
_is_online = False
_last_check = None
_check_lock = threading.Lock()

def check_network_connectivity() -> bool:
    """
    Check if internet connectivity is available
    
    Returns:
        True if online, False otherwise
    """
    global _is_online, _last_check
    
    for host, port in CONNECTIVITY_URLS:
        try:
            socket.setdefaulttimeout(3)
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((host, port))
            s.close()
            
            with _check_lock:
                _is_online = True
                _last_check = datetime.now()
            
            return True
        except (socket.error, socket.timeout):
            continue
    
    with _check_lock:
        _is_online = False
        _last_check = datetime.now()
    
    return False


def check_azure_connectivity() -> Dict[str, Any]:
    """
    Check if Azure services are reachable
    
    Returns:
        Dictionary with connectivity status for each service
    """
    from config import Config
    
    result = {
        "internet": check_network_connectivity(),
        "azure_openai": False,
        "azure_custom_vision": False,
        "latency_ms": None
    }
    
    if not result["internet"]:
        return result
    
    start_time = time.time()
    
    # Check Azure OpenAI
    if Config.AZURE_OPENAI_ENDPOINT:
        try:
            response = requests.head(
                Config.AZURE_OPENAI_ENDPOINT,
                timeout=AZURE_TIMEOUT
            )
            result["azure_openai"] = response.status_code < 500
        except:
            pass
    
    # Check Azure Custom Vision
    if Config.AZURE_CUSTOM_VISION_ENDPOINT:
        try:
            response = requests.head(
                Config.AZURE_CUSTOM_VISION_ENDPOINT,
                timeout=AZURE_TIMEOUT
            )
            result["azure_custom_vision"] = response.status_code < 500
        except:
            pass
    
    result["latency_ms"] = round((time.time() - start_time) * 1000, 2)
    
    # Log network status
    try:
        conn = sqlite3.connect(str(SYNC_DB_PATH))
        c = conn.cursor()
        c.execute(
            'INSERT INTO network_log (is_online, latency_ms) VALUES (?, ?)',
            (result["internet"], result["latency_ms"])
        )
        conn.commit()
        conn.close()
    except:
        pass
    
    return result


def is_online() -> bool:
    """Get current online status (cached)"""
    global _is_online, _last_check
    
    with _check_lock:
        # Recheck if cache is stale
        if _last_check is None or (datetime.now() - _last_check).seconds > 60:
            return check_network_connectivity()
        return _is_online


def get_network_status() -> Dict[str, Any]:
    """Get detailed network status for dashboard"""
    global _is_online, _last_check
    
    return {
        "is_online": _is_online,
        "last_check": _last_check.isoformat() if _last_check else None,
        "check_interval": NETWORK_CHECK_INTERVAL
    }


# =============================================================================
# DETECTION QUEUE
# =============================================================================
def queue_detection(
    node_id: str,
    detection_type: str,
    local_confidence: int,
    local_classification: str,
    spectrogram_path: Optional[str] = None,
    spectrogram_base64: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    battery_level: Optional[int] = None,
    metadata: Optional[Dict] = None
) -> int:
    """
    Queue a detection for Azure sync when online
    
    Args:
        node_id: Device/node identifier
        detection_type: Type of detection (chainsaw, vehicle, etc)
        local_confidence: Confidence from local inference (0-100)
        local_classification: Classification from local model
        spectrogram_path: Path to spectrogram image file
        spectrogram_base64: Base64-encoded spectrogram (alternative to path)
        latitude: GPS latitude
        longitude: GPS longitude
        battery_level: Battery percentage
        metadata: Additional metadata dict
    
    Returns:
        Queue item ID
    """
    init_sync_db()
    
    conn = sqlite3.connect(str(SYNC_DB_PATH))
    c = conn.cursor()
    
    c.execute('''
        INSERT INTO detection_queue 
        (node_id, detection_type, local_confidence, local_classification,
         spectrogram_path, spectrogram_base64, latitude, longitude,
         battery_level, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        node_id, detection_type, local_confidence, local_classification,
        spectrogram_path, spectrogram_base64, latitude, longitude,
        battery_level, json.dumps(metadata) if metadata else None
    ))
    
    item_id = c.lastrowid
    conn.commit()
    conn.close()
    
    logger.info(f"Queued detection #{item_id}: {detection_type} from {node_id} ({local_confidence}%)")
    
    return item_id


def get_pending_queue() -> List[Dict[str, Any]]:
    """Get all pending items in the sync queue"""
    init_sync_db()
    
    conn = sqlite3.connect(str(SYNC_DB_PATH))
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute('''
        SELECT * FROM detection_queue 
        WHERE sync_status = 'pending'
        ORDER BY created_at ASC
        LIMIT ?
    ''', (SYNC_BATCH_SIZE,))
    
    items = [dict(row) for row in c.fetchall()]
    conn.close()
    
    return items


def get_queue_stats() -> Dict[str, Any]:
    """Get queue statistics for dashboard"""
    init_sync_db()
    
    conn = sqlite3.connect(str(SYNC_DB_PATH))
    c = conn.cursor()
    
    # Count by status
    c.execute('''
        SELECT sync_status, COUNT(*) as count
        FROM detection_queue
        GROUP BY sync_status
    ''')
    status_counts = dict(c.fetchall())
    
    # Recent sync history
    c.execute('''
        SELECT * FROM sync_history
        ORDER BY timestamp DESC
        LIMIT 5
    ''')
    recent_syncs = c.fetchall()
    
    # Oldest pending item
    c.execute('''
        SELECT created_at FROM detection_queue
        WHERE sync_status = 'pending'
        ORDER BY created_at ASC
        LIMIT 1
    ''')
    oldest = c.fetchone()
    
    conn.close()
    
    return {
        "pending": status_counts.get('pending', 0),
        "synced": status_counts.get('synced', 0),
        "failed": status_counts.get('failed', 0),
        "oldest_pending": oldest[0] if oldest else None,
        "recent_syncs": recent_syncs
    }


def mark_item_synced(item_id: int, azure_result: Dict[str, Any]):
    """Mark a queue item as synced"""
    conn = sqlite3.connect(str(SYNC_DB_PATH))
    c = conn.cursor()
    
    c.execute('''
        UPDATE detection_queue
        SET sync_status = 'synced',
            azure_result = ?,
            synced_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (json.dumps(azure_result), item_id))
    
    conn.commit()
    conn.close()


def mark_item_failed(item_id: int, error: str):
    """Mark a queue item as failed"""
    conn = sqlite3.connect(str(SYNC_DB_PATH))
    c = conn.cursor()
    
    c.execute('''
        UPDATE detection_queue
        SET sync_status = CASE WHEN retry_count >= 3 THEN 'failed' ELSE 'pending' END,
            retry_count = retry_count + 1,
            metadata = json_set(COALESCE(metadata, '{}'), '$.last_error', ?)
        WHERE id = ?
    ''', (error, item_id))
    
    conn.commit()
    conn.close()


# =============================================================================
# SYNC SERVICE
# =============================================================================
def sync_pending_detections() -> Dict[str, Any]:
    """
    Sync pending detections to Azure
    
    Returns:
        Dictionary with sync results
    """
    from ai_service import analyze_with_custom_vision, analyze_spectrogram
    
    result = {
        "success": True,
        "items_processed": 0,
        "items_synced": 0,
        "items_failed": 0,
        "errors": []
    }
    
    # Check connectivity first
    if not check_network_connectivity():
        result["success"] = False
        result["errors"].append("No network connectivity")
        return result
    
    start_time = time.time()
    pending = get_pending_queue()
    
    logger.info(f"Syncing {len(pending)} pending detections...")
    
    for item in pending:
        result["items_processed"] += 1
        
        try:
            # Determine which image source to use
            image_source = item.get('spectrogram_path') or item.get('spectrogram_base64')
            
            if not image_source:
                mark_item_failed(item['id'], "No spectrogram data")
                result["items_failed"] += 1
                continue
            
            # Use the main analyze_spectrogram function with cloud mode
            azure_result = None
            if item.get('spectrogram_path') and os.path.exists(item['spectrogram_path']):
                # Use Custom Vision for sync (faster, cheaper)
                azure_result = analyze_with_custom_vision(item['spectrogram_path'])
            
            # If Custom Vision fails, use the full analyze_spectrogram with auto mode
            if not azure_result or not azure_result.get('success'):
                if item.get('spectrogram_path') and os.path.exists(item['spectrogram_path']):
                    # Use main analyze function which will route appropriately
                    azure_result = analyze_spectrogram(
                        item['spectrogram_path'],
                        node_id=item.get('node_id', ''),
                        location=(item.get('latitude') or 0, item.get('longitude') or 0)
                    )
            
            if azure_result and azure_result.get('success'):
                mark_item_synced(item['id'], azure_result)
                result["items_synced"] += 1
                logger.info(f"Synced detection #{item['id']}: Azure says {azure_result.get('classification')}")
            else:
                error = azure_result.get('error', 'Unknown error') if azure_result else 'No result'
                mark_item_failed(item['id'], error)
                result["items_failed"] += 1
                result["errors"].append(f"Item {item['id']}: {error}")
                
        except Exception as e:
            mark_item_failed(item['id'], str(e))
            result["items_failed"] += 1
            result["errors"].append(f"Item {item['id']}: {str(e)}")
    
    duration = (time.time() - start_time) * 1000
    
    # Log sync history
    try:
        conn = sqlite3.connect(str(SYNC_DB_PATH))
        c = conn.cursor()
        c.execute('''
            INSERT INTO sync_history (items_synced, items_failed, duration_ms)
            VALUES (?, ?, ?)
        ''', (result["items_synced"], result["items_failed"], duration))
        conn.commit()
        conn.close()
    except:
        pass
    
    result["duration_ms"] = round(duration, 2)
    logger.info(f"Sync complete: {result['items_synced']} synced, {result['items_failed']} failed in {duration:.0f}ms")
    
    return result


# =============================================================================
# BACKGROUND SYNC THREAD
# =============================================================================
_sync_thread = None
_sync_running = False

def start_background_sync():
    """Start the background sync thread"""
    global _sync_thread, _sync_running
    
    if _sync_thread is not None and _sync_thread.is_alive():
        logger.warning("Background sync already running")
        return
    
    _sync_running = True
    _sync_thread = threading.Thread(target=_background_sync_loop, daemon=True)
    _sync_thread.start()
    logger.info("Background sync thread started")


def stop_background_sync():
    """Stop the background sync thread"""
    global _sync_running
    _sync_running = False
    logger.info("Background sync stopping...")


def _background_sync_loop():
    """Background thread that periodically checks network and syncs"""
    global _sync_running
    
    while _sync_running:
        try:
            # Check network status
            is_connected = check_network_connectivity()
            
            if is_connected:
                # Get queue stats
                stats = get_queue_stats()
                
                if stats['pending'] > 0:
                    logger.info(f"Network online, {stats['pending']} items pending sync")
                    sync_pending_detections()
            else:
                logger.debug("Network offline, skipping sync")
            
        except Exception as e:
            logger.error(f"Background sync error: {e}")
        
        # Wait before next check
        time.sleep(NETWORK_CHECK_INTERVAL)


# =============================================================================
# INITIALIZATION
# =============================================================================
# Initialize database on import
init_sync_db()


# =============================================================================
# TESTING
# =============================================================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("=== Network Sync Test ===")
    
    # Test network check
    print(f"\nNetwork connectivity: {check_network_connectivity()}")
    print(f"Azure connectivity: {check_azure_connectivity()}")
    
    # Test queue
    print(f"\nQueue stats: {get_queue_stats()}")
    
    # Test queueing a detection
    item_id = queue_detection(
        node_id="TEST_001",
        detection_type="chainsaw",
        local_confidence=75,
        local_classification="chainsaw",
        latitude=49.2827,
        longitude=-123.1207,
        battery_level=85,
        metadata={"test": True}
    )
    print(f"Queued test detection: #{item_id}")
    
    # Show updated stats
    print(f"Updated queue stats: {get_queue_stats()}")
