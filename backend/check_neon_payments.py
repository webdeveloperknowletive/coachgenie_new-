import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.config import settings

async def check():
    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.connect() as conn:
        payments = (await conn.execute(text('SELECT id, tenant_id, amount FROM fee_payments;'))).fetchall()
        print(f'Neon fee_payments total count: {len(payments)}')
        for p in payments:
            print(' ', p)

if __name__ == '__main__':
    asyncio.run(check())
