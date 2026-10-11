# OpsPilot API Specification

## Base URL
`/api/v1`

All responses are serialized in `application/json` with ISO 8601 UTC timestamps.

---

## 1. System & Health Endpoints

### `GET /api/v1/health`
Checks the liveness and readiness of the OpsPilot service and downstream dependencies.

#### Response: `200 OK`
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "service": "opspilot-core",
  "timestamp": "2026-10-11T16:15:00Z",
  "uptime_seconds": 1284.52,
  "dependencies": {
    "database": "connected",
    "cache": "connected",
    "telemetry_bus": "active"
  }
}
```

---

## 2. Telemetry Ingestion Endpoints (Agent Contract)

### `POST /api/v1/telemetry/report`
Ingests a single or batched system metrics snapshot from an authorized agent.

#### Request Headers
* `Authorization: Bearer <NODE_API_KEY>`
* `Content-Type: application/json`

#### Request Body
```json
{
  "node_id": "srv-us-east-01",
  "hostname": "prod-api-worker-1",
  "timestamp": "2026-10-11T16:15:00Z",
  "os": "Linux 6.8.0-generic",
  "metrics": {
    "cpu_usage_pct": 42.8,
    "memory_used_mb": 6144,
    "memory_total_mb": 16384,
    "memory_usage_pct": 37.5,
    "disk_used_gb": 120.4,
    "disk_total_gb": 500.0,
    "disk_usage_pct": 24.08,
    "network_rx_kbps": 1420.5,
    "network_tx_kbps": 890.2
  },
  "containers": [
    {
      "id": "c1f8a92b3",
      "name": "nginx-ingress",
      "status": "running",
      "cpu_pct": 4.1,
      "memory_mb": 128
    }
  ]
}
```

#### Response: `202 Accepted`
```json
{
  "status": "acknowledged",
  "node_id": "srv-us-east-01",
  "anomalies_detected": false
}
```

---

## 3. WebSocket Real-time Feed

### `WS /api/v1/ws/telemetry`
Subscribes the frontend dashboard to real-time telemetry broadcasts and incident alerts.

#### Message Payload: `telemetry_tick`
```json
{
  "event": "telemetry_tick",
  "timestamp": "2026-10-11T16:15:05Z",
  "nodes_online": 12,
  "nodes_warning": 1,
  "nodes_critical": 0,
  "recent_metrics": [
    {
      "node_id": "srv-us-east-01",
      "cpu_usage_pct": 42.8,
      "memory_usage_pct": 37.5
    }
  ]
}
```

---

## 4. Error Response Schema
Standardized error format across all endpoints:

```json
{
  "error": {
    "code": "VALIDATION_FAILED",
    "message": "Field 'node_id' is required and must be alphanumeric.",
    "details": {},
    "timestamp": "2026-10-11T16:15:00Z"
  }
}
```
