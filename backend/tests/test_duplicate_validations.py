import pytest
import uuid
from datetime import datetime, timezone, date
from app.models.tenant import Tenant
from app.models.user import User
from app.models.lead import Lead
from app.models.student import Student
from app.models.admission import Admission
from app.models.batch import Batch, Subject, Class
from app.models.fee import FeeStructure, FeeInvoice
from app.models.syllabus import SyllabusItem
from app.services import (
    lead as lead_service,
    student as student_service,
    admission as admission_service,
    batch as batch_service,
    fee as fee_service,
    syllabus as syllabus_service,
    auth as auth_service,
    exam as exam_service,
)
from app.utils.exceptions import ConflictError


@pytest.mark.asyncio
async def test_duplicate_lead_validation(db_session, tenant):
    """Test that creating a lead with an existing phone or email raises ConflictError."""
    # 1. Create initial lead
    lead1 = await lead_service.create_lead(
        db_session,
        str(tenant.id),
        {
            "full_name": "Aman Verma",
            "phone": "9876543210",
            "email": "aman@example.com",
            "source": "website",
        }
    )
    assert lead1.id is not None

    # 2. Try creating lead with same phone -> ConflictError
    with pytest.raises(ConflictError) as exc_info:
        await lead_service.create_lead(
            db_session,
            str(tenant.id),
            {
                "full_name": "Aman Duplicate Phone",
                "phone": "9876543210",
                "email": "different@example.com",
                "source": "referral",
            }
        )
    assert "already exists" in str(exc_info.value.detail)

    # 3. Try creating lead with same email -> ConflictError
    with pytest.raises(ConflictError) as exc_info:
        await lead_service.create_lead(
            db_session,
            str(tenant.id),
            {
                "full_name": "Aman Duplicate Email",
                "phone": "9876500000",
                "email": "AMAN@EXAMPLE.COM",  # Case insensitive
                "source": "social",
            }
        )
    assert "already exists" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_duplicate_student_validation(db_session, tenant):
    """Test that creating a student with an existing email, phone, or enrollment_no raises ConflictError."""
    stu1 = await student_service.create_student(
        db_session,
        str(tenant.id),
        {
            "first_name": "Rohan",
            "last_name": "Sharma",
            "enrollment_no": "STU-DUP-001",
            "email": "rohan@example.com",
            "phone": "9123456780",
        }
    )
    assert stu1.id is not None

    # Duplicate email
    with pytest.raises(ConflictError):
        await student_service.create_student(
            db_session,
            str(tenant.id),
            {
                "first_name": "Other",
                "last_name": "Person",
                "enrollment_no": "STU-DUP-002",
                "email": "rohan@example.com",
                "phone": "9999999999",
            }
        )

    # Duplicate phone
    with pytest.raises(ConflictError):
        await student_service.create_student(
            db_session,
            str(tenant.id),
            {
                "first_name": "Other",
                "last_name": "Person",
                "enrollment_no": "STU-DUP-003",
                "email": "other@example.com",
                "phone": "9123456780",
            }
        )

    # Duplicate enrollment_no
    with pytest.raises(ConflictError):
        await student_service.create_student(
            db_session,
            str(tenant.id),
            {
                "first_name": "Other",
                "last_name": "Person",
                "enrollment_no": "STU-DUP-001",
                "email": "unique@example.com",
                "phone": "9888888888",
            }
        )


@pytest.mark.asyncio
async def test_duplicate_admission_validation(db_session, tenant):
    """Test that creating an admission with an existing email or phone raises ConflictError."""
    adm1 = await admission_service.create_admission(
        db_session,
        str(tenant.id),
        {
            "student_name": "Pooja Mehta",
            "phone": "9811122233",
            "email": "pooja@example.com",
            "status": "PENDING_DOCS",
        }
    )
    assert adm1.id is not None

    # Duplicate phone in admission
    with pytest.raises(ConflictError):
        await admission_service.create_admission(
            db_session,
            str(tenant.id),
            {
                "student_name": "Another Pooja",
                "phone": "9811122233",
                "email": "pooja2@example.com",
            }
        )


@pytest.mark.asyncio
async def test_duplicate_batch_validation(db_session, tenant):
    """Test that creating a batch with an existing name & academic_year raises ConflictError."""
    b1 = await batch_service.create_batch(
        db_session,
        str(tenant.id),
        {
            "name": "NEET Alpha 2026",
            "academic_year": "2026-27",
            "code": "NEET-A",
            "capacity": 40,
        }
    )
    assert b1.id is not None

    # Duplicate batch name + academic_year
    with pytest.raises(ConflictError):
        await batch_service.create_batch(
            db_session,
            str(tenant.id),
            {
                "name": "neet alpha 2026",  # Case insensitive
                "academic_year": "2026-27",
                "code": "NEET-A2",
                "capacity": 30,
            }
        )


@pytest.mark.asyncio
async def test_duplicate_subject_validation(db_session, tenant):
    """Test that creating a subject with an existing name raises ConflictError."""
    s1 = await batch_service.create_subject(
        db_session,
        str(tenant.id),
        {"name": "Organic Chemistry", "code": "CHEM-01"}
    )
    assert s1.id is not None

    with pytest.raises(ConflictError):
        await batch_service.create_subject(
            db_session,
            str(tenant.id),
            {"name": "organic chemistry", "code": "CHEM-02"}
        )


@pytest.mark.asyncio
async def test_duplicate_fee_structure_validation(db_session, tenant):
    """Test that creating a fee structure with an existing name raises ConflictError."""
    fs1 = await fee_service.create_fee_structure(
        db_session,
        str(tenant.id),
        {
            "name": "JEE Advanced Complete Course",
            "course": "JEE",
            "grade": "11th",
            "total_amount": 75000,
            "installments_count": 3,
        }
    )
    assert fs1.id is not None

    with pytest.raises(ConflictError):
        await fee_service.create_fee_structure(
            db_session,
            str(tenant.id),
            {
                "name": "jee advanced complete course",
                "course": "JEE",
                "grade": "12th",
                "total_amount": 80000,
                "installments_count": 2,
            }
        )


@pytest.mark.asyncio
async def test_duplicate_syllabus_topic_validation(db_session, tenant):
    """Test that creating a syllabus topic with an existing title for the same subject raises ConflictError."""
    sub = await batch_service.create_subject(
        db_session,
        str(tenant.id),
        {"name": "Subject For Syllabus", "code": "SUB-SYL"}
    )
    top1 = await batch_service.create_syllabus_topic(
        db_session,
        str(tenant.id),
        {"subject_id": sub.id, "title": "Thermodynamics"}
    )
    assert top1.id is not None

    with pytest.raises(ConflictError):
        await batch_service.create_syllabus_topic(
            db_session,
            str(tenant.id),
            {"subject_id": sub.id, "title": "thermodynamics"}
        )


@pytest.mark.asyncio
async def test_duplicate_auth_registration(db_session, tenant):
    """Test that registering a user with duplicate email or phone raises ConflictError."""
    u1 = await auth_service.register_user(
        db_session,
        str(tenant.id),
        {
            "email": "student_auth_dup@test.com",
            "phone": "9555444333",
            "first_name": "Auth",
            "last_name": "User",
            "password": "Password@123",
        }
    )
    assert u1.id is not None

    # Duplicate phone in user registration
    with pytest.raises(ConflictError):
        await auth_service.register_user(
            db_session,
            str(tenant.id),
            {
                "email": "different_email@test.com",
                "phone": "9555444333",
                "first_name": "Second",
                "last_name": "User",
                "password": "Password@123",
            }
        )
