import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DEST_URL = 'postgresql+asyncpg://postgres.jwfsxqxebfqwrsxxmvyd:knowletive123@aws-0-ap-northeast-2.pooler.supabase.com:5432/postgres'

async def fix_demo_tenant():
    engine = create_async_engine(DEST_URL)
    async with engine.begin() as conn:
        # Check if demo tenant has id '104e64da-797a-4e81-abee-e14d4f52aa27'
        res = await conn.execute(text("SELECT id, subdomain FROM tenants WHERE subdomain='demo';"))
        row = res.fetchone()
        print("Current demo tenant in Supabase:", row)
        
        # Delete dummy demo tenant
        await conn.execute(text("DELETE FROM tenants WHERE subdomain IN ('demo', 'demo2');"))
        
        # Insert the exact Neon demo tenant
        await conn.execute(text("""
            INSERT INTO tenants (id, name, subdomain, plan, is_active, settings)
            VALUES (
                '104e64da-797a-4e81-abee-e14d4f52aa27',
                'CoachGenie Top AI Academy',
                'demo',
                'enterprise',
                true,
                '{"theme": "blue"}'
            )
            ON CONFLICT (id) DO UPDATE SET subdomain='demo', name='CoachGenie Top AI Academy';
        """))
        print("Inserted exact Neon demo tenant (104e64da-797a-4e81-abee-e14d4f52aa27)!")

if __name__ == '__main__':
    asyncio.run(fix_demo_tenant())
