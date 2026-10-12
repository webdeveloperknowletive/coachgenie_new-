
import json
import re
import uuid
from pydantic import BaseModel, Field, model_validator, field_validator
from typing import Optional, List, Any


# ─── Nested payment / installment types ───────────────────────────────────────

class InstallmentIn(BaseModel):
    number:  int
    amount:  float
    dueDate: Optional[str] = None
    paid:    bool = False


class PaymentIn(BaseModel):
    totalFee:             float = 0
    amountPaid:           float = 0
    remaining:            float = 0
    paymentStatus:        str   = "PENDING"
    dateOfPayment:        Optional[str] = None
    modeOfPayment:        str   = "upi"
    hasInstallments:      bool  = False
    numberOfInstallments: int   = 0
    installmentAmount:    float = 0
    installmentSchedule:  List[InstallmentIn] = []
    notes:                str   = ""

    @model_validator(mode="after")
    def validate_payment_math(self):
        self.totalFee = max(0.0, float(self.totalFee or 0))
        self.amountPaid = max(0.0, float(self.amountPaid or 0))
        if self.totalFee > 0 and self.amountPaid > self.totalFee:
            raise ValueError(f"Amount paid ({self.amountPaid}) cannot exceed total fee ({self.totalFee})")
        self.remaining = max(0.0, self.totalFee - self.amountPaid)
        if self.totalFee > 0:
            if self.amountPaid >= self.totalFee:
                self.paymentStatus = "PAID"
            elif self.amountPaid > 0:
                self.paymentStatus = "PARTIAL"
            else:
                self.paymentStatus = "PENDING"
        return self


class DocumentIn(BaseModel):
    name:      str
    required:  bool = True
    submitted: bool = False


# ─── Request schemas ───────────────────────────────────────────────────────────

class AdmissionCreate(BaseModel):
    # Legacy / internal fields
    lead_id:        Optional[uuid.UUID] = None
    academic_year:  Optional[str]       = None
    remarks:        Optional[str]       = None

    # Frontend form fields
    student_name:   Optional[str]       = None
    batchName:      Optional[str]       = None   # maps → applied_course
    applied_course: Optional[str]       = None
    grade:          Optional[str]       = None
    board_name:     Optional[str]       = None   # ← ADD
    batch_name:     Optional[str]       = None   # ← ADD
    batch_id:       Optional[uuid.UUID] = None
    subjects:       Optional[List[str]] = None
    status:         Optional[str]       = "PENDING_DOCS"
    phone:        Optional[str] = None
    email:        Optional[str] = None
    parent_name:  Optional[str] = None
    parent_phone: Optional[str] = None
    school_name:  Optional[str] = None

    # Fee quick-access
    fee_amount: Optional[float] = 0
    fee_paid:   Optional[float] = 0

    # Payment object from frontend
    payment:   Optional[PaymentIn]      = None

    # Documents list from frontend
    documents: Optional[List[DocumentIn]] = []
    custom_fields: Optional[dict] = Field(default_factory=dict)

    documents_verified: bool = False

    @field_validator("student_name", "parent_name")
    @classmethod
    def validate_name_no_digits(cls, v: Optional[str]) -> Optional[str]:
        if v:
            v_clean = v.strip()
            if re.search(r"\d", v_clean):
                raise ValueError("Name cannot contain numbers.")
            return v_clean
        return v

    @field_validator("phone", "parent_phone", mode="before")
    @classmethod
    def validate_phone(cls, v: Any) -> Any:
        if v is None:
            return None
        v_clean = str(v).strip()
        if not v_clean:
            return None
        digits = re.sub(r"\D", "", v_clean)
        if len(digits) != 10:
            raise ValueError("Phone number must be exactly 10 digits.")
        return digits

    @model_validator(mode="after")
    def resolve_applied_course(self):
        if not self.applied_course and self.batchName:
            self.applied_course = self.batchName
        if not self.applied_course:
            self.applied_course = "N/A"
        return self


class AdmissionUpdate(BaseModel):
    status:             Optional[str]             = None
    documents_verified: Optional[bool]            = None
    remarks:            Optional[str]             = None
    applied_course:     Optional[str]             = None
    # FIX: also accept camelCase aliases that the frontend sends
    batchName:          Optional[str]             = None   # alias → applied_course
    student_name:       Optional[str]             = None
    studentName:        Optional[str]             = None   # alias → student_name
    grade:              Optional[str]             = None
    board_name:     Optional[str]        = None   # ← ADD
    batch_name:     Optional[str]        = None   # ← ADD
    batch_id:       Optional[uuid.UUID]  = None
    batch_id:       Optional[uuid.UUID] = None
    subjects:           Optional[List[str]]       = None
    fee_amount:         Optional[float]           = None
    fee_paid:           Optional[float]           = None
    payment:            Optional[PaymentIn]       = None
    documents:          Optional[List[DocumentIn]] = None
    # FIX: was `enrolled_at` (snake) but service field_map keyed on `enrolledAt` (camel).
    # Accept both so either frontend convention works.
    enrolledAt:         Optional[str]             = None
    enrolled_at:        Optional[str]             = None
       # ── NEW: contact fields ──
    phone:        Optional[str] = None
    email:        Optional[str] = None
    parent_name:  Optional[str] = None
    parent_phone: Optional[str] = None
    school_name:  Optional[str] = None
    custom_fields: Optional[dict] = None


    @model_validator(mode="after")
    def normalise_aliases(self):
        """Resolve camelCase aliases to their canonical snake_case equivalents."""
        if not self.applied_course and self.batchName:
            self.applied_course = self.batchName
        if not self.student_name and self.studentName:
            self.student_name = self.studentName
        # Prefer camelCase value if both supplied (frontend usually sends camelCase)
        if not self.enrolledAt and self.enrolled_at:
            self.enrolledAt = self.enrolled_at
        return self


# ─── Response schemas ──────────────────────────────────────────────────────────

class InstallmentOut(BaseModel):
    number:  int
    amount:  float
    dueDate: Optional[str] = None
    due_date: Optional[str] = None   # kept for any consumer that reads snake_case
    paid:    bool = False
    overdue: bool = False


class PaymentOut(BaseModel):
    totalFee:             float = 0
    amountPaid:           float = 0
    remaining:            float = 0
    paymentStatus:        str   = "PENDING"
    dateOfPayment:        Optional[str] = None
    modeOfPayment:        str   = "upi"
    hasInstallments:      bool  = False
    numberOfInstallments: int   = 0
    installmentAmount:    float = 0
    installmentSchedule:  List[InstallmentOut] = []
    notes:                str   = ""


class DocumentOut(BaseModel):
    name:      str
    required:  bool
    submitted: bool


class AdmissionOut(BaseModel):
    id:                 uuid.UUID
    admission_number:   str
    academic_year:      str
    applied_course:     str
    status:             str
    documents_verified: bool
    remarks:            Optional[str]        = None
    approved_at:        Optional[Any]        = None
    lead_id:            Optional[uuid.UUID]  = None

    # Extended fields
    student_name:  Optional[str]        = None
    grade:         Optional[str]        = None
    board_name:     Optional[str]        = None   # ← ADD
    batch_name:     Optional[str]        = None   # ← ADD
    batch_id:       Optional[uuid.UUID]  = None
    subjects:      Optional[List[str]]  = None
    fee_amount:    Optional[float]      = None
    fee_paid:      Optional[float]      = None
    documents:     List[DocumentOut]    = []
    payment:       Optional[PaymentOut] = None
    custom_fields: Optional[dict]       = Field(default_factory=dict)

    created_at: Optional[Any] = None
       # ── NEW: contact fields ──
    phone:        Optional[str] = None
    email:        Optional[str] = None
    parent_name:  Optional[str] = None
    parent_phone: Optional[str] = None
    school_name:  Optional[str] = None


    model_config = {"from_attributes": True}

    @classmethod
    def model_validate(cls, obj, **kwargs):
        """
        Parse payment_installment_schedule (raw JSON text on the ORM row) into a
        PaymentOut object and attach it before returning.

        FIX: The previous implementation used a fragile two-step trick:
          1. Let pydantic build the instance (payment=None).
          2. Inject _payment_raw via object.__setattr__.
          3. Call parse_payment_json() explicitly again.
        This caused the validator to run twice and silently swallow errors.

        New approach: extract the raw string BEFORE calling super(), build the
        PaymentOut directly, and pass it in via `update` so pydantic sees it on
        the first (and only) pass.
        """
        # Grab raw JSON from ORM object before pydantic touches it
        raw: str | None = getattr(obj, "payment_installment_schedule", None)
        payment_out: PaymentOut | None = None

        if raw:
            try:
                data = json.loads(raw) if isinstance(raw, str) else raw
                schedule = [
                    InstallmentOut(
                        number=s.get("number", 0),
                        amount=s.get("amount", 0),
                        dueDate=s.get("dueDate") or s.get("due_date"),
                        due_date=s.get("due_date") or s.get("dueDate"),
                        paid=s.get("paid", False),
                        overdue=s.get("overdue", False),
                    )
                    for s in data.get("installmentSchedule", [])
                ]
                payment_out = PaymentOut(
                    totalFee=data.get("totalFee", 0),
                    amountPaid=data.get("amountPaid", 0),
                    remaining=data.get("remaining", 0),
                    paymentStatus=data.get("paymentStatus", "PENDING"),
                    dateOfPayment=data.get("dateOfPayment"),
                    modeOfPayment=data.get("modeOfPayment", "upi"),
                    hasInstallments=data.get("hasInstallments", False),
                    numberOfInstallments=data.get("numberOfInstallments", 0),
                    installmentAmount=data.get("installmentAmount", 0),
                    installmentSchedule=schedule,
                    notes=data.get("notes", ""),
                )
            except Exception:
                pass  # malformed JSON — leave payment as None

        instance = super().model_validate(obj, **kwargs)

        # Only set if pydantic didn't already get a payment value
        if payment_out and instance.payment is None:
            instance.payment = payment_out

        return instance