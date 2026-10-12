from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, List, Any
from datetime import date, datetime
import uuid


class SubjectCreate(BaseModel):
    name: str
    code: Optional[str] = None
    description: Optional[str] = None


class SubjectOut(BaseModel):
    id: uuid.UUID
    name: str
    code: Optional[str] = None

    class Config:
        from_attributes = True


# ── Syllabus Topic ─────────────────────────────────────────────
class SyllabusTopicCreate(BaseModel):
    subject_id: uuid.UUID
    title: str
    description: Optional[str] = None
    sort_order: Optional[int] = 0
    parent_id: Optional[uuid.UUID] = None


class SyllabusTopicUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    sort_order: Optional[int] = None


class SyllabusTopicOut(BaseModel):
    id: uuid.UUID
    title: str
    description: Optional[str] = None
    sort_order: int = 0

    class Config:
        from_attributes = True


# ── Syllabus Progress ──────────────────────────────────────────
class SyllabusProgressUpdate(BaseModel):
    status: str   # "not_started" | "in_progress" | "completed"
    notes: Optional[str] = None


class SyllabusTopicWithProgress(BaseModel):
    id: uuid.UUID
    title: str
    description: Optional[str] = None
    sort_order: int = 0
    status: str = "not_started"
    notes: Optional[str] = None
    completed_at: Optional[str] = None
    progress_id: Optional[uuid.UUID] = None


# ── Schedule slot (used inside BatchCreate/BatchOut) ───────────
class ScheduleSlot(BaseModel):
    """One recurring weekly slot for a batch."""
    day: str                        # "Monday" | "Tuesday" … | "Saturday" | "Sunday"
    start_time: str                 # "09:00"  (HH:MM, 24-hr)
    end_time: str                   # "10:30"
    room_or_link: Optional[str] = None   # physical room or online link


# ── Batch ──────────────────────────────────────────────────────
class BatchCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    code: Optional[str] = None
    description: Optional[str] = None
    target_exam: Optional[str] = None
    academic_year: str = Field(min_length=1, max_length=20)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    capacity: int = Field(default=50, ge=1, le=2000, description="Capacity must be between 1 and 2000")
    status: Optional[str] = "ACTIVE"
    schedule: Optional[List[ScheduleSlot]] = None
    subjects: Optional[List[str]] = []
    custom_fields: Optional[dict] = Field(default_factory=dict)

    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def empty_str_to_none(cls, v: Any) -> Any:
        """Convert empty string "" to None so optional dates work cleanly."""
        if v == "":
            return None
        return v

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, v: Any) -> Any:
        if v is not None:
            v_upper = str(v).upper().strip()
            if v_upper not in {"ACTIVE", "UPCOMING", "COMPLETED"}:
                raise ValueError("status must be one of: 'ACTIVE', 'UPCOMING', 'COMPLETED'")
            return v_upper
        return "ACTIVE"

    @model_validator(mode="after")
    def validate_date_range(self):
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError(f"End date ({self.end_date}) cannot be earlier than start date ({self.start_date})")
        return self


class BatchUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    academic_year: Optional[str] = None
    description: Optional[str] = None
    target_exam: Optional[str] = None
    capacity: Optional[int] = Field(default=None, ge=1, le=2000)
    status: Optional[str] = None
    is_active: Optional[bool] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    schedule: Optional[List[ScheduleSlot]] = None
    subjects: Optional[List[str]] = None
    custom_fields: Optional[dict] = None

    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def empty_str_to_none(cls, v: Any) -> Any:
        if v == "":
            return None
        return v

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, v: Any) -> Any:
        if v is not None:
            v_upper = str(v).upper().strip()
            if v_upper not in {"ACTIVE", "UPCOMING", "COMPLETED"}:
                raise ValueError("status must be one of: 'ACTIVE', 'UPCOMING', 'COMPLETED'")
            return v_upper
        return v

    @model_validator(mode="after")
    def validate_date_range(self):
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError(f"End date ({self.end_date}) cannot be earlier than start date ({self.start_date})")
        return self


class BatchOut(BaseModel):
    id: uuid.UUID
    name: str
    code: Optional[str] = None
    target_exam: Optional[str] = None
    academic_year: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    capacity: int
    is_active: bool
    status: Optional[str] = "ACTIVE"
    student_ids: List[str] = []
    schedule: Optional[List[ScheduleSlot]] = None
    subjects: Optional[List[str]] = []
    custom_fields: Optional[dict] = Field(default_factory=dict)

    class Config:
        from_attributes = True

# ── Class ──────────────────────────────────────────────────────
class ClassCreate(BaseModel):
    batch_id: uuid.UUID
    subject_id: Optional[uuid.UUID] = None
    tutor_id: Optional[uuid.UUID] = None
    title: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None
    scheduled_at: datetime
    duration_min: int = Field(default=60, ge=15, le=720, description="Duration in minutes (15-720)")
    room_or_link: Optional[str] = None


class ClassUpdate(BaseModel):
    title: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    duration_min: Optional[int] = Field(default=None, ge=15, le=720)
    room_or_link: Optional[str] = None
    status: Optional[str] = None


class ClassOut(BaseModel):
    id: uuid.UUID
    title: str
    # scheduled_at: str
    scheduled_at: datetime
    duration_min: int
    status: str
    room_or_link: Optional[str] = None

    class Config:
        from_attributes = True