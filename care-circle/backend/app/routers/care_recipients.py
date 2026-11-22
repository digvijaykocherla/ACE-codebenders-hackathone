"""Care recipients: list/create the caller's circles, read and update one."""
from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.access import get_membership, log_activity, require_write
from app.database import get_db
from app.deps import CurrentUser
from app.models import CareRecipient, Membership
from app.schemas import CareRecipientCreate, CareRecipientOut, CareRecipientUpdate, model_dump_set

router = APIRouter(prefix="/care-recipients", tags=["care-recipients"])


def _out(cr: CareRecipient, role: str | None) -> CareRecipientOut:
    out = CareRecipientOut.model_validate(cr)
    out.my_role = role  # type: ignore[assignment]
    return out


@router.get("", response_model=list[CareRecipientOut])
def list_care_recipients(user: CurrentUser, db: Session = Depends(get_db)) -> list[CareRecipientOut]:
    rows = db.execute(
        select(CareRecipient, Membership.role)
        .join(Membership, Membership.care_recipient_id == CareRecipient.id)
        .where(Membership.user_id == user.id)
        .order_by(CareRecipient.full_name)
    ).all()
    return [_out(cr, role) for cr, role in rows]


@router.post("", response_model=CareRecipientOut, status_code=status.HTTP_201_CREATED)
def create_care_recipient(body: CareRecipientCreate, user: CurrentUser, db: Session = Depends(get_db)) -> CareRecipientOut:
    cr = CareRecipient(**body.model_dump())
    db.add(cr)
    db.flush()  # assigns cr.id
    db.add(Membership(user_id=user.id, care_recipient_id=cr.id, role="coordinator"))
    log_activity(db, cr.id, user.id, "create", "care_recipient", cr.id,
                 f"{user.full_name} created care record '{cr.full_name}'")
    db.commit()
    db.refresh(cr)
    return _out(cr, "coordinator")


@router.get("/{care_recipient_id}", response_model=CareRecipientOut)
def get_care_recipient(care_recipient_id: int, user: CurrentUser, db: Session = Depends(get_db)) -> CareRecipientOut:
    membership = get_membership(db, user.id, care_recipient_id)
    cr = db.get(CareRecipient, care_recipient_id)
    return _out(cr, membership.role)


@router.patch("/{care_recipient_id}", response_model=CareRecipientOut)
def update_care_recipient(
    care_recipient_id: int, body: CareRecipientUpdate, user: CurrentUser, db: Session = Depends(get_db)
) -> CareRecipientOut:
    membership = require_write(get_membership(db, user.id, care_recipient_id))
    cr = db.get(CareRecipient, care_recipient_id)
    for field, value in model_dump_set(body).items():
        setattr(cr, field, value)
    log_activity(db, cr.id, user.id, "update", "care_recipient", cr.id,
                 f"{user.full_name} updated care record '{cr.full_name}'")
    db.commit()
    db.refresh(cr)
    return _out(cr, membership.role)
