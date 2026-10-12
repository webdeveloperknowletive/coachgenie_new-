import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import app.models  # noqa: F401
from app.database import Base
from app.config import settings

SRC_URL = settings.DATABASE_URL
DEST_URL = "postgresql+asyncpg://postgres.jwfsxqxebfqwrsxxmvyd:knowletive123@aws-0-ap-northeast-2.pooler.supabase.com:5432/postgres"

TABLES_ORDER = [
    "tenants",
    "roles",
    "users",
    "batches",
    "students",
    "parents",
    "batch_students",
    "leads",
    "lead_activities",
    "admissions",
    "fee_structures",
    "fee_invoices",
    "fee_payments",
    "notification_templates",
    "notifications",
    "exams",
    "exam_results",
    "attendance_records",
    "refresh_tokens",
    "audit_logs",
    "crm_pipeline_configs",
    "custom_field_definitions",
    "custom_field_values",
    "automation_rules",
    "automation_executions",
]

async def migrate():
    print("Connecting to source (Neon)...")
    src_engine = create_async_engine(SRC_URL)

    print("Connecting to destination (Supabase)...")
    dest_engine = create_async_engine(DEST_URL)

    print("Ensuring tables created on Supabase...")
    async with dest_engine.begin() as dest_conn:
        await dest_conn.run_sync(Base.metadata.create_all)
    print("Tables created.")

    # Migrate table by table with individual transactions
    async with src_engine.connect() as src_conn:
        for tbl in TABLES_ORDER:
            try:
                res = await src_conn.execute(text(f"SELECT * FROM {tbl};"))
                rows = res.fetchall()
                if not rows:
                    print(f"  [-] {tbl}: 0 rows")
                    continue

                cols = res.keys()
                col_names = ", ".join(cols)
                placeholders = ", ".join([f":{c}" for c in cols])
                insert_stmt = text(f"INSERT INTO {tbl} ({col_names}) VALUES ({placeholders}) ON CONFLICT DO NOTHING;")
                data = [dict(row._mapping) for row in rows]

                async with dest_engine.begin() as dest_conn:
                    await dest_conn.execute(insert_stmt, data)
                print(f"  [+] {tbl}: migrated {len(data)} rows")
            except Exception as e:
                print(f"  [!] Note for table {tbl}: {e}")

    print("\n--- Verifying Migrated Counts on Supabase ---")
    async with dest_engine.connect() as dest_conn:
        for tbl in ["tenants", "users", "students", "batches", "fee_invoices", "fee_payments", "leads", "admissions"]:
            try:
                cnt = (await dest_conn.execute(text(f"SELECT count(*) FROM {tbl};"))).scalar()
                print(f"  {tbl}: {cnt} rows")
            except Exception as e:
                print(f"  {tbl}: error ({e})")

if __name__ == "__main__":
    asyncio.run(migrate())
