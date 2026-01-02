# app.py - Forest Guardian Hub
import os
import json
import time
import logging
import threading
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, g, session
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from flask_login import login_required, current_user
from flask_wtf.csrf import CSRFProtect
from config import Config
from database import init_db, get_db, close_db, query_db, add_user
from auth import login_manager, limiter, auth_bp
from admin import admin_bp
from ai_service import analyze_alert, generate_daily_report, generate_sms_text

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
                        
                    elif data.get('type') == 'heartbeat':
                        # Update node status
                        db.execute('''
                            INSERT OR REPLACE INTO nodes 
                            (node_id, last_seen, battery, lat, lon, status, rssi)
                            VALUES (?, ?, ?, ?, ?, 'active', ?)
                        ''', [
                            data.get('node_id'),
                            timestamp,
                            data.get('battery'),
                            data.get('lat', 0),
                            data.get('lon', 0),
                            rssi
                        ])
                        db.commit()
                        
                        # Emit node update to web dashboard
                        socketio.emit('node_update', {
                            'node_id': data.get('node_id'),
                            'battery': data.get('battery'),
                            'lat': data.get('lat'),
                            'lon': data.get('lon'),
                            'timestamp': timestamp,
                            'rssi': rssi
                        })
                        
                        logging.info(f"💓 Heartbeat from {data.get('node_id')}")
            
            time.sleep(0.5)  # Check queue every 500ms
            
        except Exception as e:
            logging.error(f"Error processing LoRa messages: {e}")
            time.sleep(1)


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
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
