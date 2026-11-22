"""Appointments: list (with ?status= filter), create, update, delete."""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.access import ensure_member_user, get_membership, log_activity, require_write
from app.database import get_db
from app.deps import CurrentUser
from app.models import Appointment
from app.schemas import AppointmentCreate, AppointmentOut, AppointmentUpdate, model_dump_set
from app.models import utcnow

router = APIRouter(prefix="/care-recipients/{care_recipient_id}/appointments", tags=["appointments"])


def _get_item(db: Session, care_recipient_id: int, item_id: int) -> Appointment:
    item = db.get(Appointment, item_id)
    if item is None or item.care_recipient_id != care_recipient_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Appointment not found")
    return item


@router.get("", response_model=list[AppointmentOut])
def list_appointments(
    care_recipient_id: int,
    user: CurrentUser,
    db: Session = Depends(get_db),
    status_filter: Literal["scheduled", "completed", "cancelled"] | None = Query(None, alias="status"),
) -> list[Appointment]:
    get_membership(db, user.id, care_recipient_id)
    stmt = select(Appointment).where(Appointment.care_recipient_id == care_recipient_id)
    if status_filter:
        stmt = stmt.where(Appointment.status == status_filter)
    return list(db.scalars(stmt.order_by(Appointment.scheduled_at)).all())


@router.post("", response_model=AppointmentOut, status_code=status.HTTP_201_CREATED)
def create_appointment(care_recipient_id: int, body: AppointmentCreate, user: CurrentUser, db: Session = Depends(get_db)) -> Appointment:
    require_write(get_membership(db, user.id, care_recipient_id))
    ensure_member_user(db, care_recipient_id, body.assigned_to_id)
    item = Appointment(care_recipient_id=care_recipient_id, created_by_id=user.id, **body.model_dump())
    db.add(item)
    db.flush()
    log_activity(db, care_recipient_id, user.id, "create", "appointment", item.id,
                 f"{user.full_name} scheduled '{item.title}' on {item.scheduled_at:%d %b %Y %H:%M}")
    db.commit()
    db.refresh(item)
    return item


@router.patch("/{item_id}", response_model=AppointmentOut)
def update_appointment(care_recipient_id: int, item_id: int, body: AppointmentUpdate, user: CurrentUser, db: Session = Depends(get_db)) -> Appointment:
    require_write(get_membership(db, user.id, care_recipient_id))
    item = _get_item(db, care_recipient_id, item_id)
    changes = model_dump_set(body)
    ensure_member_user(db, care_recipient_id, changes.get("assigned_to_id"))
    for field, value in changes.items():
        setattr(item, field, value)
    item.updated_at = utcnow()
    if "status" in changes:
        verb = {"completed": "marked as completed", "cancelled": "cancelled"}.get(item.status, "set to " + item.status)
        summary = f"{user.full_name} {verb} appointment '{item.title}'"
    else:
        summary = f"{user.full_name} updated appointment '{item.title}'"
    log_activity(db, care_recipient_id, user.id, "update", "appointment", item.id, summary)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_appointment(care_recipient_id: int, item_id: int, user: CurrentUser, db: Session = Depends(get_db)) -> Response:
    require_write(get_membership(db, user.id, care_recipient_id))
    item = _get_item(db, care_recipient_id, item_id)
    log_activity(db, care_recipient_id, user.id, "delete", "appointment", item.id,
                 f"{user.full_name} deleted appointment '{item.title}'")
    db.delete(item)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
