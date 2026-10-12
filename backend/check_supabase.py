import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DEST_URL = 'postgresql+asyncpg://postgres.jwfsxqxebfqwrsxxmvyd:knowletive123@aws-0-ap-northeast-2.pooler.supabase.com:5432/postgres'

async def check():
    engine = create_async_engine(DEST_URL)
    async with engine.connect() as conn:
        payments = (await conn.execute(text('SELECT coalesce(sum(amount), 0) FROM fee_payments;'))).scalar()
        students = (await conn.execute(text('SELECT count(*) FROM students;'))).scalar()
        batches = (await conn.execute(text('SELECT count(*) FROM batches;'))).scalar()
        print('Supabase State:')
        print('  Total students:', students)
        print('  Total batches:', batches)
        print('  Total fee payments:', payments)

if __name__ == '__main__':
    asyncio.run(check())
