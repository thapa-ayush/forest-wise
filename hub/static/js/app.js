// app.js - Forest Guardian Hub
const socket = io({
    reconnection: true,
    reconnectionAttempts: 10,
    reconnectionDelay: 1000,
    reconnectionDelayMax: 5000,
    timeout: 20000,
    transports: ['websocket', 'polling'],  // Try WebSocket first, fallback to polling
    upgrade: true,  // Allow upgrade from polling to websocket
    forceNew: false
});

// Connection state
let isConnected = false;
let reconnectAttempts = 0;

socket.on('connect', () => {
    console.log('✅ Connected to server');
    isConnected = true;
    reconnectAttempts = 0;

    socket.on('disconnect', () => {
        console.log('Disconnected from server');
        isConnected = false;
        document.querySelectorAll('[data-connection-status]').forEach(el => {
            el.classList.remove('online');
            el.classList.add('offline');
        });
    });

    socket.on('reconnect_attempt', (attempt) => {
        reconnectAttempts = attempt;
        console.log(`Reconnecting... attempt ${attempt}`);
    });

    socket.on('reconnect', () => {
        console.log('Reconnected to server');
        // Refresh data after reconnection
        if (typeof loadStats === 'function') loadStats();
        if (typeof loadSpectrograms === 'function') loadSpectrograms();
    });

    socket.on('new_alert', (data) => {
        console.log('New alert received:', data);
        const audio = document.getElementById('alert-audio');
        if (audio) {
            audio.play().catch(e => console.log('Audio autoplay blocked'));
        }
        // Refresh stats instead of full page reload
        if (typeof loadStats === 'function') {
            loadStats();
        } else {
            location.reload();
        }
    });

    socket.on('node_update', (data) => {
        console.log('Node update received:', data);
        // Refresh stats instead of full page reload
        if (typeof loadStats === 'function') {
            loadStats();
        }
    });

    socket.on('new_spectrogram', (data) => {
        console.log('New spectrogram received:', data);
        if (typeof loadSpectrograms === 'function') {
            loadSpectrograms();
        }
        if (typeof loadStats === 'function') {
            loadStats();
        }
    });

    document.addEventListener('DOMContentLoaded', () => {
        console.log('Forest Guardian dashboard loaded');
    });
