import re
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
from typing import Optional, List, Any
import uuid
from datetime import date, datetime

VALID_LEAD_STAGES = {
    "new", "contacted", "interested", "demo_scheduled", "demo_done",
    "negotiation", "enrolled", "lost", "converted"
}

VALID_LEAD_SOURCES = {
    "website", "walk_in", "walk-in", "referral", "social_media",
    "google_ads", "campaign", "other", "direct", "manual"
}


def sanitize_phone_number(v: Optional[str]) -> Optional[str]:
    if v is None:
        return None
    v_clean = str(v).strip()
    if not v_clean:
        return None
    digits = re.sub(r"\D", "", v_clean)
    if len(digits) != 10:
        raise ValueError("Phone number must be exactly 10 digits.")
    return digits


class LeadCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=150)
    phone: str
    email: Optional[EmailStr] = None
    parent_name: Optional[str] = None
    parent_phone: Optional[str] = None
    parent_contact_number: Optional[str] = None
    school_name: Optional[str] = None
    source: str = "website"
    status: Optional[str] = "new"
    interested_course: Optional[str] = None
    grade: Optional[str] = None
    notes: Optional[str] = None
    follow_up_date: Optional[date] = None
    assigned_to: Optional[uuid.UUID] = None
    board_name: Optional[str] = None
    batch_id: Optional[uuid.UUID] = None
    subjects: Optional[List[str]] = []
    custom_fields: Optional[dict] = Field(default_factory=dict)

    @field_validator("full_name", "parent_name")
    @classmethod
    def validate_name_no_digits(cls, v: Optional[str]) -> Optional[str]:
        if v:
            v_clean = v.strip()
            if re.search(r"\d", v_clean):
                raise ValueError("Name cannot contain numbers.")
            return v_clean
        return v

    @field_validator("phone", "parent_phone", "parent_contact_number", mode="before")
    @classmethod
    def validate_phone(cls, v: Any) -> Any:
        return sanitize_phone_number(v) if v else v

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, v: Any) -> Any:
        if v:
            v_norm = str(v).strip().lower()
            if v_norm in VALID_LEAD_STAGES:
                return v_norm
        return "new"

    @field_validator("source", mode="before")
    @classmethod
    def validate_source(cls, v: Any) -> Any:
        if v:
            v_norm = str(v).strip().lower().replace("-", "_")
            if v_norm in VALID_LEAD_SOURCES:
                return v_norm
        return "website"


class LeadUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    parent_name: Optional[str] = None
    parent_phone: Optional[str] = None
    parent_contact_number: Optional[str] = None
    school_name: Optional[str] = None
    source: Optional[str] = None
    status: Optional[str] = None
    interested_course: Optional[str] = None
    grade: Optional[str] = None
    notes: Optional[str] = None
    follow_up_date: Optional[date] = None
    assigned_to: Optional[uuid.UUID] = None
    board_name: Optional[str] = None
    batch_id: Optional[uuid.UUID] = None
    subjects: Optional[List[str]] = None
    custom_fields: Optional[dict] = None

    @field_validator("full_name", "parent_name")
    @classmethod
    def validate_name_no_digits(cls, v: Optional[str]) -> Optional[str]:
        if v:
            v_clean = v.strip()
            if re.search(r"\d", v_clean):
                raise ValueError("Name cannot contain numbers.")
            return v_clean
        return v

    @field_validator("phone", "parent_phone", "parent_contact_number", mode="before")
    @classmethod
    def validate_phone(cls, v: Any) -> Any:
        return sanitize_phone_number(v) if v else v

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, v: Any) -> Any:
        if v:
            v_norm = str(v).strip().lower()
            if v_norm in VALID_LEAD_STAGES:
                return v_norm
        return v


class ActivityCreate(BaseModel):
    type: str = "NOTE"
    description: Optional[str] = None
    content: Optional[str] = None
    created_by: Optional[str] = None


class ActivityOut(BaseModel):
    id: uuid.UUID
    lead_id: Optional[uuid.UUID] = None
    type: str
    description: str
    content: Optional[str] = None
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

    @model_validator(mode="before")
    @classmethod
    def extract_activity(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            d = getattr(data, "__dict__", {})
            user = d.get("user")
            creator = "Staff Counselor"
            if user:
                ud = getattr(user, "__dict__", {})
                first = ud.get("first_name", "") or ""
                last = ud.get("last_name", "") or ""
                name = f"{first} {last}".strip()
                creator = name if name else (ud.get("email", "") or "Staff Counselor")
            desc = d.get("description", "") or ""
            return {
                "id": d.get("id"),
                "lead_id": d.get("lead_id"),
                "type": d.get("type", "NOTE"),
                "description": desc,
                "content": desc,
                "created_by": creator,
                "created_at": d.get("created_at"),
            }
        desc = data.get("description") or data.get("content") or ""
        data["description"] = desc
        if "content" not in data or not data["content"]:
            data["content"] = desc
        return data


class LeadOut(BaseModel):
    id: uuid.UUID
    full_name: str
    phone: str
    email: Optional[str] = None
    parent_name: Optional[str] = None
    parent_phone: Optional[str] = None
    parent_contact_number: Optional[str] = None
    school_name: Optional[str] = None
    source: str
    status: str
    interested_course: Optional[str] = None
    grade: Optional[str] = None
    follow_up_date: Optional[date] = None
    notes: Optional[str] = None
    board_name: Optional[str] = None
    batch_id: Optional[uuid.UUID] = None
    batch_name: Optional[str] = None
    subjects: Optional[List[str]] = []
    custom_fields: Optional[dict] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    activities: Optional[List[ActivityOut]] = []

    class Config:
        from_attributes = True

    @model_validator(mode="before")
    @classmethod
    def extract_lead(cls, obj: Any) -> Any:
        if not isinstance(obj, dict):
            d = getattr(obj, "__dict__", {})
            acts = []
            if "activities" in d and d["activities"]:
                try:
                    acts = [ActivityOut.model_validate(a) for a in d["activities"]]
                except Exception:
                    acts = []

            return {
                "id": d.get("id"),
                "full_name": d.get("full_name", ""),
                "phone": d.get("phone", ""),
                "email": d.get("email"),
                "parent_name": d.get("parent_name"),
                "parent_phone": d.get("parent_phone"),
                "parent_contact_number": d.get("parent_contact_number"),
                "school_name": d.get("school_name"),
                "source": d.get("source", "website"),
                "status": d.get("status", "new"),
                "interested_course": d.get("interested_course"),
                "grade": d.get("grade"),
                "follow_up_date": d.get("follow_up_date"),
                "notes": d.get("notes"),
                "board_name": d.get("board_name"),
                "batch_id": d.get("batch_id"),
                "batch_name": d.get("batch_name"),
                "subjects": d.get("subjects") or [],
                "custom_fields": d.get("custom_fields") or {},
                "activities": acts,
            }
        return obj


class PipelineStageConfig(BaseModel):
    id: str = Field(..., pattern="^[a-z0-9_]{2,30}$", description="Unique lowercase identifier for stage")
    label: str = Field(..., min_length=2, max_length=50)
    order: int = Field(..., ge=1, le=50)
    is_system: bool = False


class RequiredDocumentConfig(BaseModel):
    id: str = Field(..., pattern="^[a-z0-9_]{2,30}$")
    name: str = Field(..., min_length=2, max_length=100)
    mandatory: bool = False


class CRMPipelineConfig(BaseModel):
    stages: List[PipelineStageConfig] = []
    required_documents: List[RequiredDocumentConfig] = []

    @field_validator("stages")
    @classmethod
    def validate_unique_stages(cls, v: List[PipelineStageConfig]) -> List[PipelineStageConfig]:
        ids = set()
        orders = set()
        has_new = False
        for s in v:
            if s.id in ids:
                raise ValueError(f"Duplicate stage ID '{s.id}' found in pipeline configuration.")
            if s.order in orders:
                raise ValueError(f"Duplicate stage order '{s.order}' found in pipeline configuration.")
            ids.add(s.id)
            orders.add(s.order)
            if s.id == "new":
                has_new = True
        if not has_new:
            raise ValueError("Pipeline configuration must contain the default initial stage 'new'.")
        return v