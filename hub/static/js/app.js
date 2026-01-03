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
    // App initialized
    console.log('Forest Guardian dashboard loaded');
});
