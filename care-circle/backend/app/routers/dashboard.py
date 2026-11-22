"""Dashboard summary and 48-hour reminders."""
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.access import get_membership
from app.database import get_db
from app.deps import CurrentUser
from app.models import Appointment, Prescription, Task, User, utcnow
from app.routers.activity import recent_activity
from app.routers.prescriptions import build_refill_items
from app.routers.tasks import to_out
from app.schemas import AppointmentOut, AssigneeCount, DashboardOut, ReminderItem

router = APIRouter(prefix="/care-recipients/{care_recipient_id}", tags=["dashboard"])


@router.get("/dashboard", response_model=DashboardOut)
def dashboard(care_recipient_id: int, user: CurrentUser, db: Session = Depends(get_db)) -> DashboardOut:
    get_membership(db, user.id, care_recipient_id)
    now = utcnow()

    upcoming = db.scalars(
        select(Appointment)
        .where(Appointment.care_recipient_id == care_recipient_id,
               Appointment.status == "scheduled", Appointment.scheduled_at >= now)
        .order_by(Appointment.scheduled_at).limit(3)
    ).all()

    refills = build_refill_items(db, care_recipient_id, days=14)

    overdue = db.scalars(
        select(Task).where(Task.care_recipient_id == care_recipient_id, Task.status != "done",
                           Task.due_at.is_not(None), Task.due_at < now)
        .order_by(Task.due_at)
    ).all()

    per_assignee = db.execute(
        select(Task.assignee_id, func.count(Task.id))
        .where(Task.care_recipient_id == care_recipient_id, Task.status != "done")
        .group_by(Task.assignee_id)
    ).all()
    ids = [aid for aid, _ in per_assignee if aid is not None]
    names = dict(db.execute(select(User.id, User.full_name).where(User.id.in_(ids))).all()) if ids else {}
    assignee_counts = [
        AssigneeCount(assignee_id=aid, assignee_name=names.get(aid) if aid else None, open_count=cnt)
        for aid, cnt in per_assignee
    ]

    open_task_count = db.scalar(
        select(func.count(Task.id)).where(Task.care_recipient_id == care_recipient_id, Task.status != "done")
    ) or 0
    upcoming_count = db.scalar(
        select(func.count(Appointment.id)).where(
            Appointment.care_recipient_id == care_recipient_id,
            Appointment.status == "scheduled", Appointment.scheduled_at >= now)
    ) or 0

    return DashboardOut(
        upcoming_appointments=[AppointmentOut.model_validate(a) for a in upcoming],
        refills_due=refills,
        overdue_task_count=len(overdue),
        overdue_tasks=[to_out(t, now) for t in overdue],
        open_tasks_per_assignee=assignee_counts,
        recent_activity=recent_activity(db, care_recipient_id, 5),
        pending_items=open_task_count + upcoming_count + len(refills),
    )


@router.get("/reminders", response_model=list[ReminderItem])
def reminders(care_recipient_id: int, user: CurrentUser, db: Session = Depends(get_db)) -> list[ReminderItem]:
    """Tasks (reminder or due), appointments and refills falling in the next 48 hours."""
    get_membership(db, user.id, care_recipient_id)
    now = utcnow()
    horizon = now + timedelta(hours=48)
    out: list[ReminderItem] = []

    tasks = db.scalars(
        select(Task).where(Task.care_recipient_id == care_recipient_id, Task.status != "done")
    ).all()
    for t in tasks:
        for label, at in (("reminder", t.reminder_at), ("due", t.due_at)):
            if at is not None and now <= at <= horizon:
                out.append(ReminderItem(kind="task", item_id=t.id, title=t.title, at=at,
                                        detail=f"Task {label}"))

    appts = db.scalars(
        select(Appointment).where(
            Appointment.care_recipient_id == care_recipient_id,
            Appointment.status == "scheduled",
            Appointment.scheduled_at.between(now, horizon),
        )
    ).all()
    for a in appts:
        out.append(ReminderItem(kind="appointment", item_id=a.id, title=a.title, at=a.scheduled_at,
                                detail=f"Appointment{' with ' + a.doctor_name if a.doctor_name else ''}"))

    today: date = now.date()
    refill_rows = db.scalars(
        select(Prescription).where(
            Prescription.care_recipient_id == care_recipient_id,
            Prescription.refill_due_date.is_not(None),
            Prescription.refill_due_date >= today,
            Prescription.refill_due_date <= (horizon.date()),
        )
    ).all()
    for p in refill_rows:
        out.append(ReminderItem(kind="refill", item_id=p.id, title=p.medicine_name,
                                at=datetime.combine(p.refill_due_date, datetime.min.time()),
                                detail="Refill due"))

    return sorted(out, key=lambda r: r.at)
