# Forest Guardian - API Reference

## Authentication
All API endpoints (except `/api/status`) require authentication via Flask-Login session cookie.

---

## Endpoints

### GET /api/status
Returns system status.

**Response:**
```json
{
  "status": "ok",
  "time": "2026-01-01T00:00:00.000000"
}
```

---

### GET /api/nodes
Returns all registered nodes.

**Response:**
```json
[
  {
    "node_id": "GUARDIAN_001",
    "last_seen": "2026-01-01 00:00:00",
    "battery": 80,
    "lat": 43.65,
    "lon": -79.38,
    "status": "active"
  }
]
```

---

### GET /api/alerts
Returns recent alerts (up to 100).

**Response:**
```json
[
  {
    "id": 1,
    "node_id": "GUARDIAN_001",
    "confidence": 85,
    "lat": 43.65,
    "lon": -79.38,
    "timestamp": "2026-01-01 00:00:00",
    "ai_analysis": "...",
    "responded": 0,
    "responded_by": null,
    "responded_at": null
  }
]
```

---

### POST /api/alerts/{id}/respond
Marks an alert as responded.

**Request:**
- `id`: Alert ID (path parameter)

**Response:**
```json
{ "success": true }
```

---

### GET /api/reports/daily
Returns AI-generated daily report.

**Response:**
```json
{
  "report": "Summary of alerts..."
}
```

---

### GET /api/reports/risk
Returns AI risk prediction (placeholder).

**Response:**
```json
{
  "risk_areas": []
}
```

---

### POST /api/simulate/alert
Simulates a new alert (for testing/demo).

**Request Body:**
```json
{
  "node_id": "SIM_001",
  "confidence": 85,
  "lat": 43.65,
  "lon": -79.38
}
```

**Response:**
```json
{ "success": true }
```

---

### POST /api/simulate/heartbeat
Simulates a node heartbeat (for testing/demo).

**Request Body:**
```json
{
  "node_id": "SIM_001",
  "battery": 80,
  "lat": 43.65,
  "lon": -79.38
}
```

**Response:**
```json
{ "success": true }
```

---

## WebSocket Events

### `new_alert`
Emitted when a new alert is received.

**Payload:**
```json
{
  "node_id": "GUARDIAN_001",
  "confidence": 85,
  "lat": 43.65,
  "lon": -79.38
}
```

---

### `node_update`
Emitted when a node status is updated.

**Payload:**
```json
{
  "node_id": "GUARDIAN_001",
  "battery": 80,
  "lat": 43.65,
  "lon": -79.38
}
```

---

## Error Handling
All endpoints return JSON errors:
```json
{ "error": "Unauthorized" }
```

---

## License
MIT
