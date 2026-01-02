// app.js - Forest Guardian Hub
const socket = io();

socket.on('connect', () => {
    console.log('Connected to server');
});

socket.on('new_alert', (data) => {
    const audio = document.getElementById('alert-audio');
    if (audio) audio.play();
    location.reload();
});

socket.on('node_update', (data) => {
    location.reload();
});

document.addEventListener('DOMContentLoaded', () => {
    // Simulation buttons
    const alertBtn = document.getElementById('simulate-alert');
    if (alertBtn) {
        alertBtn.addEventListener('click', async () => {
            await fetch('/api/simulate/alert', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ node_id: 'SIM_001', confidence: 85, lat: 43.65, lon: -79.38 }) });
        });
    }
    const heartbeatBtn = document.getElementById('simulate-heartbeat');
    if (heartbeatBtn) {
        heartbeatBtn.addEventListener('click', async () => {
            await fetch('/api/simulate/heartbeat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ node_id: 'SIM_001', battery: 80, lat: 43.65, lon: -79.38 }) });
        });
    }
});
