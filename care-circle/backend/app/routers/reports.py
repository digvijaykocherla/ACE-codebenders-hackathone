"""Medical and other reports (organised records only; no clinical interpretation)."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.access import get_membership, log_activity, require_write
from app.database import get_db
from app.deps import CurrentUser
from app.models import Report, utcnow
from app.schemas import ReportCreate, ReportOut, ReportUpdate, model_dump_set

router = APIRouter(prefix="/care-recipients/{care_recipient_id}/reports", tags=["reports"])


def _get_item(db: Session, care_recipient_id: int, item_id: int) -> Report:
    item = db.get(Report, item_id)
    if item is None or item.care_recipient_id != care_recipient_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report not found")
    return item


@router.get("", response_model=list[ReportOut])
def list_reports(care_recipient_id: int, user: CurrentUser, db: Session = Depends(get_db)) -> list[Report]:
    get_membership(db, user.id, care_recipient_id)
    return list(db.scalars(
        select(Report).where(Report.care_recipient_id == care_recipient_id).order_by(Report.report_date.desc())
    ).all())


@router.post("", response_model=ReportOut, status_code=status.HTTP_201_CREATED)
def create_report(care_recipient_id: int, body: ReportCreate, user: CurrentUser, db: Session = Depends(get_db)) -> Report:
    require_write(get_membership(db, user.id, care_recipient_id))
    item = Report(care_recipient_id=care_recipient_id, created_by_id=user.id, **body.model_dump())
    db.add(item)
    db.flush()
    log_activity(db, care_recipient_id, user.id, "create", "report", item.id,
                 f"{user.full_name} filed report '{item.title}'")
    db.commit()
    db.refresh(item)
    return item


@router.patch("/{item_id}", response_model=ReportOut)
def update_report(care_recipient_id: int, item_id: int, body: ReportUpdate, user: CurrentUser, db: Session = Depends(get_db)) -> Report:
    require_write(get_membership(db, user.id, care_recipient_id))
    item = _get_item(db, care_recipient_id, item_id)
    for field, value in model_dump_set(body).items():
        setattr(item, field, value)
    log_activity(db, care_recipient_id, user.id, "update", "report", item.id,
                 f"{user.full_name} updated report '{item.title}'")
    db.commit()
    db.refresh(item)
    return item
