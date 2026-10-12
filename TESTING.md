# 🧪 Testing & Verification Guide (TESTING.md) — The AI Safety Net

> **Target System:** CoachGenie AI  
> **Mandatory AI Loop:** Write/Modify Code ➡️ Run Automated Verification Commands ➡️ Inspect Failures ➡️ Fix Regression ➡️ Commit

---

## 1. Automated Verification CLI Commands

Every AI agent must execute the relevant local verification commands before finalizing code changes:

### 🐍 Backend Verification (FastAPI / Pytest)
```bash
# 1. Run full backend unit and integration test suite
pytest backend/tests/ -v

# 2. Run with coverage report
pytest backend/tests/ --cov=backend/app --cov-report=term-missing

# 3. Run specific domain test (e.g., Leads, Auth, Fees)
pytest backend/tests/test_leads.py -v
pytest backend/tests/test_auth.py -v
pytest backend/tests/test_fees.py -v
```

### 🔒 Security & Defense Verification
```bash
# Run automated CI Security, SQL Injection, and Secrets Scanner suite
python run_ci_security_suite.py
python test_sql_injection_defense.py
python test_error_handling_defense.py
python test_dependency_verification.py
```

### 🌐 Frontend & E2E Verification (Playwright & Next.js)
```bash
# 1. Run Next.js type check & linter
cd client && pnpm run lint

# 2. Run Playwright End-to-End User Flow Tests
npx playwright test
node test_all_modules_multilingual.js
```

---

## 2. Test Fixtures & Scaffolding Rules

### Backend Test Fixtures (`backend/tests/conftest.py`)
```python
import pytest
from httpx import AsyncClient
from app.main import app
from app.database import get_db, Base, engine

@pytest.fixture(scope="session")
async def client():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.fixture
def auth_headers_admin():
    # Returns JWT headers for an Institute Admin
    return {"Authorization": "Bearer test_admin_jwt_token_tenant_1"}

@pytest.fixture
def auth_headers_tutor():
    # Returns JWT headers for a Tutor
    return {"Authorization": "Bearer test_tutor_jwt_token_tenant_1"}
```

---

## 3. Mock Data Structures for Testing

### Mock Lead Payload
```json
{
  "name": "Aarav Sharma",
  "phone": "+919876543210",
  "email": "aarav.sharma@example.com",
  "course_interested": "IIT-JEE Advanced",
  "notes": "Inquired for 2-year classroom program"
}
```

### Mock Attendance Marking Payload
```json
{
  "batch_id": "b10a5638-3482-4f6c-843e-782a17684df3",
  "date": "2026-09-01",
  "records": [
    { "student_id": "s82a4521-1234-4b5c-912a-892a17684df1", "status": "PRESENT" },
    { "student_id": "s92b6789-5678-4c6d-823b-903b28795ef2", "status": "ABSENT" }
  ]
}
```

### Mock Fee Payment Transaction
```json
{
  "student_id": "s82a4521-1234-4b5c-912a-892a17684df1",
  "amount": 25000.00,
  "payment_mode": "UPI",
  "reference_id": "UPI-IND-20260901-8932",
  "remarks": "Term 1 Tuition Fee Installment"
}
```

---

## 4. Definition of Pass for AI Execution
An AI modification is considered complete **ONLY** if:
1. All Pytest assertions pass with 0 errors.
2. The endpoint responds with valid HTTP status codes (`200 OK`, `201 Created`).
3. Multi-tenant isolation test asserts data cannot be read by another `tenant_id`.
4. No secrets or credentials are hardcoded into source code.
