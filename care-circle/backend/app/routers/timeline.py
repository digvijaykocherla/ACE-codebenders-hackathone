"""Merged timeline of appointments, prescriptions and reports."""
from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.access import get_membership
from app.database import get_db
from app.deps import CurrentUser
from app.models import Appointment, Prescription, Report
from app.schemas import TimelineItem

router = APIRouter(prefix="/care-recipients/{care_recipient_id}/timeline", tags=["timeline"])


@router.get("", response_model=list[TimelineItem])
def get_timeline(
    care_recipient_id: int,
    user: CurrentUser,
    db: Session = Depends(get_db),
    date_from: date | None = Query(None, alias="from"),
    date_to: date | None = Query(None, alias="to"),
) -> list[TimelineItem]:
    get_membership(db, user.id, care_recipient_id)
    items: list[TimelineItem] = []

    appt_stmt = select(Appointment).where(Appointment.care_recipient_id == care_recipient_id)
    if date_from:
        appt_stmt = appt_stmt.where(Appointment.scheduled_at >= datetime.combine(date_from, time.min))
    if date_to:
        appt_stmt = appt_stmt.where(Appointment.scheduled_at < datetime.combine(date_to + timedelta(days=1), time.min))
    for a in db.scalars(appt_stmt).all():
        with_doctor = f" with {a.doctor_name}" if a.doctor_name else ""
        items.append(TimelineItem(item_type="appointment", item_id=a.id, at=a.scheduled_at,
                                  title=a.title, summary=f"{a.status.capitalize()} appointment{with_doctor}"))

    rx_stmt = select(Prescription).where(Prescription.care_recipient_id == care_recipient_id)
    if date_from:
        rx_stmt = rx_stmt.where(Prescription.start_date >= date_from)
    if date_to:
        rx_stmt = rx_stmt.where(Prescription.start_date <= date_to)
    for p in db.scalars(rx_stmt).all():
        items.append(TimelineItem(item_type="prescription", item_id=p.id,
                                  at=datetime.combine(p.start_date, time.min),
                                  title=p.medicine_name, summary=f"Prescription started: {p.dosage_text}"))

    rep_stmt = select(Report).where(Report.care_recipient_id == care_recipient_id)
    if date_from:
        rep_stmt = rep_stmt.where(Report.report_date >= date_from)
    if date_to:
        rep_stmt = rep_stmt.where(Report.report_date <= date_to)
    for r in db.scalars(rep_stmt).all():
        items.append(TimelineItem(item_type="report", item_id=r.id,
                                  at=datetime.combine(r.report_date, time.min),
                                  title=r.title, summary=f"{r.report_type.capitalize()} report from {r.source or 'unknown source'}"))

    return sorted(items, key=lambda i: i.at)
