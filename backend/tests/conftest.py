import sys
import os
import asyncio

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

# Isolate all automated test execution to a dedicated test database
# to guarantee zero contamination of the live production/development opspilot_system.db
TEST_DB_PATH = os.path.join(BACKEND_ROOT, "test_opspilot.db").replace("\\", "/")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_DB_PATH}"
os.environ["ENVIRONMENT"] = "testing"
os.environ["DEMO_MODE"] = "false"
os.environ["MOCK_MODE"] = "true"

from app.core.config import settings
settings.DATABASE_URL = f"sqlite+aiosqlite:///{TEST_DB_PATH}"
settings.ENVIRONMENT = "testing"

from app.core.db import configure_db_engine, init_system_db
configure_db_engine(settings.DATABASE_URL)

try:
    asyncio.run(init_system_db())
except Exception:
    loop = asyncio.new_event_loop()
    loop.run_until_complete(init_system_db())
