"""
OpsPilot Administrative Script: Initialize & Seed Operational Database
Explicit administrative setup for operational schema and realistic baseline fixtures.
NEVER called implicitly by MCP read tools.
"""

import sys
import os
import asyncio

# Add project root to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from mcp_servers.postgres_server.db import ops_db

async def main():
    print(f"Initializing operational database schema at: {ops_db.db_url}")
    await ops_db.init_db()
    print("Operational database schema initialized and seeded successfully.")

if __name__ == "__main__":
    asyncio.run(main())
