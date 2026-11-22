"""Activity log: who did what, newest first."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.access import get_membership
from app.database import get_db
from app.deps import CurrentUser
from app.models import ActivityLog, User
from app.schemas import ActivityOut

router = APIRouter(prefix="/care-recipients/{care_recipient_id}/activity", tags=["activity"])


def recent_activity(db: Session, care_recipient_id: int, limit: int) -> list[ActivityOut]:
    rows = db.execute(
        select(ActivityLog, User.full_name)
        .outerjoin(User, User.id == ActivityLog.actor_id)
        .where(ActivityLog.care_recipient_id == care_recipient_id)
        .order_by(ActivityLog.created_at.desc(), ActivityLog.id.desc())
        .limit(limit)
    ).all()
    out: list[ActivityOut] = []
    for log, actor_name in rows:
        item = ActivityOut.model_validate(log)
        item.actor_name = actor_name
        out.append(item)
    return out


@router.get("", response_model=list[ActivityOut])
def list_activity(
    care_recipient_id: int,
    user: CurrentUser,
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
) -> list[ActivityOut]:
    get_membership(db, user.id, care_recipient_id)
    return recent_activity(db, care_recipient_id, limit)
