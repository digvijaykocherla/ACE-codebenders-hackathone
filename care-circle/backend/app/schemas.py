"""Pydantic v2 request/response schemas. Organisational fields only."""
from datetime import date, datetime, timedelta, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

Role = Literal["coordinator", "caregiver", "viewer"]
AppointmentStatus = Literal["scheduled", "completed", "cancelled"]
PrescriptionStatus = Literal["active", "paused", "completed"]
ReportType = Literal["lab", "imaging", "discharge", "other"]
TaskStatus = Literal["open", "in_progress", "done"]
Priority = Literal["low", "normal", "high"]

MAX_FUTURE_DAYS = 3653  # roughly 10 years


def to_naive_utc(dt: datetime) -> datetime:
    """Convert aware datetimes to naive UTC so SQLite and PostgreSQL behave the same."""
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def check_not_too_far(value: date | None) -> date | None:
    """Reject due/scheduled dates more than 10 years in the future."""
    if value is None:
        return None
    as_date = value.date() if isinstance(value, datetime) else value
    if as_date > date.today() + timedelta(days=MAX_FUTURE_DAYS):
        raise ValueError("date must be within 10 years from today")
    return value


def normalize_dt(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return check_not_too_far(to_naive_utc(value))  # type: ignore[return-value]


def reject_nulls(model: BaseModel, names: tuple[str, ...]) -> None:
    """For PATCH bodies: required columns may be omitted but not set to null."""
    for name in names:
        if name in model.model_fields_set and getattr(model, name) is None:
            raise ValueError(f"{name} cannot be null")


# ---------- auth / users ----------
class UserCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8)
    city: str = Field(min_length=1, max_length=120)

    @field_validator("email")
    @classmethod
    def _lower_email(cls, v: str) -> str:
        return v.lower()

    @field_validator("password")
    @classmethod
    def _password_bytes(cls, v: str) -> str:
        if len(v.encode("utf-8")) > 72:  # bcrypt limit
            raise ValueError("password must be at most 72 bytes")
        return v


class LoginIn(BaseModel):
    email: EmailStr
    password: str

    @field_validator("email")
    @classmethod
    def _lower_email(cls, v: str) -> str:
        return v.lower()


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    full_name: str
    email: str
    city: str
    created_at: datetime


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------- care recipients & members ----------
class CareRecipientCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=120)
    date_of_birth: date | None = None
    city: str = Field(min_length=1, max_length=120)
    notes: str | None = Field(default=None, max_length=2000)


class CareRecipientUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=120)
    date_of_birth: date | None = None
    city: str | None = Field(default=None, min_length=1, max_length=120)
    notes: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def _required(self) -> "CareRecipientUpdate":
        reject_nulls(self, ("full_name", "city"))
        return self


class CareRecipientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    full_name: str
    date_of_birth: date | None
    city: str
    notes: str | None
    created_at: datetime
    my_role: Role | None = None


class MemberCreate(BaseModel):
    email: EmailStr
    role: Role = "caregiver"

    @field_validator("email")
    @classmethod
    def _lower_email(cls, v: str) -> str:
        return v.lower()


class MemberUpdate(BaseModel):
    role: Role


class MemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    care_recipient_id: int
    role: Role
    user: UserOut


# ---------- appointments ----------
class AppointmentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    doctor_name: str | None = Field(default=None, max_length=120)
    location: str | None = Field(default=None, max_length=200)
    scheduled_at: datetime
    status: AppointmentStatus = "scheduled"
    notes: str | None = Field(default=None, max_length=2000)
    assigned_to_id: int | None = None

    @field_validator("scheduled_at")
    @classmethod
    def _dt(cls, v: datetime) -> datetime:
        return normalize_dt(v)  # type: ignore[return-value]


class AppointmentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    doctor_name: str | None = Field(default=None, max_length=120)
    location: str | None = Field(default=None, max_length=200)
    scheduled_at: datetime | None = None
    status: AppointmentStatus | None = None
    notes: str | None = Field(default=None, max_length=2000)
    assigned_to_id: int | None = None

    @field_validator("scheduled_at")
    @classmethod
    def _dt(cls, v: datetime | None) -> datetime | None:
        return normalize_dt(v)

    @model_validator(mode="after")
    def _required(self) -> "AppointmentUpdate":
        reject_nulls(self, ("title", "scheduled_at", "status"))
        return self


class AppointmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    care_recipient_id: int
    title: str
    doctor_name: str | None
    location: str | None
    scheduled_at: datetime
    status: AppointmentStatus
    notes: str | None
    created_by_id: int
    assigned_to_id: int | None
    created_at: datetime
    updated_at: datetime


# ---------- prescriptions & refills ----------
class PrescriptionCreate(BaseModel):
    medicine_name: str = Field(min_length=1, max_length=200)
    dosage_text: str = Field(min_length=1, max_length=200)
    prescribed_by: str | None = Field(default=None, max_length=120)
    start_date: date
    end_date: date | None = None
    refill_due_date: date | None = None
    refills_remaining: int = Field(default=0, ge=0, le=99)
    pharmacy: str | None = Field(default=None, max_length=200)
    status: PrescriptionStatus = "active"

    @field_validator("refill_due_date", "end_date")
    @classmethod
    def _not_far(cls, v: date | None) -> date | None:
        return check_not_too_far(v)

    @model_validator(mode="after")
    def _dates(self) -> "PrescriptionCreate":
        if self.end_date is not None and self.end_date < self.start_date:
            raise ValueError("end_date cannot be before start_date")
        return self


class PrescriptionUpdate(BaseModel):
    medicine_name: str | None = Field(default=None, min_length=1, max_length=200)
    dosage_text: str | None = Field(default=None, min_length=1, max_length=200)
    prescribed_by: str | None = Field(default=None, max_length=120)
    start_date: date | None = None
    end_date: date | None = None
    refill_due_date: date | None = None
    refills_remaining: int | None = Field(default=None, ge=0, le=99)
    pharmacy: str | None = Field(default=None, max_length=200)
    status: PrescriptionStatus | None = None

    @field_validator("refill_due_date", "end_date")
    @classmethod
    def _not_far(cls, v: date | None) -> date | None:
        return check_not_too_far(v)

    @model_validator(mode="after")
    def _required(self) -> "PrescriptionUpdate":
        reject_nulls(self, ("medicine_name", "dosage_text", "start_date", "refills_remaining", "status"))
        return self


class PrescriptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    care_recipient_id: int
    medicine_name: str
    dosage_text: str
    prescribed_by: str | None
    start_date: date
    end_date: date | None
    refill_due_date: date | None
    refills_remaining: int
    pharmacy: str | None
    status: PrescriptionStatus
    created_by_id: int
    created_at: datetime
    updated_at: datetime


class RefillItem(BaseModel):
    prescription: PrescriptionOut
    days_until_refill: int | None
    flags: list[str]  # any of: "overdue", "due_soon", "no_refills_left"


# ---------- reports ----------
class ReportCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    report_type: ReportType
    report_date: date
    source: str | None = Field(default=None, max_length=200)
    summary: str | None = Field(default=None, max_length=4000)


class ReportUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    report_type: ReportType | None = None
    report_date: date | None = None
    source: str | None = Field(default=None, max_length=200)
    summary: str | None = Field(default=None, max_length=4000)

    @model_validator(mode="after")
    def _required(self) -> "ReportUpdate":
        reject_nulls(self, ("title", "report_type", "report_date"))
        return self


class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    care_recipient_id: int
    title: str
    report_type: ReportType
    report_date: date
    source: str | None
    summary: str | None
    created_by_id: int
    created_at: datetime


# ---------- tasks ----------
class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    assignee_id: int | None = None
    due_at: datetime | None = None
    reminder_at: datetime | None = None
    priority: Priority = "normal"
    status: TaskStatus = "open"

    @field_validator("due_at", "reminder_at")
    @classmethod
    def _dt(cls, v: datetime | None) -> datetime | None:
        return normalize_dt(v)


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    assignee_id: int | None = None
    due_at: datetime | None = None
    reminder_at: datetime | None = None
    priority: Priority | None = None
    status: TaskStatus | None = None

    @field_validator("due_at", "reminder_at")
    @classmethod
    def _dt(cls, v: datetime | None) -> datetime | None:
        return normalize_dt(v)

    @model_validator(mode="after")
    def _required(self) -> "TaskUpdate":
        reject_nulls(self, ("title", "priority", "status"))
        return self


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    care_recipient_id: int
    title: str
    description: str | None
    assignee_id: int | None
    due_at: datetime | None
    reminder_at: datetime | None
    priority: Priority
    status: TaskStatus
    created_by_id: int
    completed_by_id: int | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    is_overdue: bool = False


# ---------- timeline / dashboard / reminders / activity ----------
class TimelineItem(BaseModel):
    item_type: Literal["appointment", "prescription", "report"]
    item_id: int
    at: datetime
    title: str
    summary: str


class AssigneeCount(BaseModel):
    assignee_id: int | None
    assignee_name: str | None
    open_count: int


class ReminderItem(BaseModel):
    kind: Literal["task", "appointment", "refill"]
    item_id: int
    title: str
    at: datetime
    detail: str


class ActivityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    care_recipient_id: int
    actor_id: int
    actor_name: str | None = None
    action: str
    entity_type: str
    entity_id: int | None
    summary: str
    created_at: datetime


class DashboardOut(BaseModel):
    upcoming_appointments: list[AppointmentOut]
    refills_due: list[RefillItem]
    overdue_task_count: int
    overdue_tasks: list[TaskOut]
    open_tasks_per_assignee: list[AssigneeCount]
    recent_activity: list[ActivityOut]
    pending_items: int  # open tasks + upcoming scheduled appointments + flagged refills


def model_dump_set(model: BaseModel) -> dict[str, Any]:
    """Only the fields the client actually sent (for PATCH)."""
    return model.model_dump(exclude_unset=True)
