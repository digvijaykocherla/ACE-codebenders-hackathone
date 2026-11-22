"""Tasks with assignees, reminders, overdue tracking and completion."""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.access import ensure_member_user, get_membership, log_activity, require_write
from app.database import get_db
from app.deps import CurrentUser
from app.models import Task, utcnow
from app.schemas import TaskCreate, TaskOut, TaskUpdate, model_dump_set

router = APIRouter(prefix="/care-recipients/{care_recipient_id}/tasks", tags=["tasks"])


def to_out(task: Task, now: datetime | None = None) -> TaskOut:
    now = now or utcnow()
    out = TaskOut.model_validate(task)
    out.is_overdue = task.status != "done" and task.due_at is not None and task.due_at < now
    return out


def _get_item(db: Session, care_recipient_id: int, item_id: int) -> Task:
    item = db.get(Task, item_id)
    if item is None or item.care_recipient_id != care_recipient_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")
    return item


@router.get("", response_model=list[TaskOut])
def list_tasks(
    care_recipient_id: int,
    user: CurrentUser,
    db: Session = Depends(get_db),
    assignee_id: int | None = Query(None),
    status_filter: str | None = Query(None, alias="status", pattern="^(open|in_progress|done)$"),
    overdue: bool = Query(False),
) -> list[TaskOut]:
    get_membership(db, user.id, care_recipient_id)
    now = utcnow()
    stmt = select(Task).where(Task.care_recipient_id == care_recipient_id)
    if assignee_id is not None:
        stmt = stmt.where(Task.assignee_id == assignee_id)
    if status_filter:
        stmt = stmt.where(Task.status == status_filter)
    if overdue:
        stmt = stmt.where(Task.status != "done", Task.due_at.is_not(None), Task.due_at < now)
    tasks = db.scalars(stmt.order_by(Task.due_at.is_(None), Task.due_at)).all()
    return [to_out(t, now) for t in tasks]


@router.post("", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(care_recipient_id: int, body: TaskCreate, user: CurrentUser, db: Session = Depends(get_db)) -> TaskOut:
    require_write(get_membership(db, user.id, care_recipient_id))
    ensure_member_user(db, care_recipient_id, body.assignee_id)
    item = Task(care_recipient_id=care_recipient_id, created_by_id=user.id, **body.model_dump())
    if item.status == "done":
        item.completed_by_id, item.completed_at = user.id, utcnow()
    db.add(item)
    db.flush()
    log_activity(db, care_recipient_id, user.id, "create", "task", item.id,
                 f"{user.full_name} created task '{item.title}'")
    db.commit()
    db.refresh(item)
    return to_out(item)


@router.patch("/{item_id}", response_model=TaskOut)
def update_task(care_recipient_id: int, item_id: int, body: TaskUpdate, user: CurrentUser, db: Session = Depends(get_db)) -> TaskOut:
    require_write(get_membership(db, user.id, care_recipient_id))
    item = _get_item(db, care_recipient_id, item_id)
    changes = model_dump_set(body)
    ensure_member_user(db, care_recipient_id, changes.get("assignee_id"))
    for field, value in changes.items():
        setattr(item, field, value)
    if "status" in changes:
        if item.status == "done":
            item.completed_by_id, item.completed_at = user.id, utcnow()
        else:
            item.completed_by_id, item.completed_at = None, None
        summary = f"{user.full_name} set '{item.title}' to {item.status.replace('_', ' ')}"
    else:
        summary = f"{user.full_name} updated task '{item.title}'"
    item.updated_at = utcnow()
    log_activity(db, care_recipient_id, user.id, "update", "task", item.id, summary)
    db.commit()
    db.refresh(item)
    return to_out(item)


@router.post("/{item_id}/complete", response_model=TaskOut)
def complete_task(care_recipient_id: int, item_id: int, user: CurrentUser, db: Session = Depends(get_db)) -> TaskOut:
    require_write(get_membership(db, user.id, care_recipient_id))
    item = _get_item(db, care_recipient_id, item_id)
    if item.status != "done":
        item.status = "done"
        item.completed_by_id, item.completed_at = user.id, utcnow()
        item.updated_at = utcnow()
        log_activity(db, care_recipient_id, user.id, "complete", "task", item.id,
                     f"{user.full_name} marked '{item.title}' as done")
        db.commit()
        db.refresh(item)
    return to_out(item)
