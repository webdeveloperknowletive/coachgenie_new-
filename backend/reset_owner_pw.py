import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.config import settings
from app.utils.security import hash_password, verify_password

async def fix_owner_password():
    engine = create_async_engine(settings.DATABASE_URL)
    hashed = hash_password("Admin@1234")
    async with engine.begin() as conn:
        res = await conn.execute(text("SELECT u.email, u.password_hash, t.subdomain FROM users u JOIN tenants t ON u.tenant_id = t.id WHERE lower(u.email) = 'owner@demo.com';"))
        rows = res.fetchall()
        print("Existing owner@demo.com rows:", rows)
        
        # Ensure password is Admin@1234 for owner@demo.com
        await conn.execute(text(f"UPDATE users SET password_hash = '{hashed}', is_active = true WHERE lower(email) = 'owner@demo.com';"))
        print("Updated owner@demo.com password to Admin@1234!")

if __name__ == '__main__':
    asyncio.run(fix_owner_password())
