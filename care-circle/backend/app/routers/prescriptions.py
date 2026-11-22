"""Prescriptions and the refill tracker."""
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.access import get_membership, log_activity, require_write
from app.database import get_db
from app.deps import CurrentUser
from app.models import Prescription, utcnow
from app.schemas import (
    PrescriptionCreate,
    PrescriptionOut,
    PrescriptionUpdate,
    RefillItem,
    model_dump_set,
)

router = APIRouter(prefix="/care-recipients/{care_recipient_id}/prescriptions", tags=["prescriptions"])


def build_refill_items(db: Session, care_recipient_id: int, days: int) -> list[RefillItem]:
    """Prescriptions due for refill within `days` (or overdue), plus those with no refills left."""
    today = date.today()
    horizon = today + timedelta(days=days)
    rows = db.scalars(select(Prescription).where(Prescription.care_recipient_id == care_recipient_id)).all()
    items: list[RefillItem] = []
    for p in rows:
        flags: list[str] = []
        days_until = None
        if p.refill_due_date is not None:
            days_until = (p.refill_due_date - today).days
            if p.refill_due_date < today:
                flags.append("overdue")
            elif p.refill_due_date <= horizon:
                flags.append("due_soon")
        if p.refills_remaining == 0:
            flags.append("no_refills_left")
        if flags:
            items.append(RefillItem(prescription=PrescriptionOut.model_validate(p),
                                    days_until_refill=days_until, flags=flags))
    return sorted(items, key=lambda i: (i.days_until_refill is None, i.days_until_refill or 0))


def _get_item(db: Session, care_recipient_id: int, item_id: int) -> Prescription:
    item = db.get(Prescription, item_id)
    if item is None or item.care_recipient_id != care_recipient_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Prescription not found")
    return item


@router.get("", response_model=list[PrescriptionOut])
def list_prescriptions(care_recipient_id: int, user: CurrentUser, db: Session = Depends(get_db)) -> list[Prescription]:
    get_membership(db, user.id, care_recipient_id)
    return list(db.scalars(
        select(Prescription).where(Prescription.care_recipient_id == care_recipient_id).order_by(Prescription.start_date.desc())
    ).all())


@router.post("", response_model=PrescriptionOut, status_code=status.HTTP_201_CREATED)
def create_prescription(care_recipient_id: int, body: PrescriptionCreate, user: CurrentUser, db: Session = Depends(get_db)) -> Prescription:
    require_write(get_membership(db, user.id, care_recipient_id))
    item = Prescription(care_recipient_id=care_recipient_id, created_by_id=user.id, **body.model_dump())
    db.add(item)
    db.flush()
    log_activity(db, care_recipient_id, user.id, "create", "prescription", item.id,
                 f"{user.full_name} added prescription '{item.medicine_name}'")
    db.commit()
    db.refresh(item)
    return item


@router.patch("/{item_id}", response_model=PrescriptionOut)
def update_prescription(care_recipient_id: int, item_id: int, body: PrescriptionUpdate, user: CurrentUser, db: Session = Depends(get_db)) -> Prescription:
    require_write(get_membership(db, user.id, care_recipient_id))
    item = _get_item(db, care_recipient_id, item_id)
    changes = model_dump_set(body)
    # Re-validate the merged record so cross-field rules (end before start) still hold.
    merged = {c: getattr(item, c) for c in PrescriptionCreate.model_fields} | changes
    try:
        PrescriptionCreate.model_validate(merged)
    except ValidationError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, exc.errors()[0]["msg"])
    for field, value in changes.items():
        setattr(item, field, value)
    item.updated_at = utcnow()
    if "refills_remaining" in changes or "refill_due_date" in changes:
        summary = f"{user.full_name} updated refill details for '{item.medicine_name}'"
    else:
        summary = f"{user.full_name} updated prescription '{item.medicine_name}'"
    log_activity(db, care_recipient_id, user.id, "update", "prescription", item.id, summary)
    db.commit()
    db.refresh(item)
    return item


@router.get("/refills", response_model=list[RefillItem])
def refills_due(
    care_recipient_id: int,
    user: CurrentUser,
    db: Session = Depends(get_db),
    days: int = Query(14, ge=0, le=365),
) -> list[RefillItem]:
    get_membership(db, user.id, care_recipient_id)
    return build_refill_items(db, care_recipient_id, days)
