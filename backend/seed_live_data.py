"""
CoachGenie - Database Seeder Utility
Reads seed_live_data.sql and applies all production seed records into the target database.
Safe and idempotent: uses ON CONFLICT DO NOTHING for primary keys.
"""

import asyncio
import os
import sys

# Ensure backend root is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal, engine
from sqlalchemy import text

async def run_seed():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    sql_file = os.path.join(current_dir, "seed_live_data.sql")
    
    if not os.path.exists(sql_file):
        print(f"❌ Error: seed file not found at {sql_file}")
        sys.exit(1)
        
    print(f"Reading seed SQL: {sql_file}")
    with open(sql_file, "r", encoding="utf-8") as f:
        sql_content = f.read()

    # Split by statements
    statements = [stmt.strip() for stmt in sql_content.split(";") if stmt.strip()]
    print(f"Total SQL statements to execute: {len(statements)}")

    async with SessionLocal() as session:
        executed = 0
        for stmt in statements:
            if not stmt or stmt.startswith("--") or stmt.upper() in ["BEGIN", "COMMIT"]:
                continue
            try:
                await session.execute(text(stmt))
                executed += 1
            except Exception as e:
                print(f"Warning on statement: {stmt[:60]}... -> {e}")
        
        await session.commit()
        print(f"Successfully seeded {executed} statements into database!")

if __name__ == "__main__":
    asyncio.run(run_seed())
