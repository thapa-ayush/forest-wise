# app.py - Forest Guardian Hub
import os
import json
import time
import logging
import threading
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, g, session, send_from_directory
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from flask_login import login_required, current_user
from flask_wtf.csrf import CSRFProtect
from config import Config
from database import init_db, get_db, close_db, query_db, add_user
from auth import login_manager, limiter, auth_bp
from admin import admin_bp
from ai_service import (
    analyze_alert, 
    generate_daily_report, 
    generate_sms_text,
    analyze_spectrogram,
    generate_alert_notification,
    get_ai_mode,
    set_ai_mode
)

app = Flask(__name__)
app.config.from_object(Config)
CORS(app)
csrf = CSRFProtect(app)
csrf.exempt(auth_bp)  # Exempt auth routes from CSRF for simpler login
socketio = SocketIO(app, cors_allowed_origins="*")
login_manager.init_app(app)
limiter.init_app(app)
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)

logging.basicConfig(level=logging.INFO)

@app.teardown_appcontext
def teardown_db(exception):
    close_db()

# Initialize database on startup
with app.app_context():
    init_db()
    # Create admin user if not exists
    if not query_db('SELECT * FROM users WHERE username = ?', ['admin'], one=True):
        add_user('admin', 'admin@forestguardian.io', 'admin123', 'Admin', '', 'Admin')

# Dashboard
@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route('/map')
@login_required
def map_view():
    return render_template('map.html')

@app.route('/alerts')
@login_required
def alerts_view():
    alerts = query_db('SELECT * FROM alerts ORDER BY timestamp DESC LIMIT 100')
    return render_template('alerts.html', alerts=alerts)

@app.route('/nodes')
@login_required
def nodes_view():
    nodes = query_db('SELECT * FROM nodes')
    return render_template('nodes.html', nodes=nodes)

@app.route('/reports')
@login_required
def reports_view():
    return render_template('reports.html')

# API Endpoints
@app.route('/api/status')
def api_status():
    return jsonify({'status': 'ok', 'time': datetime.utcnow().isoformat()})

@app.route('/api/nodes')
@login_required
def api_nodes():
    nodes = query_db('SELECT * FROM nodes')
    return jsonify([dict(n) for n in nodes])

@app.route('/api/alerts')
@login_required
def api_alerts():
    alerts = query_db('SELECT * FROM alerts ORDER BY timestamp DESC LIMIT 100')
    return jsonify([dict(a) for a in alerts])

@app.route('/api/alerts/<int:alert_id>/respond', methods=['POST'])
@login_required
def api_respond_alert(alert_id):
    db = get_db()
    db.execute('UPDATE alerts SET responded = 1, responded_by = ?, responded_at = ? WHERE id = ?',
               [current_user.id, datetime.utcnow(), alert_id])
    db.commit()
    return jsonify({'success': True})

@app.route('/api/reports/daily')
@login_required
def api_daily_report():
    alerts = query_db('SELECT * FROM alerts WHERE timestamp > datetime("now", "-1 day")')
    report = generate_daily_report([dict(a) for a in alerts])
    return jsonify({'report': report})

@app.route('/api/reports/risk')
@login_required
def api_risk_prediction():
    # Placeholder for risk prediction
    return jsonify({'risk_areas': []})

@app.route('/api/lora/status')
@login_required
def api_lora_status():
    """Get LoRa receiver status and stats"""
    try:
        from lora_receiver import get_receiver
        rx = get_receiver()
        return jsonify({
            'status': 'running' if rx.running else 'stopped',
            'stats': rx.get_stats()
        })
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)})


# =============================================================================
# SPECTROGRAM API ENDPOINTS
# =============================================================================

@app.route('/api/spectrograms')
@login_required
def api_spectrograms():
    """Get list of recent spectrograms"""
    spectrograms = query_db('''
        SELECT * FROM spectrograms 
        ORDER BY timestamp DESC LIMIT 50
    ''')
    return jsonify([dict(s) for s in spectrograms] if spectrograms else [])


@app.route('/api/spectrograms/<int:spec_id>')
@login_required
def api_spectrogram_detail(spec_id):
    """Get spectrogram details including AI analysis"""
    spec = query_db('SELECT * FROM spectrograms WHERE id = ?', [spec_id], one=True)
    if spec:
        return jsonify(dict(spec))
    return jsonify({'error': 'Spectrogram not found'}), 404


@app.route('/api/spectrograms/<int:spec_id>/analyze', methods=['POST'])
@login_required
def api_analyze_spectrogram(spec_id):
    """Trigger AI analysis for a spectrogram"""
    spec = query_db('SELECT * FROM spectrograms WHERE id = ?', [spec_id], one=True)
    if not spec:
        return jsonify({'error': 'Spectrogram not found'}), 404
    
    # Run analysis
    result = analyze_spectrogram(
        spec['image_path'],
        node_id=spec['node_id'],
        location=(spec['lat'], spec['lon'])
    )
    
    # Update database with results
    if result.get('success'):
        db = get_db()
        db.execute('''
            UPDATE spectrograms 
            SET classification = ?, confidence = ?, threat_level = ?, 
                ai_reasoning = ?, service_used = ?, analyzed_at = ?
            WHERE id = ?
        ''', [
            result.get('classification'),
            result.get('confidence'),
            result.get('threat_level'),
            result.get('reasoning'),
            result.get('service_used', 'unknown'),
            datetime.utcnow(),
            spec_id
        ])
        db.commit()
        
        # Emit update to dashboard
        socketio.emit('spectrogram_analyzed', {
            'id': spec_id,
            'classification': result.get('classification'),
            'confidence': result.get('confidence'),
            'service_used': result.get('service_used'),
            'threat_level': result.get('threat_level')
        })
    
    return jsonify(result)


@app.route('/api/spectrograms/image/<path:filename>')
@login_required
def api_spectrogram_image(filename):
    """Serve spectrogram images"""
    spectrogram_dir = os.path.join(app.root_path, Config.SPECTROGRAM_DIR)
    return send_from_directory(spectrogram_dir, filename)


@app.route('/api/spectrograms/stats')
@login_required
def api_spectrogram_stats():
    """Get spectrogram analysis statistics"""
    stats = {}
    
    # Total spectrograms
    total = query_db('SELECT COUNT(*) as count FROM spectrograms', one=True)
    stats['total'] = total['count'] if total else 0
    
    # By classification
    classifications = query_db('''
        SELECT classification, COUNT(*) as count 
        FROM spectrograms 
        WHERE classification IS NOT NULL 
        GROUP BY classification
    ''')
    stats['by_classification'] = {c['classification']: c['count'] for c in classifications} if classifications else {}
    
    # By threat level
    threats = query_db('''
        SELECT threat_level, COUNT(*) as count 
        FROM spectrograms 
        WHERE threat_level IS NOT NULL 
        GROUP BY threat_level
    ''')
    stats['by_threat_level'] = {t['threat_level']: t['count'] for t in threats} if threats else {}
    
    # Last 24 hours
    recent = query_db('''
        SELECT COUNT(*) as count FROM spectrograms 
        WHERE timestamp > datetime("now", "-1 day")
    ''', one=True)
    stats['last_24h'] = recent['count'] if recent else 0
    
    # Chainsaw detections last 24h
    chainsaw = query_db('''
        SELECT COUNT(*) as count FROM spectrograms 
        WHERE classification = "chainsaw" 
        AND timestamp > datetime("now", "-1 day")
    ''', one=True)
    stats['chainsaw_24h'] = chainsaw['count'] if chainsaw else 0
    
    return jsonify(stats)


# =============================================================================
# AI MODE API ENDPOINTS
# =============================================================================

@app.route('/api/ai/mode')
@login_required
def api_get_ai_mode():
    """Get current AI analysis mode"""
    mode = get_ai_mode()
    return jsonify({
        'mode': mode,
        'description': {
            'gpt4o': 'Azure GPT-4o Vision - Detailed analysis with reasoning',
            'custom_vision': 'Azure Custom Vision - Fast classification',
            'auto': 'Auto - Custom Vision + GPT-4o verification for threats'
        }.get(mode, 'Unknown mode'),
        'available_modes': ['gpt4o', 'custom_vision', 'auto']
    })


@app.route('/api/ai/mode', methods=['POST'])
@login_required
def api_set_ai_mode():
    """Set AI analysis mode"""
    data = request.json or {}
    mode = data.get('mode', 'gpt4o')
    
    if set_ai_mode(mode):
        # Emit update to all connected clients
        socketio.emit('ai_mode_changed', {'mode': mode})
        logging.info(f"AI mode changed to: {mode} by user {current_user.username}")
        return jsonify({'success': True, 'mode': mode})
    else:
        return jsonify({
            'success': False, 
            'error': f"Invalid mode: {mode}. Valid modes: gpt4o, custom_vision, auto"
        }), 400


@app.route('/api/ai/status')
@login_required
def api_ai_status():
    """Get AI services status"""
    status = {
        'current_mode': get_ai_mode(),
        'services': {
            'gpt4o': {
                'configured': bool(Config.AZURE_OPENAI_KEY and Config.AZURE_OPENAI_ENDPOINT),
                'deployment': Config.AZURE_OPENAI_DEPLOYMENT
            },
            'custom_vision': {
                'configured': bool(Config.AZURE_CUSTOM_VISION_KEY and Config.AZURE_CUSTOM_VISION_ENDPOINT),
                'project_id': Config.AZURE_CUSTOM_VISION_PROJECT_ID[:8] + '...' if Config.AZURE_CUSTOM_VISION_PROJECT_ID else None,
                'iteration': Config.AZURE_CUSTOM_VISION_ITERATION
            }
        }
    }
    return jsonify(status)


@app.route('/api/simulate/alert', methods=['POST'])
@login_required
def api_simulate_alert():
    data = request.json or {}
    db = get_db()
    db.execute('INSERT INTO alerts (node_id, confidence, lat, lon, timestamp, ai_analysis) VALUES (?, ?, ?, ?, ?, ?)',
               [data.get('node_id', 'SIM_001'), data.get('confidence', 85), data.get('lat', 43.65), data.get('lon', -79.38), datetime.utcnow(), ''])
    db.commit()
    socketio.emit('new_alert', data)
    return jsonify({'success': True})

@app.route('/api/simulate/heartbeat', methods=['POST'])
@login_required
def api_simulate_heartbeat():
    data = request.json or {}
    db = get_db()
    db.execute('INSERT OR REPLACE INTO nodes (node_id, last_seen, battery, lat, lon, status) VALUES (?, ?, ?, ?, ?, ?)',
               [data.get('node_id', 'SIM_001'), datetime.utcnow(), data.get('battery', 80), data.get('lat', 43.65), data.get('lon', -79.38), 'active'])
    db.commit()
    socketio.emit('node_update', data)
    return jsonify({'success': True})

# SocketIO events
@socketio.on('connect')
def handle_connect():
    logging.info('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    logging.info('Client disconnected')


def process_lora_messages():
    """Background task to process LoRa messages and save to database"""
    from lora_receiver import get_message_queue, get_receiver
    
    logging.info("Starting LoRa message processor...")
    
    while True:
        try:
            queue = get_message_queue()
            
            # Process all pending messages
            while not queue.empty():
                msg = queue.get()
                data = msg['data']
                rssi = msg['rssi']
                timestamp = msg['timestamp']
                
                with app.app_context():
                    db = get_db()
                    
                    if data.get('type') == 'alert':
                        # Save alert to database
                        db.execute('''
                            INSERT INTO alerts (node_id, confidence, lat, lon, timestamp, rssi, ai_analysis)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        ''', [
                            data.get('node_id'),
                            data.get('confidence'),
                            data.get('lat', 0),
                            data.get('lon', 0),
                            timestamp,
                            rssi,
                            ''  # AI analysis will be added later
                        ])
                        db.commit()
                        
                        # Emit real-time alert to web dashboard
                        socketio.emit('new_alert', {
                            'node_id': data.get('node_id'),
                            'confidence': data.get('confidence'),
                            'lat': data.get('lat'),
                            'lon': data.get('lon'),
                            'timestamp': timestamp,
                            'rssi': rssi
                        })
                        
                        logging.info(f"🚨 Alert saved from {data.get('node_id')}")
                        
                    elif data.get('type') in ('heartbeat', 'boot'):
                        # Update node status (heartbeat or boot message)
                        db.execute('''
                            INSERT OR REPLACE INTO nodes 
                            (node_id, last_seen, battery, lat, lon, status, rssi)
                            VALUES (?, ?, ?, ?, ?, 'active', ?)
                        ''', [
                            data.get('node_id'),
                            timestamp,
                            data.get('battery', 100),
                            data.get('lat', 0),
                            data.get('lon', 0),
                            rssi
                        ])
                        db.commit()
                        
                        # Emit node update to web dashboard
                        socketio.emit('node_update', {
                            'node_id': data.get('node_id'),
                            'battery': data.get('battery', 100),
                            'lat': data.get('lat'),
                            'lon': data.get('lon'),
                            'timestamp': timestamp,
                            'rssi': rssi
                        })
                        
                        msg_type = '🚀 Boot' if data.get('type') == 'boot' else '💓 Heartbeat'
                        logging.info(f"{msg_type} from {data.get('node_id')}")
                    
                    elif data.get('type') == 'spectrogram':
                        # Process spectrogram message (already reassembled by lora_receiver)
                        process_spectrogram_message(db, data, rssi, timestamp)
            
            time.sleep(0.5)  # Check queue every 500ms
            
        except Exception as e:
            logging.error(f"Error processing LoRa messages: {e}")
            time.sleep(1)


def process_spectrogram_message(db, data, rssi, timestamp):
    """Process a reassembled spectrogram and optionally analyze with Azure AI"""
    node_id = data.get('node_id')
    # Handle both 'image_path' and 'spectrogram_file' field names
    image_filename = data.get('image_path') or data.get('spectrogram_file')
    lat = data.get('lat', 0)
    lon = data.get('lon', 0)
    anomaly_score = data.get('anomaly_score') or data.get('confidence', 0)
    session_id = data.get('session_id')
    
    # Ensure we have an image path
    if not image_filename:
        logging.error(f"No image_path in spectrogram data: {data.keys()}")
        return
    
    # Build full path for analysis (files are in static/spectrograms/)
    spectrogram_dir = os.path.join(os.path.dirname(__file__), 'static', 'spectrograms')
    image_path = os.path.join(spectrogram_dir, os.path.basename(image_filename))
    
    logging.info(f"📊 Processing spectrogram from {node_id} (session: {session_id}, file: {image_filename})")
    
    # Save spectrogram record to database
    cursor = db.execute('''
        INSERT INTO spectrograms 
        (node_id, image_path, lat, lon, anomaly_score, timestamp, rssi, session_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', [
        node_id,
        image_path,
        lat,
        lon,
        anomaly_score,
        timestamp,
        rssi,
        session_id
    ])
    db.commit()
    spec_id = cursor.lastrowid
    
    # Node only sends spectrograms when it detects potential chainsaw
    # Create an initial alert (will be confirmed/updated by AI)
    db.execute('''
        INSERT INTO alerts 
        (node_id, confidence, lat, lon, timestamp, rssi, ai_analysis, spectrogram_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', [
        node_id,
        anomaly_score,
        lat,
        lon,
        timestamp,
        rssi,
        "Pending AI verification",
        spec_id
    ])
    db.commit()
    logging.info(f"🚨 Alert created from spectrogram (pending AI verification)")
    
    # Emit to dashboard that new spectrogram received
    socketio.emit('new_spectrogram', {
        'id': spec_id,
        'node_id': node_id,
        'lat': lat,
        'lon': lon,
        'anomaly_score': anomaly_score,
        'image_path': image_path,
        'timestamp': timestamp
    })
    
    # Auto-analyze with Azure AI if enabled
    if Config.AUTO_ANALYZE_SPECTROGRAMS:
        try:
            result = analyze_spectrogram(
                image_path,
                node_id=node_id,
                location=(lat, lon)
            )
            
            if result.get('success'):
                # Update database with AI analysis
                db.execute('''
                    UPDATE spectrograms 
                    SET classification = ?, confidence = ?, threat_level = ?, 
                        ai_reasoning = ?, analyzed_at = ?
                    WHERE id = ?
                ''', [
                    result.get('classification'),
                    result.get('confidence'),
                    result.get('threat_level'),
                    result.get('reasoning'),
                    datetime.utcnow(),
                    spec_id
                ])
                db.commit()
                
                logging.info(f"🤖 AI Analysis: {result.get('classification')} ({result.get('confidence')}%) - {result.get('threat_level')}")
                
                # Emit analysis results to dashboard
                socketio.emit('spectrogram_analyzed', {
                    'id': spec_id,
                    'node_id': node_id,
                    'classification': result.get('classification'),
                    'confidence': result.get('confidence'),
                    'threat_level': result.get('threat_level'),
                    'reasoning': result.get('reasoning'),
                    'features_detected': result.get('features_detected', []),
                    'recommended_action': result.get('recommended_action')
                })
                
                # If chainsaw detected, create an alert
                if result.get('classification') == 'chainsaw' and result.get('confidence', 0) >= 70:
                    db.execute('''
                        INSERT INTO alerts 
                        (node_id, confidence, lat, lon, timestamp, rssi, ai_analysis, spectrogram_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', [
                        node_id,
                        result.get('confidence'),
                        lat,
                        lon,
                        timestamp,
                        rssi,
                        f"AI Vision: {result.get('reasoning')}",
                        spec_id
                    ])
                    db.commit()
                    
                    # Emit alert to dashboard
                    notification = generate_alert_notification(
                        {'node_id': node_id, 'lat': lat, 'lon': lon},
                        result
                    )
                    socketio.emit('new_alert', notification)
                    
                    logging.warning(f"🚨 CHAINSAW CONFIRMED by AI Vision at ({lat}, {lon})")
            else:
                logging.warning(f"AI Analysis failed: {result.get('error')}")
                
        except Exception as e:
            logging.error(f"Error during AI analysis: {e}")


def start_lora_receiver():
    """Start LoRa receiver and message processor"""
    try:
        from lora_receiver import init_receiver
        
        # Initialize and start receiver
        rx = init_receiver()
        rx.start()
        
        # Start message processor in background thread
        processor_thread = threading.Thread(target=process_lora_messages, daemon=True)
        processor_thread.start()
        
        logging.info("LoRa subsystem started successfully")
        
    except Exception as e:
        logging.error(f"Failed to start LoRa subsystem: {e}")


# Start LoRa receiver when app starts
start_lora_receiver()


if __name__ == '__main__':
    # Debug=False to prevent reloader stealing GPIO from first process
    # allow_unsafe_werkzeug=True for development (use gunicorn for production)
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)
