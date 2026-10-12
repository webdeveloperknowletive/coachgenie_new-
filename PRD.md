# 📋 Product Requirements Document (PRD) — CoachGenie AI (Phase 1)

> **Document Version:** 1.0.0  
> **Status:** Production / Active  
> **Target System:** CoachGenie AI Coaching Institute ERP & Agentic Analytics System

---

## 1. Executive Summary & Vision

**CoachGenie AI** is a multi-tenant, production-grade Institute Management System & AI Operating System tailored for coaching institutes, test-prep academies, and tutorial centers.

The platform bridges operational management (leads, admissions, batches, attendance, examinations, fee collection) with intelligent educational intelligence (student dropout prediction, automated report generation, AI teaching copilot, and multi-lingual voice/video briefing).

---

## 2. User Personas

| Persona | Role | Key Needs & Pain Points | Primary Goals |
| :--- | :--- | :--- | :--- |
| **Super Admin** | Platform Owner / Multi-Tenant Mgr | Needs platform-wide metrics, tenant provisioning, and billing oversight. | Monitor tenant health, isolate databases, configure global system settings. |
| **Institute Admin (Owner/Director)** | Executive Management | Struggling with high lead leakage, fee default rates, and manual staff tracking. | Automated lead conversion CRM, fee installment tracking, aggregate performance analytics. |
| **Teacher / Tutor** | Academic Staff | Spends too much time marking manual attendance, making test reports, and tracking syllabus progress. | 1-click attendance, automated test grading, syllabus completion tracker, AI lesson generation. |
| **Student** | Learner / Candidate | Needs access to class schedules, test results, fee receipts, and customized doubt clearing. | Track academic growth, view test score trends, access learning materials and AI tutor assistance. |
| **Parent / Guardian** | Sponsor / Overseer | Lack of visibility into actual attendance, test scores, and pending fee due dates. | Receive real-time SMS/WhatsApp/Push attendance alerts, monthly progress cards, fee receipts. |

---

## 3. Feature Breakdown: MVP (Phase 1) vs. Future Scope

### 🟢 Phase 1: MVP Core Scope (Delivered & Active)

1. **Authentication & Multi-Tenant RBAC:**
   - Multi-tenant tenant segregation (`tenant_id` scope).
   - JWT-based authentication with bcrypt hashing.
   - Role-Based Access Control: `SUPER_ADMIN`, `INSTITUTE_ADMIN`, `TUTOR`, `STUDENT`, `PARENT`.

2. **Lead Management & CRM Pipeline:**
   - Lead capture from web/manual sources.
   - Stage tracking (`NEW`, `CONTACTED`, `DEMO_SCHEDULED`, `ENROLLED`, `LOST`).
   - Follow-up reminders and conversion to student with 1-click admission.

3. **Student Information & Admissions:**
   - Full student lifecycle KYC, parent linking, batch assignment.
   - Document records and enrollment logs.

4. **Batch & Timetable Management:**
   - Multi-subject batch scheduling, classroom allocation, teacher assignments.
   - Dynamic timetable calendar.

5. **Attendance Management:**
   - Daily batch-wise student & faculty attendance marking.
   - Absence alert logging and aggregate attendance percentage calculations.

6. **Exams & Performance Tracking:**
   - Examination scheduling (Offline/Online marks entry).
   - Subject-wise grading, percentile calculation, and score report generation.

7. **Fee Management & Invoicing:**
   - Fee structure definitions (lump-sum vs. monthly/quarterly installments).
   - Payment collection recording (Cash, UPI, NetBanking, Cheque).
   - Automated PDF receipt generation and overdue reminder tracking.

8. **AI Copilot & Smart Growth Cards:**
   - Student academic health insights (Dropout Risk Warning).
   - AI-driven automated feedback reports for parent-teacher meetings.

---

### 🔮 Phase 2: Future Scope (Post-MVP)

- 💳 **Direct Payment Gateway Integration** (Razorpay / Stripe auto-debit webhooks).
- 📲 **Biometric / RFID Hardware Sync** for automated turnstile attendance.
- 🤖 **Voice-Interactive Real-time AI Tutor** for students in native regional languages.
- 📱 **Native Mobile Apps** (React Native / Flutter for iOS & Android).
- 📊 **Multi-Branch Franchise Hierarchy** with centralized consolidated financial ledger.

---

## 4. End-to-End User Flow Steps

### Flow A: Lead Capture to Admission & Batch Assignment
```
[Visitor/Ad Lead] 
       │
       ▼
[Lead Captured (CRM)] ──▶ [Follow-Up Call Logged] ──▶ [Demo Class Completed]
                                                              │
                                                              ▼
[Convert Lead to Student] ◀───────────────────────── [Admit Student Button]
       │
       ├─▶ 1. Generate Student ID & Parent Account
       ├─▶ 2. Set Fee Structure & Payment Installments
       └─▶ 3. Assign to Batch & Issue Welcome Notification
```

### Flow B: Daily Academic & Attendance Cycle
```
[Tutor Logs In] ──▶ [Select Batch Dashboard] ──▶ [Mark Attendance (Present/Absent)]
                                                          │
       ┌──────────────────────────────────────────────────┴────────────────────────────────┐
       ▼                                                                                  ▼
[Auto-Log Absentee Alerts]                                                [Syllabus Topic Marked Completed]
       │                                                                                  │
       ▼                                                                                  ▼
[Notify Parents]                                                          [Update AI Student Growth Index]
```

### Flow C: Examination to AI Performance Card
```
[Exam Created] ──▶ [Marks Entered by Subject] ──▶ [Aggregate Performance Calculated]
                                                              │
                                                              ▼
[AI Copilot Analysis] ──▶ [Generate Growth Card PDF] ──▶ [Distribute to Parent/Student Portal]
```

---

## 5. Acceptance Criteria (Definition of Done)

| Module | Acceptance Criteria |
| :--- | :--- |
| **Auth & Security** | User cannot access records belonging to another `tenant_id`. Passwords must be hashed with `bcrypt`. Expired JWT tokens return `401 Unauthorized`. |
| **Lead CRM** | Adding a lead with duplicate phone number warns user. Converting a lead creates both a `Student` and a linked `Parent` record in a single atomic transaction. |
| **Attendance** | Marking a student absent updates their monthly attendance % in real-time. Prevents duplicate attendance entries for the same date/batch. |
| **Fee Collection**| Payments cannot exceed the total outstanding balance. Every successful payment generates a sequential invoice number and downloadable receipt. |
| **AI Reports** | AI Growth Card generates in < 4 seconds with actionable strengths, weaknesses, and remedial recommendations. |
