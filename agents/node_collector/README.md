# OpsPilot Node Collector Probe

The OpsPilot Node Collector is a daemon designed to be installed on bare-metal servers, virtual machines, or container hosts.

## Core Responsibilities
- Continuously samples host telemetry (CPU, Memory, Disk, Network I/O).
- Formats metrics into standardized OpsPilot Telemetry Packets.
- Sends cryptographically signed/authenticated heartbeats to the central OpsPilot API.
- Backs off gracefully during network outages and recovers automatically.

## Requirements
- Python 3.9+
- `psutil`
- `httpx`

## Running Locally
```bash
python collector.py
```
