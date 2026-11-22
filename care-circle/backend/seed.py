"""Seed SYNTHETIC demo data. Run from backend/:  python seed.py

Idempotent: if priya@demo-family.com already exists, prints a message and exits.
All names, records and contacts below are fictional.
"""
from datetime import date, datetime, time, timedelta

from sqlalchemy import select

from app import models  # noqa: F401  (registers tables)
from app.access import log_activity
from app.database import Base, SessionLocal, engine
from app.models import Appointment, CareRecipient, Membership, Prescription, Report, Task, User, utcnow
from app.security import hash_password

PASSWORD = "Demo@1234"


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.scalar(select(User).where(User.email == "priya@demo-family.com")):
            print("Seed data already present")
            return

        pw = hash_password(PASSWORD)
        priya = User(full_name="Priya Sharma (SYNTHETIC)", email="priya@demo-family.com", password_hash=pw, city="Pune")
        arjun = User(full_name="Arjun Sharma (SYNTHETIC)", email="arjun@demo-family.com", password_hash=pw, city="Toronto")
        meera = User(full_name="Meera Sharma (SYNTHETIC)", email="meera@demo-family.com", password_hash=pw, city="Chennai")
        db.add_all([priya, arjun, meera])
        db.flush()

        cr = CareRecipient(
            full_name="Ramesh Sharma (SYNTHETIC)",
            date_of_birth=date(1948, 5, 12),
            city="Pune",
            notes="SYNTHETIC demo record. Organisational notes only.",
        )
        db.add(cr)
        db.flush()
        db.add_all([
            Membership(user_id=priya.id, care_recipient_id=cr.id, role="coordinator"),
            Membership(user_id=arjun.id, care_recipient_id=cr.id, role="caregiver"),
            Membership(user_id=meera.id, care_recipient_id=cr.id, role="viewer"),
        ])
        log_activity(db, cr.id, priya.id, "create", "care_recipient", cr.id,
                     f"{priya.full_name} created care record '{cr.full_name}'")
        log_activity(db, cr.id, priya.id, "add_member", "membership", None,
                     f"{priya.full_name} added {arjun.full_name} as caregiver")
        log_activity(db, cr.id, priya.id, "add_member", "membership", None,
                     f"{priya.full_name} added {meera.full_name} as viewer")

        # Appointments (4)
        now = utcnow()
        at_10 = lambda days: (now + timedelta(days=days)).replace(hour=10, minute=0, second=0, microsecond=0)  # noqa: E731
        appts = [
            Appointment(title="Cardiology follow-up", care_recipient_id=cr.id, doctor_name="Dr. Anita Rao (SYNTHETIC)",
                        location="City Clinic, Pune (SYNTHETIC)", scheduled_at=at_10(2),
                        status="scheduled", assigned_to_id=priya.id, created_by_id=priya.id),
            Appointment(title="Physiotherapy session", care_recipient_id=cr.id, doctor_name="Dr. Vikram Nair (SYNTHETIC)",
                        location="Riverside Physio, Toronto (SYNTHETIC)", scheduled_at=at_10(9),
                        status="scheduled", assigned_to_id=arjun.id, created_by_id=priya.id),
            Appointment(title="Annual eye check", care_recipient_id=cr.id, doctor_name="Dr. Leela Menon (SYNTHETIC)",
                        location="Chennai Eye Centre (SYNTHETIC)", scheduled_at=at_10(-10),
                        status="completed", assigned_to_id=priya.id, created_by_id=priya.id),
            Appointment(title="Dental cleaning", care_recipient_id=cr.id, doctor_name="Dr. Kiran Das (SYNTHETIC)",
                        location="Smile Dental, Pune (SYNTHETIC)", scheduled_at=at_10(30),
                        status="cancelled", created_by_id=priya.id),
        ]
        db.add_all(appts)

        # Prescriptions (3)
        today = date.today()
        rx = [
            Prescription(medicine_name="Metformin 500 mg (SYNTHETIC)", care_recipient_id=cr.id, dosage_text="1 tablet twice daily",
                         prescribed_by="Dr. Anita Rao (SYNTHETIC)", start_date=today - timedelta(days=90),
                         refill_due_date=today + timedelta(days=3), refills_remaining=2,
                         pharmacy="Sunrise Pharmacy (SYNTHETIC)", status="active", created_by_id=priya.id),
            Prescription(medicine_name="Amlodipine 5 mg (SYNTHETIC)", care_recipient_id=cr.id, dosage_text="1 tablet each morning",
                         prescribed_by="Dr. Anita Rao (SYNTHETIC)", start_date=today - timedelta(days=120),
                         refill_due_date=today - timedelta(days=2), refills_remaining=1,
                         pharmacy="Sunrise Pharmacy (SYNTHETIC)", status="active", created_by_id=priya.id),
            Prescription(medicine_name="Vitamin D3 1000 IU (SYNTHETIC)", care_recipient_id=cr.id, dosage_text="1 capsule weekly",
                         prescribed_by="Dr. Anita Rao (SYNTHETIC)", start_date=today - timedelta(days=30),
                         refills_remaining=0, pharmacy="Sunrise Pharmacy (SYNTHETIC)",
                         status="active", created_by_id=priya.id),
        ]
        db.add_all(rx)

        # Reports (2)
        db.add_all([
            Report(title="Blood panel (SYNTHETIC)", care_recipient_id=cr.id, report_type="lab", report_date=today - timedelta(days=14),
                   source="Sunrise Diagnostics (SYNTHETIC)",
                   summary="Routine panel filed for records (SYNTHETIC).", created_by_id=priya.id),
            Report(title="Knee X-ray (SYNTHETIC)", care_recipient_id=cr.id, report_type="imaging", report_date=today - timedelta(days=40),
                   source="City Imaging Centre (SYNTHETIC)",
                   summary="Imaging report filed for records (SYNTHETIC).", created_by_id=priya.id),
        ])

        # Tasks (5 across statuses; 2 overdue)
        db.add_all([
            Task(title="Pick up BP meds (SYNTHETIC)", care_recipient_id=cr.id, assignee_id=arjun.id, priority="high", status="open",
                 due_at=now - timedelta(days=1), reminder_at=now - timedelta(days=1), created_by_id=priya.id),
            Task(title="Book cardiology follow-up (SYNTHETIC)", care_recipient_id=cr.id, assignee_id=priya.id, priority="normal",
                 status="open", due_at=now + timedelta(days=1), reminder_at=now + timedelta(hours=20),
                 created_by_id=priya.id),
            Task(title="Arrange wheelchair ramp quote (SYNTHETIC)", care_recipient_id=cr.id, assignee_id=arjun.id, priority="normal",
                 status="open", due_at=now - timedelta(days=3), created_by_id=priya.id),
            Task(title="Upload last month's lab report (SYNTHETIC)", care_recipient_id=cr.id, assignee_id=priya.id, priority="low",
                 status="done", due_at=now - timedelta(days=5), created_by_id=priya.id,
                 completed_by_id=priya.id, completed_at=now - timedelta(days=1)),
            Task(title="Confirm physiotherapy transport (SYNTHETIC)", care_recipient_id=cr.id, assignee_id=arjun.id, priority="normal",
                 status="in_progress", due_at=now + timedelta(days=5), created_by_id=priya.id),
        ])

        log_activity(db, cr.id, priya.id, "create", "appointment", None,
                     f"{priya.full_name} scheduled 'Cardiology follow-up' (SYNTHETIC)")
        log_activity(db, cr.id, priya.id, "create", "prescription", None,
                     f"{priya.full_name} added prescription 'Metformin 500 mg (SYNTHETIC)'")
        log_activity(db, cr.id, priya.id, "create", "task", None,
                     f"{priya.full_name} created task 'Pick up BP meds (SYNTHETIC)'")
        log_activity(db, cr.id, priya.id, "complete", "task", None,
                     f"{priya.full_name} marked 'Upload last month's lab report (SYNTHETIC)' as done")
        log_activity(db, cr.id, arjun.id, "update", "task", None,
                     f"{arjun.full_name} set 'Confirm physiotherapy transport (SYNTHETIC)' to in progress")

        db.commit()
        print("Seed complete. Login with priya@demo-family.com / arjun@demo-family.com / meera@demo-family.com, password Demo@1234 (SYNTHETIC data)")
    finally:
        db.close()


if __name__ == "__main__":
    main()
