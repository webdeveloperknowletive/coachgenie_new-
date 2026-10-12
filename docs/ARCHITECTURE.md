# CoachGenie Enterprise SaaS — Architecture & Engineering Baseline

> **Status:** Canonical Engineering Source of Truth  
> **Architecture Pattern:** Multi-Tenant Modular Monolith with Specialized RAG/Copilot Engine  
> **Last Validated:** 2026-09-01

---

## 1. Domain Model & Tenant Hierarchy

CoachGenie enforces a multi-tenant hierarchy designed for single-tutor setups up to multi-branch enterprises:

```
Platform (Super Admin / CoachGenie)
└── Tenant (Institute / Organization)
    ├── [Optional] Branch
    │   └── [Optional] Department
    ├── Dynamic Custom Roles & RBAC Matrix
    ├── Dynamic Custom Fields Definitions
    ├── Courses / Programs
    │   └── Batches / Classes
    │       ├── Batch Students (Enrolled)
    │       ├── Attendance Sessions & Records
    │       └── Exams & Exam Results
    ├── CRM Leads & Lead Activities
    ├── Admissions & Verification Pipeline
    ├── Fee Structures, Invoices & Payments
    ├── Growth Cards & AI Copilot Sessions
    └── Notification Templates & Logs
```

---

## 2. Canonical Database Entities & Conventions

All business tables are tenant-isolated with mandatory `tenant_id: UUID` foreign keys referencing `tenants(id)` with `ON DELETE CASCADE`.

### Core Entities:
1. `tenants`: Institute profile, subdomain, plan tier, settings JSONB.
2. `users`: Authentication identities, email, Argon2 password hash, role (`owner`, `admin`, `counselor`, `tutor`, `student`, `parent`, `super_admin`).
3. `custom_roles`: Tenant-scoped dynamic roles (`name`, `description`, `permissions_json`).
4. `audit_logs`: Immutable audit trails capturing `(tenant_id, actor_id, action, entity_type, entity_id, metadata, timestamp)`.
5. `leads` & `lead_activities`: Prospective student CRM, status stages, notes, and follow-ups.
6. `admissions`: Registration records, required documents, fee commitments, approval workflows.
7. `students`: Enrolled student academic records, linked `user_id`, emergency contacts, dynamic `custom_fields` JSONB.
8. `batches` & `batch_students`: Class batches, schedules, capacity, and student enrollments.
9. `classes`: Timetable schedule instances, assigned tutor, room/link, and duration.
10. `attendance_sessions` & `attendance_records`: Date-indexed batch attendance marking with status (`present`, `absent`, `late`, `excused`).
11. `fee_structures`, `fee_invoices` & `fee_payments`: Fee assignments, installment schedules, settlement records, PDF receipts.
12. `exams` & `exam_results`: Assessments, total marks, passing thresholds, student scores, batch rankings.
13. `growth_cards`: 360-degree student behavioral and academic evaluations.
14. `notification_templates`, `notification_logs`, `inbox_notifications`: Multi-channel communication engine.

---

## 3. RBAC & Granular Permission Convention

### Permission Format: `<resource>.<action>`
- **Resources:** `leads`, `admissions`, `students`, `batches`, `attendance`, `fees`, `exams`, `growth_cards`, `reports`, `settings`, `audit_logs`
- **Actions:** `view`, `create`, `edit`, `delete`, `approve`, `publish`, `export`, `assign`, `manage`

### Permission Evaluator:
```python
def has_permission(user: User, resource: str, action: str) -> bool:
    # 1. Platform Super Admin and Institute Owner bypass with full permissions
    if user.role in ["super_admin", "owner"]:
        return True
    # 2. Check predefined role permission sets
    # 3. Check custom role permissions assigned to user
    return check_custom_role_permissions(user, f"{resource}.{action}")
```

---

## 4. Subscription & Entitlement Architecture

### Entitlement Evaluation Pipeline:
$$\text{Request} \rightarrow \text{Tenant Plan Resolution} \rightarrow \text{Quota & Feature Check} \rightarrow \text{Operation Permitted / Blocked}$$

- Hard caps checked server-side before insertion:
  - `students_count < plan.max_students`
  - `staff_count < plan.max_staff`
  - `batches_count < plan.max_batches`
- Feature flags evaluated:
  - `ai_copilot_enabled`
  - `multi_branch_enabled`
  - `custom_roles_enabled`
  - `automated_reminders_enabled`

---

## 5. Automation & Background Schedulers

- Zero-cost in-process scheduler (`APScheduler`) running async cron jobs on database sessions.
- **Idempotency Guarantees:**
  - Scheduled jobs (overdue fees, attendance alerts) use deterministic status transitions and unique constraint deduplication to prevent double-charging or duplicate alerts.
  - Job failure retry logic with exponential backoff and error logging.

---

## 6. Super Admin Platform Control Plane

The Super Admin Control Plane is the platform management surface of CoachGenie:
- **Scope & Isolation:** Super Admin operations operate at the platform level (`role="super_admin"`) with strict server-side verification in `get_current_super_admin`.
- **Navigation & Modules:** Dedicated platform workspace covering Overview, Institutes, Subscriptions, Plans, Entitlements, Usage & Quotas, AI/LLM Control Center, Platform Analytics, Finance, Feature Flags, Diagnostics, System Health, and Audit Logs.
- **AI / LLM Architecture:** Server-side model routing and inference provider registry without leaking API keys to client browsers.
- **Financial Architecture:** Clear separation between SaaS subscription license revenue (MRR/ARR) and tenant-level student tuition fee processing.

---

## 7. Definition of Done (DoD)

A feature or phase is considered **DONE** only when:
1. Requirements and acceptance criteria are completely met.
2. Server-side tenant isolation and RBAC evaluated and enforced.
3. Database migrations are backward-compatible and tested.
4. Input validation (Pydantic v2 schemas) in place.
5. Error handling and audit logging integrated.
6. Backend unit/integration tests pass (`pytest backend/tests`).
7. Frontend TypeScript compiles without errors (`tsc --noEmit`).
8. Zero fake implementations or hardcoded mocks in production code.

