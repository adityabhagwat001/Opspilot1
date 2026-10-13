"""
OpsPilot Administrative Script: Initialize & Seed Productivity Store
Explicit administrative setup for mock sandbox productivity mailbox and calendar.
"""

import sys
import os
import asyncio

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from mcp_servers.productivity_server.server import prod_store

async def main():
    print("Initializing productivity database schema...")
    await prod_store.init_db()
    print("Productivity schema initialized and seeded successfully.")

if __name__ == "__main__":
    asyncio.run(main())
