import re
import uuid
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
from typing import Optional, Any
from datetime import date


def sanitize_phone(v: Optional[str]) -> Optional[str]:
    if v is None:
        return None
    v_clean = str(v).strip()
    if not v_clean:
        return None
    digits = re.sub(r"\D", "", v_clean)
    if len(digits) != 10:
        raise ValueError("Phone number must be exactly 10 digits.")
    return digits


def validate_pincode_format(v: Optional[str]) -> Optional[str]:
    if not v:
        return None
    v_clean = str(v).strip()
    if not re.match(r"^\d{5,10}$", v_clean):
        raise ValueError("Pincode must be between 5 and 10 digits.")
    return v_clean


class StudentCreate(BaseModel):
    enrollment_no: str = Field(min_length=1, max_length=50)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    blood_group: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    parent_name: Optional[str] = None
    parent_phone: Optional[str] = None
    parent_email: Optional[EmailStr] = None
    school_name: Optional[str] = None
    current_class: Optional[str] = None
    target_exam: Optional[str] = None
    subjects: list[str] = []
    custom_fields: Optional[dict] = Field(default_factory=dict)
    batch_id: Optional[uuid.UUID] = None
    joined_at: Optional[date] = None

    @field_validator("first_name", "last_name", "parent_name")
    @classmethod
    def validate_name_no_digits(cls, v: Optional[str]) -> Optional[str]:
        if v:
            v_clean = v.strip()
            if re.search(r"\d", v_clean):
                raise ValueError("Name cannot contain numbers.")
            return v_clean
        return v

    @field_validator("date_of_birth")
    @classmethod
    def validate_dob(cls, v: Optional[date]) -> Optional[date]:
        if v and v > date.today():
            raise ValueError("Date of birth cannot be in the future.")
        return v

    @field_validator("phone", "parent_phone", mode="before")
    @classmethod
    def validate_phone(cls, v: Any) -> Any:
        return sanitize_phone(v) if v else v

    @field_validator("pincode", mode="before")
    @classmethod
    def validate_pincode(cls, v: Any) -> Any:
        return validate_pincode_format(v) if v else v


class StudentUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    parent_name: Optional[str] = None
    parent_phone: Optional[str] = None
    parent_email: Optional[EmailStr] = None
    school_name: Optional[str] = None
    current_class: Optional[str] = None
    target_exam: Optional[str] = None
    subjects: Optional[list[str]] = None
    custom_fields: Optional[dict] = None
    is_active: Optional[bool] = None

    @field_validator("first_name", "last_name", "parent_name")
    @classmethod
    def validate_name_no_digits(cls, v: Optional[str]) -> Optional[str]:
        if v:
            v_clean = v.strip()
            if re.search(r"\d", v_clean):
                raise ValueError("Name cannot contain numbers.")
            return v_clean
        return v

    @field_validator("date_of_birth")
    @classmethod
    def validate_dob(cls, v: Optional[date]) -> Optional[date]:
        if v and v > date.today():
            raise ValueError("Date of birth cannot be in the future.")
        return v

    @field_validator("phone", "parent_phone", mode="before")
    @classmethod
    def validate_phone(cls, v: Any) -> Any:
        return sanitize_phone(v) if v else v

    @field_validator("pincode", mode="before")
    @classmethod
    def validate_pincode(cls, v: Any) -> Any:
        return validate_pincode_format(v) if v else v


class StudentOut(BaseModel):
    id: uuid.UUID
    enrollment_no: str
    first_name: str
    last_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    gender: Optional[str] = None
    date_of_birth: Optional[date] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    parent_name: Optional[str] = None
    parent_phone: Optional[str] = None
    parent_email: Optional[str] = None
    school_name: Optional[str] = None
    current_class: Optional[str] = None
    target_exam: Optional[str] = None
    subjects: list[str] = []
    custom_fields: Optional[dict] = Field(default_factory=dict)
    batch_ids: list[str] = []
    admission_id: Optional[uuid.UUID] = None
    joined_at: Optional[Any] = None
    is_active: bool

    @model_validator(mode="before")
    @classmethod
    def extract_batch_ids(cls, obj: Any) -> Any:
        if not isinstance(obj, dict):
            d = getattr(obj, "__dict__", {})
            batch_ids = []
            if "batch_enrollments" in d and d["batch_enrollments"]:
                try:
                    batch_ids = [str(e.batch_id) for e in d["batch_enrollments"]]
                except Exception:
                    batch_ids = []

            data = {
                "id":            getattr(obj, "id", None),
                "enrollment_no": getattr(obj, "enrollment_no", ""),
                "first_name":    getattr(obj, "first_name", ""),
                "last_name":     getattr(obj, "last_name", ""),
                "email":         getattr(obj, "email", None),
                "phone":         getattr(obj, "phone", None),
                "gender":        getattr(obj, "gender", None),
                "date_of_birth": getattr(obj, "date_of_birth", None),
                "address":       getattr(obj, "address", None),
                "city":          getattr(obj, "city", None),
                "state":         getattr(obj, "state", None),
                "pincode":       getattr(obj, "pincode", None),
                "parent_name":   getattr(obj, "parent_name", None),
                "parent_phone":  getattr(obj, "parent_phone", None),
                "parent_email":  getattr(obj, "parent_email", None),
                "school_name":   getattr(obj, "school_name", None),
                "current_class": getattr(obj, "current_class", None),
                "target_exam":   getattr(obj, "target_exam", None),
                "subjects":      getattr(obj, "subjects", []) or [],
                "custom_fields": getattr(obj, "custom_fields", {}) or {},
                "is_active":     getattr(obj, "is_active", True),
                "admission_id":  getattr(obj, "admission_id", None),
                "joined_at":     getattr(obj, "joined_at", None),
                "batch_ids":     batch_ids,
            }
            return data
        return obj

    class Config:
        from_attributes = True
