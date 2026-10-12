# from pydantic import BaseModel
# from typing import Optional
# import uuid


# class FeeStructureCreate(BaseModel):
#     batch_id: Optional[uuid.UUID] = None
#     name: str
#     total_amount: float
#     installments: int = 1
#     description: Optional[str] = None


# class FeeInvoiceCreate(BaseModel):
#     student_id: uuid.UUID
#     fee_structure_id: Optional[uuid.UUID] = None
#     invoice_no: str
#     amount_due: float
#     discount: float = 0
#     due_date: str


# class FeeInvoiceOut(BaseModel):
#     id: uuid.UUID
#     invoice_no: str
#     amount_due: float
#     amount_paid: float
#     discount: float
#     due_date: str
#     status: str

#     class Config:
#         from_attributes = True


# class PaymentCreate(BaseModel):
#     amount: float
#     payment_mode: str = "cash"
#     transaction_ref: Optional[str] = None
#     notes: Optional[str] = None


# class PaymentOut(BaseModel):
#     id: uuid.UUID
#     amount: float
#     payment_mode: str
#     transaction_ref: Optional[str] = None

#     class Config:
#         from_attributes = True

import uuid
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import date, datetime


class FeeStructureCreate(BaseModel):
    batch_id: Optional[uuid.UUID] = None
    name: str = Field(min_length=1, max_length=150)
    total_amount: float = Field(gt=0, description="Total amount must be greater than 0")
    installments: int = Field(default=1, ge=1, le=24, description="Installments must be between 1 and 24")
    description: Optional[str] = None


class FeeInvoiceCreate(BaseModel):
    student_id: uuid.UUID
    fee_structure_id: Optional[uuid.UUID] = None
    invoice_no: str = Field(min_length=1, max_length=50)
    amount_due: float = Field(gt=0, description="Amount due must be greater than 0")
    discount: float = Field(default=0, ge=0, description="Discount cannot be negative")
    due_date: str


class PaymentCreate(BaseModel):
    amount: float = Field(gt=0, description="Payment amount must be greater than 0")
    payment_mode: str = "cash"
    transaction_ref: Optional[str] = None
    notes: Optional[str] = None


class PaymentOut(BaseModel):
    id:               uuid.UUID
    amount:           float
    payment_mode:     str
    transaction_ref:  Optional[str] = None
    model_config = {"from_attributes": True}
    paid_at:          Optional[datetime] = None   # ✅ add
    created_at:       Optional[datetime] = None


class FeeInvoiceOut(BaseModel):
    id:           uuid.UUID
    invoice_no:   str
    student_id:   uuid.UUID
    amount_due:   float
    amount_paid:  float
    discount:     float
    due_date:     date
    status:       str
    created_at:   Optional[datetime] = None

    # Flattened from student relationship
    student_name:  Optional[str] = None
    grade:         Optional[str] = None
    admission_id:  Optional[uuid.UUID] = None

    # Installment schedule inherited from linked admission
    payment_installment_schedule: Optional[str] = None

    # Payment history ledger list
    payments: list[PaymentOut] = []
    installments: list["FeeInstallmentOut"] = []

    model_config = {"from_attributes": True}

    @classmethod
    def model_validate(cls, obj, *args, **kwargs):
        instance = super().model_validate(obj, *args, **kwargs)
        # Flatten student name from relationship if present
        if hasattr(obj, "student") and obj.student:
            s = obj.student
            first = getattr(s, "first_name", "") or ""
            last  = getattr(s, "last_name",  "") or ""
            instance.student_name = f"{first} {last}".strip() or None
            instance.grade        = getattr(s, "current_class", None)
            if getattr(s, "admission_id", None):
                instance.admission_id = s.admission_id
            # Pull installment schedule from student's linked admission
            admission = getattr(s, "admission", None)
            if admission:
                instance.admission_id = admission.id
                if getattr(admission, "payment_installment_schedule", None):
                    instance.payment_installment_schedule = admission.payment_installment_schedule
        if hasattr(obj, "payments"):
            try:
                payments_val = getattr(obj, "payments", None)
                if payments_val:
                    instance.payments = [PaymentOut.model_validate(p) for p in payments_val]
            except Exception:
                pass
        if hasattr(obj, "installments"):
            try:
                inst_val = getattr(obj, "installments", None)
                if inst_val:
                    instance.installments = [FeeInstallmentOut.model_validate(inst) for inst in inst_val]
            except Exception:
                pass
        return instance


class FeeInstallmentOut(BaseModel):
    id: uuid.UUID
    installment_no: int
    title: str
    amount_due: float
    amount_paid: float
    due_date: date
    status: str
    model_config = {"from_attributes": True}


class ReceiptOut(BaseModel):
    receipt_no: str
    payment_id: uuid.UUID
    invoice_id: uuid.UUID
    invoice_no: str
    student_id: uuid.UUID
    student_name: str
    enrollment_no: Optional[str] = None
    grade: Optional[str] = None
    amount_paid: float
    payment_mode: str
    transaction_ref: Optional[str] = None
    paid_at: datetime
    notes: Optional[str] = None
    total_amount_due: float
    total_amount_paid: float
    balance_remaining: float
    institute_name: str
    institute_subdomain: str
    institute_phone: Optional[str] = None
    institute_email: Optional[str] = None
    institute_address: Optional[str] = None
    gstin: Optional[str] = None