from decimal import Decimal, ROUND_FLOOR, ROUND_HALF_UP
from datetime import date, datetime, timedelta
from typing import List, Dict, Any, Optional
import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models.fee import FeeInvoice, FeePayment, FeeInstallment
from app.models.student import Student
from app.models.tenant import Tenant
from app.utils.exceptions import NotFoundError, ConflictError


def to_decimal(val: Any) -> Decimal:
    """Safely convert any numeric input to 2-decimal-place Decimal."""
    if val is None:
        return Decimal("0.00")
    if isinstance(val, Decimal):
        return val.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return Decimal(str(val)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_installment_schedule(
    total_amount: Any,
    installments_count: int = 1,
    start_date: Optional[date] = None,
    frequency: str = "monthly",
    discount: Any = 0,
    scholarship: Any = 0,
) -> List[Dict[str, Any]]:
    """
    Deterministic & exact Decimal installment calculator.
    Guarantees:
    1. Zero binary floating-point rounding errors.
    2. Final installment absorbs fractional paise/cent remainder.
    3. SUM(installments) == net_amount_due exactly.
    """
    gross_amount = to_decimal(total_amount)
    disc_amount = to_decimal(discount)
    schol_amount = to_decimal(scholarship)

    if gross_amount < Decimal("0.00"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Total fee amount cannot be negative.",
        )
    if disc_amount < Decimal("0.00") or schol_amount < Decimal("0.00"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Discounts and scholarships cannot be negative.",
        )

    net_amount_due = gross_amount - disc_amount - schol_amount
    if net_amount_due < Decimal("0.00"):
        net_amount_due = Decimal("0.00")

    if installments_count < 1:
        installments_count = 1

    if not start_date:
        start_date = date.today()

    if installments_count == 1:
        return [
            {
                "installment_no": 1,
                "title": "Full Fee Payment",
                "amount_due": float(net_amount_due),
                "due_date": start_date,
                "status": "pending" if net_amount_due > 0 else "paid",
            }
        ]

    # Equal split with remainder absorbed into the final installment
    n = Decimal(str(installments_count))
    base_installment = (net_amount_due / n).quantize(Decimal("0.01"), rounding=ROUND_FLOOR)
    allocated_so_far = base_installment * Decimal(str(installments_count - 1))
    final_installment = net_amount_due - allocated_so_far

    schedule = []
    current_due_date = start_date

    for i in range(1, installments_count + 1):
        if i == installments_count:
            inst_amount = final_installment
        else:
            inst_amount = base_installment

        title = f"Installment {i} of {installments_count}"

        schedule.append(
            {
                "installment_no": i,
                "title": title,
                "amount_due": float(inst_amount),
                "due_date": current_due_date,
                "status": "pending" if inst_amount > 0 else "paid",
            }
        )

        # Advance due date based on frequency
        if frequency == "quarterly":
            # Roughly 3 months
            year = current_due_date.year + (current_due_date.month + 3 - 1) // 12
            month = (current_due_date.month + 3 - 1) % 12 + 1
            day = min(current_due_date.day, 28)
            current_due_date = date(year, month, day)
        else:
            # Default monthly: advance 1 month
            year = current_due_date.year + (current_due_date.month + 1 - 1) // 12
            month = (current_due_date.month + 1 - 1) % 12 + 1
            day = min(current_due_date.day, 28)
            current_due_date = date(year, month, day)

    # Verification: Reconciles exactly to net_amount_due
    total_scheduled = sum(Decimal(str(item["amount_due"])) for item in schedule)
    if total_scheduled != net_amount_due:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Financial reconciliation error: scheduled sum ({total_scheduled}) does not match net due ({net_amount_due}).",
        )

    return schedule


async def create_invoice_installments(
    db: AsyncSession,
    tenant_id: uuid.UUID | str,
    invoice: FeeInvoice,
    installment_specs: List[Dict[str, Any]],
) -> List[FeeInstallment]:
    """Persist normalized relational installment rows for an invoice."""
    t_uuid = uuid.UUID(str(tenant_id)) if isinstance(tenant_id, (str, uuid.UUID)) else tenant_id
    installments = []

    for spec in installment_specs:
        inst = FeeInstallment(
            id=uuid.uuid4(),
            tenant_id=t_uuid,
            invoice_id=invoice.id,
            student_id=invoice.student_id,
            installment_no=spec["installment_no"],
            title=spec["title"],
            amount_due=spec["amount_due"],
            amount_paid=spec.get("amount_paid", 0.0),
            due_date=spec["due_date"] if isinstance(spec["due_date"], date) else date.fromisoformat(str(spec["due_date"])),
            status=spec.get("status", "pending"),
        )
        db.add(inst)
        installments.append(inst)

    await db.flush()
    return installments


async def sync_payment_to_installments(
    db: AsyncSession,
    invoice: FeeInvoice,
    payment_amount: Any,
) -> None:
    """
    Sequentially allocate a collected payment to relational installments.
    Guarantees:
    1. Earliest pending installment gets paid first.
    2. Overpayments / negative balances prevented.
    3. Installment statuses correctly reflect 'paid', 'partial', 'pending'.
    """
    remaining_payment = to_decimal(payment_amount)
    if remaining_payment <= Decimal("0.00"):
        return

    # Fetch ordered installments for this invoice
    stmt = (
        select(FeeInstallment)
        .where(FeeInstallment.invoice_id == invoice.id)
        .order_by(FeeInstallment.installment_no.asc())
    )
    result = await db.execute(stmt)
    installments = list(result.scalars().all())

    if not installments:
        # If no relational installments exist, create 1 default installment
        default_inst = FeeInstallment(
            id=uuid.uuid4(),
            tenant_id=invoice.tenant_id,
            invoice_id=invoice.id,
            student_id=invoice.student_id,
            installment_no=1,
            title="Invoice Full Payment",
            amount_due=invoice.amount_due,
            amount_paid=0.0,
            due_date=invoice.due_date,
            status="pending",
        )
        db.add(default_inst)
        await db.flush()
        installments = [default_inst]

    for inst in installments:
        if remaining_payment <= Decimal("0.00"):
            break

        inst_due = to_decimal(inst.amount_due)
        inst_paid = to_decimal(inst.amount_paid)
        inst_outstanding = inst_due - inst_paid

        if inst_outstanding > Decimal("0.00"):
            allocation = min(remaining_payment, inst_outstanding)
            new_inst_paid = inst_paid + allocation
            inst.amount_paid = float(new_inst_paid)
            remaining_payment -= allocation

            if new_inst_paid >= inst_due:
                inst.status = "paid"
            elif new_inst_paid > Decimal("0.00"):
                inst.status = "partial"
            else:
                inst.status = "pending"

    await db.flush()
