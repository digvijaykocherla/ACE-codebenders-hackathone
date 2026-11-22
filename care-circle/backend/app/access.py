"""Care-recipient access rules and the activity-log helper."""
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.deps import require_role
from app.models import ActivityLog, Membership, utcnow


def get_membership(db: Session, user_id: int, care_recipient_id: int) -> Membership:
    """Return the caller's membership, or 404 so non-members cannot even see the record exists."""
    membership = db.scalar(
        select(Membership).where(
            Membership.user_id == user_id,
            Membership.care_recipient_id == care_recipient_id,
        )
    )
    if membership is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Care recipient not found")
    return membership


def require_write(membership: Membership) -> Membership:
    """Coordinators and caregivers may write; viewers get 403."""
    return require_role(membership, "coordinator", "caregiver")


def require_coordinator(membership: Membership) -> Membership:
    return require_role(membership, "coordinator")


def ensure_member_user(db: Session, care_recipient_id: int, user_id: int | None) -> None:
    """Assignees must be members of the same care circle."""
    if user_id is None:
        return
    exists = db.scalar(
        select(Membership.id).where(
            Membership.user_id == user_id,
            Membership.care_recipient_id == care_recipient_id,
        )
    )
    if exists is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Assignee must be a member of this care circle")


def log_activity(
    db: Session,
    care_recipient_id: int,
    actor_id: int,
    action: str,
    entity_type: str,
    entity_id: int | None,
    summary: str,
) -> None:
    """Stage an ActivityLog row. The caller commits, so the change and its log are saved together."""
    db.add(
        ActivityLog(
            care_recipient_id=care_recipient_id,
            actor_id=actor_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            summary=summary[:500],
            created_at=utcnow(),
        )
    )
