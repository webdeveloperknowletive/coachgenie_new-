import asyncio
import json
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.config import settings

SRC_URL = settings.DATABASE_URL
DEST_URL = "postgresql+asyncpg://postgres.jwfsxqxebfqwrsxxmvyd:knowletive123@aws-0-ap-northeast-2.pooler.supabase.com:5432/postgres"

# Step 1: Admissions first, then Students, then Batches, etc.
TABLES = [
    "admissions",
    "students",
    "batch_students",
    "fee_structures",
    "fee_invoices",
    "fee_payments",
    "attendance_records",
]

async def sync_data():
    src = create_async_engine(SRC_URL)
    dest = create_async_engine(DEST_URL)

    # In PostgreSQL, we can defer or drop FKs or insert admissions without student, then student, then update
    for t in TABLES:
        async with src.connect() as sconn:
            res = await sconn.execute(text(f"SELECT * FROM {t};"))
            rows = res.fetchall()
            if not rows:
                print(f"[-] {t}: 0 rows")
                continue
            cols = res.keys()
            raw_data = [dict(r._mapping) for r in rows]

        async with dest.connect() as dconn:
            dest_cols_res = await dconn.execute(text(f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name = '{t}';"))
            dest_col_info = {r[0]: r[1] for r in dest_cols_res.fetchall()}

        valid_cols = [c for c in cols if c in dest_col_info]
        col_str = ", ".join(valid_cols)
        params_str = ", ".join([f":{c}" for c in valid_cols])

        clean_data = []
        for row in raw_data:
            clean_row = {}
            for c in valid_cols:
                val = row[c]
                dtype = dest_col_info[c].lower()
                if ("json" in dtype) and isinstance(val, (dict, list)):
                    clean_row[c] = json.dumps(val)
                else:
                    clean_row[c] = val
            clean_data.append(clean_row)

        insert_sql = text(f"INSERT INTO {t} ({col_str}) VALUES ({params_str}) ON CONFLICT DO NOTHING;")

        try:
            async with dest.begin() as dconn:
                # If students table, admission_id might point to admission or user_id
                await dconn.execute(insert_sql, clean_data)
            print(f"[+] {t}: {len(clean_data)} rows migrated!")
        except Exception as e:
            print(f"[!] {t} failed: {e}")

if __name__ == '__main__':
    asyncio.run(sync_data())
