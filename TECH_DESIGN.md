# 🏗️ Technical Architecture & Design Document (TECH_DESIGN.md) — CoachGenie AI

> **Target System:** CoachGenie AI Institute Management Platform  
> **Architecture Pattern:** Multi-Tenant Modular Monolith / Micro-ready Service Architecture  
> **Last Updated:** 2026-09-01

---

## 1. Tech Stack Decisions & Rationale

```
+-------------------------------------------------------------------------+
|                              FRONTEND LAYER                             |
|       Next.js 15 (App Router) + React 19 + TypeScript + Tailwind CSS     |
|             State: TanStack Query + Zustand | Icons: Lucide             |
+-------------------------------------------------------------------------+
                                    │  HTTPS / REST / WebSocket
                                    ▼
+-------------------------------------------------------------------------+
|                              BACKEND LAYER                              |
|          FastAPI (Python 3.11+) + Pydantic v2 + SQLAlchemy 2.0          |
|    Security: OAuth2 Bearer + JWT (HS256/RS256) + Bcrypt Passwords       |
+-------------------------------------------------------------------------+
                 │                                    │
                 ▼                                    ▼
+---------------------------------+  +------------------------------------+
|         DATA STORAGE            |  |         AI & ASYNC ENGINE          |
| PostgreSQL 15+ (Relational)     |  | LangChain + OpenAI/Gemini SDK      |
| Redis (Caching & Rate Limiting) |  | APScheduler / Celery Workers       |
+---------------------------------+  +------------------------------------+
```

### Rationale Matrix

| Layer | Selected Tech | Key Justification |
| :--- | :--- | :--- |
| **Frontend** | `Next.js 15` + `TypeScript` + `Tailwind` | Server-Side Rendering (SSR) for fast initial load, strict type safety, modular component library. |
| **Backend** | `FastAPI` (Python) | High-throughput asynchronous I/O, native Pydantic data validation, automatic OpenAPI / Swagger generation. |
| **Database** | `PostgreSQL 15+` | ACID compliance, JSONB capabilities for flexible student/exam attributes, row-level multi-tenant indexing. |
| **ORM / Migration** | `SQLAlchemy 2.0` + `Alembic` | Strict typed declarative models, robust migration lifecycle management. |
| **Cache & Limiting** | `Redis` | Sub-millisecond session validation, rate-limiting, and AI prompt caching. |
| **AI Copilot** | `LangChain` / `OpenAI` / `Gemini` | Dynamic prompt templating, automated document generation, contextual academic evaluations. |

---

## 2. Multi-Tenant Database Schema

Every business table enforces tenant segregation using a mandatory `tenant_id` foreign key.

```mermaid
erDiagram
    TENANTS ||--o{ USERS : "contains"
    TENANTS ||--o{ LEADS : "tracks"
    TENANTS ||--o{ BATCHES : "manages"
    TENANTS ||--o{ STUDENTS : "enrolls"
    
    USERS ||--o| STUDENTS : "authenticates"
    USERS ||--o| PARENTS : "authenticates"
    USERS ||--o| TUTORS : "authenticates"
    
    STUDENTS }|--|| PARENTS : "linked_to"
    STUDENTS }|--o{ BATCH_STUDENTS : "assigned"
    BATCHES ||--o{ BATCH_STUDENTS : "contains"
    
    BATCHES ||--o{ ATTENDANCE : "logs"
    STUDENTS ||--o{ ATTENDANCE : "records"
    
    BATCHES ||--o{ EXAMS : "schedules"
    EXAMS ||--o{ EXAM_RESULTS : "scores"
    STUDENTS ||--o{ EXAM_RESULTS : "receives"
    
    STUDENTS ||--o{ FEES : "billed"
    FEES ||--o{ FEE_PAYMENTS : "settles"
```

### Core Table Schemas

```sql
-- 1. Tenants (Institutes)
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    subdomain VARCHAR(100) UNIQUE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Users (Authentication & RBAC)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL CHECK (role IN ('SUPER_ADMIN', 'INSTITUTE_ADMIN', 'TUTOR', 'STUDENT', 'PARENT')),
    full_name VARCHAR(255) NOT NULL,
    phone VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. Leads (CRM)
CREATE TABLE leads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    phone VARCHAR(50) NOT NULL,
    email VARCHAR(255),
    course_interested VARCHAR(100),
    status VARCHAR(50) DEFAULT 'NEW', -- NEW, CONTACTED, DEMO_SCHEDULED, ENROLLED, LOST
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 4. Batches & Courses
CREATE TABLE batches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    subject VARCHAR(100) NOT NULL,
    tutor_id UUID REFERENCES users(id),
    start_time TIME,
    end_time TIME,
    is_active BOOLEAN DEFAULT TRUE
);

-- 5. Students
CREATE TABLE students (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    parent_id UUID REFERENCES users(id),
    enrollment_number VARCHAR(100) UNIQUE NOT NULL,
    admission_date DATE DEFAULT CURRENT_DATE,
    status VARCHAR(50) DEFAULT 'ACTIVE'
);

-- 6. Fees & Invoices
CREATE TABLE fees (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    student_id UUID REFERENCES students(id) ON DELETE CASCADE,
    total_amount NUMERIC(10,2) NOT NULL,
    paid_amount NUMERIC(10,2) DEFAULT 0.00,
    due_amount NUMERIC(10,2) NOT NULL,
    due_date DATE,
    status VARCHAR(50) DEFAULT 'PENDING' -- PENDING, PARTIAL, PAID, OVERDUE
);
```

---

## 3. API Endpoints Map (FastAPI Router Topology)

| Prefix | Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- | :--- |
| `/api/auth` | `POST` | `/login` | Authenticate user & return JWT token | Public |
| `/api/auth` | `GET` | `/me` | Get current logged-in user profile | Bearer Token |
| `/api/tenants` | `GET` / `POST` | `/` | List / Provision institute tenants | Super Admin |
| `/api/leads` | `GET` / `POST` | `/` | Fetch all leads / Create new lead | Admin / Tutor |
| `/api/leads` | `PUT` | `/{lead_id}/convert` | Convert lead to enrolled student | Admin |
| `/api/students` | `GET` / `POST` | `/` | List students / Register student | Admin / Tutor |
| `/api/batches` | `GET` / `POST` | `/` | Manage institute class batches | Admin / Tutor |
| `/api/attendance`| `POST` | `/mark` | Record batch attendance | Tutor / Admin |
| `/api/attendance`| `GET` | `/summary` | Get student attendance percentage | Authenticated |
| `/api/exams` | `GET` / `POST` | `/` | Create exams and record test marks | Tutor / Admin |
| `/api/fees` | `GET` / `POST` | `/` | Manage student fee records & payments | Admin / Parent |
| `/api/ai` | `POST` | `/growth-card` | Generate AI student performance card | Admin / Tutor |
| `/api/ai` | `POST` | `/copilot` | Real-time AI chat query for institute ERP | Authenticated |

---

## 4. Security, Isolation & Environment Boundaries

### Multi-Tenant Isolation Rule
- Every database query executed through SQLAlchemy must pass through the `get_current_tenant_id` dependency.
- Global filter enforcement prevents Cross-Tenant Data Leaks:
```python
# app/dependencies.py
async def get_current_user_and_tenant(
    token: str = Depends(oauth2_scheme), 
    db: AsyncSession = Depends(get_db)
) -> User:
    payload = decode_jwt(token)
    user = await get_user_by_id(db, payload.get("sub"))
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return user
```

### Environment Configuration (.env)
```ini
# Core Configuration
ENVIRONMENT=production
SECRET_KEY=your-secure-jwt-secret-key-32-bytes
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Database
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/coachgenie_db
REDIS_URL=redis://localhost:6379/0

# AI / LLM Integrations
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=AIza...

# CORS Allowed Origins
CORS_ORIGINS=["http://localhost:3000","https://app.coachgenie.ai"]
```
