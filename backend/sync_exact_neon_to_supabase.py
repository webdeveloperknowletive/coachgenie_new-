import asyncio
import json
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.config import settings

SRC_URL = settings.DATABASE_URL
DEST_URL = "postgresql+asyncpg://postgres.jwfsxqxebfqwrsxxmvyd:knowletive123@aws-0-ap-northeast-2.pooler.supabase.com:5432/postgres"

TABLES = [
    "users",
    "batches",
    "students",
    "batch_students",
    "admissions",
    "fee_structures",
    "fee_invoices",
    "fee_payments",
    "leads",
    "lead_activities",
    "attendance_records",
    "exams",
    "exam_results",
    "notification_templates",
    "notifications",
    "refresh_tokens",
    "audit_logs",
    "crm_pipeline_configs",
    "custom_field_definitions",
    "custom_field_values",
    "automation_rules",
    "automation_executions",
]

async def sync_remaining():
    print("Connecting to Neon & Supabase...")
    src = create_async_engine(SRC_URL)
    dest = create_async_engine(DEST_URL)

    for t in TABLES:
        try:
            async with src.connect() as sconn:
                res = await sconn.execute(text(f"SELECT * FROM {t};"))
                rows = res.fetchall()
                if not rows:
                    print(f"  [-] {t}: 0 rows")
                    continue
                cols = res.keys()
                raw_data = [dict(r._mapping) for r in rows]

            async with dest.connect() as dconn:
                dest_cols_res = await dconn.execute(text(f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name = '{t}';"))
                dest_col_info = {r[0]: r[1] for r in dest_cols_res.fetchall()}

            valid_cols = [c for c in cols if c in dest_col_info]
            if not valid_cols:
                continue

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

            async with dest.begin() as dconn:
                await dconn.execute(insert_sql, clean_data)
            print(f"  [+] {t}: {len(clean_data)} rows successfully migrated!")

        except Exception as err:
            safe_err = str(err).encode('ascii', errors='ignore').decode('ascii')
            print(f"  [!] Table {t} note: {safe_err[:120]}")

    print("\n--- Final Verification on Supabase ---")
    async with dest.connect() as dconn:
        t_cnt = (await dconn.execute(text("SELECT count(*) FROM tenants;"))).scalar()
        u_cnt = (await dconn.execute(text("SELECT count(*) FROM users;"))).scalar()
        s_cnt = (await dconn.execute(text("SELECT count(*) FROM students;"))).scalar()
        b_cnt = (await dconn.execute(text("SELECT count(*) FROM batches;"))).scalar()
        p_cnt = (await dconn.execute(text("SELECT count(*) FROM fee_payments;"))).scalar()
        p_sum = (await dconn.execute(text("SELECT coalesce(sum(amount), 0) FROM fee_payments WHERE tenant_id='104e64da-797a-4e81-abee-e14d4f52aa27';"))).scalar()

        print(f"Tenants: {t_cnt}")
        print(f"Users: {u_cnt}")
        print(f"Students: {s_cnt}")
        print(f"Batches: {b_cnt}")
        print(f"Fee payments: {p_cnt}")
        print(f"Total Fees Collected for Demo: INR {p_sum:,.2f}")

if __name__ == "__main__":
    asyncio.run(sync_remaining())
