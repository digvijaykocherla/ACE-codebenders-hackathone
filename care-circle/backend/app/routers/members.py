"""Members of a care circle. Only coordinators manage members."""
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.access import get_membership, log_activity, require_coordinator
from app.database import get_db
from app.deps import CurrentUser
from app.models import Membership, User
from app.schemas import MemberCreate, MemberOut, MemberUpdate

router = APIRouter(prefix="/care-recipients/{care_recipient_id}/members", tags=["members"])


def _coordinator_count(db: Session, care_recipient_id: int) -> int:
    return db.scalar(
        select(func.count(Membership.id)).where(
            Membership.care_recipient_id == care_recipient_id, Membership.role == "coordinator"
        )
    ) or 0


@router.get("", response_model=list[MemberOut])
def list_members(care_recipient_id: int, user: CurrentUser, db: Session = Depends(get_db)) -> list[Membership]:
    get_membership(db, user.id, care_recipient_id)
    return list(db.scalars(
        select(Membership).where(Membership.care_recipient_id == care_recipient_id).order_by(Membership.id)
    ).all())


@router.post("", response_model=MemberOut, status_code=status.HTTP_201_CREATED)
def add_member(care_recipient_id: int, body: MemberCreate, user: CurrentUser, db: Session = Depends(get_db)) -> Membership:
    require_coordinator(get_membership(db, user.id, care_recipient_id))
    target = db.scalar(select(User).where(User.email == body.email))
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No user with that email; they must register first")
    if db.scalar(select(Membership.id).where(
        Membership.user_id == target.id, Membership.care_recipient_id == care_recipient_id
    )) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "User is already a member")
    membership = Membership(user_id=target.id, care_recipient_id=care_recipient_id, role=body.role)
    db.add(membership)
    db.flush()
    log_activity(db, care_recipient_id, user.id, "add_member", "membership", membership.id,
                 f"{user.full_name} added {target.full_name} as {body.role}")
    db.commit()
    db.refresh(membership)
    return membership


@router.patch("/{membership_id}", response_model=MemberOut)
def update_member(
    care_recipient_id: int, membership_id: int, body: MemberUpdate, user: CurrentUser, db: Session = Depends(get_db)
) -> Membership:
    require_coordinator(get_membership(db, user.id, care_recipient_id))
    target = db.get(Membership, membership_id)
    if target is None or target.care_recipient_id != care_recipient_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Membership not found")
    if target.role == "coordinator" and body.role != "coordinator" and _coordinator_count(db, care_recipient_id) <= 1:
        raise HTTPException(status.HTTP_409_CONFLICT, "Cannot demote the last coordinator")
    old_role = target.role
    target.role = body.role
    log_activity(db, care_recipient_id, user.id, "update_member", "membership", target.id,
                 f"{user.full_name} changed {target.user.full_name}'s role from {old_role} to {body.role}")
    db.commit()
    db.refresh(target)
    return target


@router.delete("/{membership_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(care_recipient_id: int, membership_id: int, user: CurrentUser, db: Session = Depends(get_db)) -> Response:
    require_coordinator(get_membership(db, user.id, care_recipient_id))
    target = db.get(Membership, membership_id)
    if target is None or target.care_recipient_id != care_recipient_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Membership not found")
    if target.role == "coordinator" and _coordinator_count(db, care_recipient_id) <= 1:
        raise HTTPException(status.HTTP_409_CONFLICT, "Cannot remove the last coordinator")
    log_activity(db, care_recipient_id, user.id, "remove_member", "membership", target.id,
                 f"{user.full_name} removed {target.user.full_name} from the care circle")
    db.delete(target)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
