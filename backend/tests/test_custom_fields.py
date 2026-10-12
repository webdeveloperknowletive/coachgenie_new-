import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.tenant import Tenant
from app.models.student import Student
from app.models.lead import Lead
from app.models.batch import Batch
from app.models.admission import Admission


@pytest.mark.asyncio
async def test_student_custom_fields_persistence(client: AsyncClient, db_session: AsyncSession, tenant: Tenant, owner_headers: dict):
    # 1. Create a student with custom fields (e.g. Bus Route, Hostel Required)
    student_payload = {
        "enrollment_no": f"STU-CF-{uuid.uuid4().hex[:6]}",
        "first_name": "Rohan",
        "last_name": "Verma",
        "email": f"rohan-{uuid.uuid4().hex[:6]}@example.com",
        "phone": "9876543210",
        "parent_name": "Suresh Verma",
        "parent_phone": "9876543211",
        "current_class": "10th",
        "custom_fields": {
            "bus_route": "Route 42",
            "hostel_required": True,
            "scholarship_tier": "Gold 50%",
        },
    }

    create_res = await client.post("/api/v1/students/", json=student_payload, headers=owner_headers)
    assert create_res.status_code == 201
    created_stu = create_res.json()["data"]
    stu_id = created_stu["id"]
    assert created_stu["custom_fields"]["bus_route"] == "Route 42"
    assert created_stu["custom_fields"]["hostel_required"] is True

    # 2. Fetch student by ID and verify custom fields
    get_res = await client.get(f"/api/v1/students/{stu_id}", headers=owner_headers)
    assert get_res.status_code == 200
    fetched_stu = get_res.json()["data"]
    assert fetched_stu["custom_fields"]["scholarship_tier"] == "Gold 50%"

    # 3. Update custom fields
    update_payload = {
        "custom_fields": {
            "bus_route": "Route 10A",
            "hostel_required": False,
            "scholarship_tier": "Gold 50%",
            "extra_notes": "Changed bus route on parent request",
        }
    }
    update_res = await client.patch(f"/api/v1/students/{stu_id}", json=update_payload, headers=owner_headers)
    assert update_res.status_code == 200
    updated_stu = update_res.json()["data"]
    assert updated_stu["custom_fields"]["bus_route"] == "Route 10A"
    assert updated_stu["custom_fields"]["hostel_required"] is False
    assert updated_stu["custom_fields"]["extra_notes"] == "Changed bus route on parent request"


@pytest.mark.asyncio
async def test_lead_and_batch_custom_fields(client: AsyncClient, db_session: AsyncSession, tenant: Tenant, owner_headers: dict):
    # 1. Create a lead with custom fields
    lead_payload = {
        "full_name": "Priya Sharma",
        "phone": "9811223344",
        "email": f"priya-{uuid.uuid4().hex[:6]}@example.com",
        "source": "website",
        "status": "new",
        "custom_fields": {
            "lead_priority": "High",
            "target_score": 95,
            "counseling_notes": "Needs weekend batch only",
        },
    }
    lead_res = await client.post("/api/v1/leads/", json=lead_payload, headers=owner_headers)
    assert lead_res.status_code == 201
    lead_data = lead_res.json()["data"]
    lead_id = lead_data["id"]
    assert lead_data["custom_fields"]["lead_priority"] == "High"

    # 2. Create a batch with custom fields
    batch_payload = {
        "name": f"Batch JEE Adv-{uuid.uuid4().hex[:4]}",
        "academic_year": "2026-2027",
        "capacity": 60,
        "custom_fields": {
            "lab_room": "Lab 3B",
            "recording_available": True,
        },
    }
    batch_res = await client.post("/api/v1/batches/", json=batch_payload, headers=owner_headers)
    assert batch_res.status_code == 201
    batch_data = batch_res.json()["data"]
    assert batch_data["custom_fields"]["lab_room"] == "Lab 3B"
    assert batch_data["custom_fields"]["recording_available"] is True


@pytest.mark.asyncio
async def test_audit_logs_query(client: AsyncClient, db_session: AsyncSession, tenant: Tenant, owner_headers: dict):
    # Perform a role creation which automatically generates an audit log
    role_payload = {
        "name": f"Audited Role {uuid.uuid4().hex[:4]}",
        "description": "For audit testing",
        "permissions": ["leads.view"],
    }
    create_res = await client.post("/api/v1/roles/", json=role_payload, headers=owner_headers)
    assert create_res.status_code == 201

    # Query audit logs
    audit_res = await client.get("/api/v1/audit-logs/", headers=owner_headers)
    assert audit_res.status_code == 200
    audit_data = audit_res.json()
    assert audit_data["success"] is True
    assert audit_data["total"] >= 1
    assert any(log["action"] == "CREATE_ROLE" for log in audit_data["items"])
