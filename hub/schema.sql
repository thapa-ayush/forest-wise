-- schema.sql for Forest Guardian Hub
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT,
    phone TEXT,
    role TEXT DEFAULT 'Ranger',
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

CREATE TABLE IF NOT EXISTS nodes (
    node_id TEXT PRIMARY KEY,
    last_seen TIMESTAMP,
    battery INTEGER,
    lat REAL,
    lon REAL,
    status TEXT DEFAULT 'active',
    rssi INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_id TEXT,
    confidence INTEGER,
    lat REAL,
    lon REAL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ai_analysis TEXT,
    responded INTEGER DEFAULT 0,
    responded_by INTEGER,
    responded_at TIMESTAMP,
    rssi INTEGER DEFAULT 0,
    spectrogram_id INTEGER,
    FOREIGN KEY (spectrogram_id) REFERENCES spectrograms(id)
);

-- Spectrograms table for Azure AI Vision analysis
CREATE TABLE IF NOT EXISTS spectrograms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_id TEXT NOT NULL,
    image_path TEXT NOT NULL,
    lat REAL DEFAULT 0,
    lon REAL DEFAULT 0,
    anomaly_score REAL DEFAULT 0,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    rssi INTEGER DEFAULT 0,
    session_id TEXT,
    -- AI Analysis Results
    classification TEXT,        -- 'chainsaw', 'vehicle', 'natural', 'unknown'
    confidence INTEGER,         -- 0-100
    threat_level TEXT,          -- 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'NONE'
    ai_reasoning TEXT,          -- AI explanation
    features_detected TEXT,     -- JSON array of detected features
    service_used TEXT,          -- 'gpt4o', 'custom_vision', 'custom_vision+gpt4o'
    analyzed_at TIMESTAMP,
    -- Indexes
    FOREIGN KEY (node_id) REFERENCES nodes(node_id)
);

CREATE INDEX IF NOT EXISTS idx_spectrograms_node ON spectrograms(node_id);
CREATE INDEX IF NOT EXISTS idx_spectrograms_timestamp ON spectrograms(timestamp);
CREATE INDEX IF NOT EXISTS idx_spectrograms_classification ON spectrograms(classification);
CREATE INDEX IF NOT EXISTS idx_spectrograms_threat ON spectrograms(threat_level);

CREATE TABLE IF NOT EXISTS login_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    ip_address TEXT,
    success INTEGER,
    timestamp TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    action TEXT,
    details TEXT,
    ip_address TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
