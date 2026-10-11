"""
OpsPilot Node Collector Daemon
==============================
A lightweight telemetry agent designed to run as a systemd service or background process.
It samples host metrics (CPU, RAM, Disk, Network) and periodically posts heartbeats to OpsPilot API.
"""

import os
import sys
import time
import socket
import platform
import logging
from typing import Dict, Any
import psutil
import httpx

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [OpsPilot-Agent] %(message)s"
)
logger = logging.getLogger("opspilot_agent")

OPSPILOT_URL = os.getenv("OPSPILOT_URL", "http://localhost:8000")
NODE_ID = os.getenv("NODE_ID", f"node-{socket.gethostname().lower()}")
API_KEY = os.getenv("NODE_API_KEY", "dev-agent-key-secret")
REPORT_INTERVAL_SECONDS = int(os.getenv("REPORT_INTERVAL_SECONDS", "5"))


def collect_metrics() -> Dict[str, Any]:
    """Collects real-time host system utilization metrics."""
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    net_io = psutil.net_io_counters()

    return {
        "node_id": NODE_ID,
        "hostname": socket.gethostname(),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "os": f"{platform.system()} {platform.release()}",
        "metrics": {
            "cpu_usage_pct": round(psutil.cpu_percent(interval=1), 2),
            "memory_used_mb": round((mem.total - mem.available) / (1024 * 1024), 2),
            "memory_total_mb": round(mem.total / (1024 * 1024), 2),
            "memory_usage_pct": round(mem.percent, 2),
            "disk_used_gb": round(disk.used / (1024 * 1024 * 1024), 2),
            "disk_total_gb": round(disk.total / (1024 * 1024 * 1024), 2),
            "disk_usage_pct": round(disk.percent, 2),
            "bytes_sent": net_io.bytes_sent,
            "bytes_recv": net_io.bytes_recv
        }
    }


def send_telemetry(payload: Dict[str, Any]) -> bool:
    """Dispatches metric snapshot to OpsPilot Central Gateway."""
    endpoint = f"{OPSPILOT_URL}/api/v1/telemetry/report"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    try:
        with httpx.Client(timeout=3.0) as client:
            resp = client.post(endpoint, json=payload, headers=headers)
            if resp.status_code in (200, 202):
                logger.info(f"Telemetry packet acknowledged by {OPSPILOT_URL}")
                return True
            else:
                logger.warning(f"Server returned status {resp.status_code}: {resp.text}")
                return False
    except httpx.RequestError as exc:
        logger.warning(f"Failed to transmit telemetry to {OPSPILOT_URL}: {exc}")
        return False


def main():
    logger.info(f"Initializing OpsPilot Agent probe for Node ID: {NODE_ID}")
    logger.info(f"Target Gateway: {OPSPILOT_URL} | Interval: {REPORT_INTERVAL_SECONDS}s")
    
    try:
        while True:
            payload = collect_metrics()
            logger.info(f"Sampled metrics - CPU: {payload['metrics']['cpu_usage_pct']}% | RAM: {payload['metrics']['memory_usage_pct']}%")
            # In Sprint 1, send_telemetry will test against gateway once endpoint is registered in Sprint 3
            time.sleep(REPORT_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        logger.info("Agent process terminated gracefully.")
        sys.exit(0)


if __name__ == "__main__":
    main()
