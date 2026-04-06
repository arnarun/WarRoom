#!/bin/sh
set -e

echo "=== WarRoom Backend Starting ==="
echo "PORT: ${PORT:-8000}"

echo "Initializing database schema..."
python - <<'EOF'
import asyncio
from database import engine
from models import Base

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database schema ready.")

asyncio.run(init_db())
EOF

echo "Starting server on port ${PORT:-8000}..."
exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}"
