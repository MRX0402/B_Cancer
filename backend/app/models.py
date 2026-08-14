import enum
from datetime import datetime, date, time

from sqlalchemy import (
    String, Integer, Float, Boolean, Date, Time, DateTime, ForeignKey, Enum, Text
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class RoleEnum(str, enum.Enum):
    admin = "admin"
    doctor = "doctor"
    patient = "patient"


class StageEnum(str, enum.Enum):
    I = "I"
    II = "II"
    III = "III"
    IV = "IV"


class PatientStatusEnum(str, enum.Enum):
    faol = "Faol"
    davolanmoqda = "Davolanmoqda"
    remissiya = "Remissiya"
    kritik = "Kritik"
    barqaror = "Barqaror"
    kuzatuv = "Kuzatuv"
    yangi = "Yangi"


class AppointmentStatusEnum(str, enum.Enum):
    scheduled = "scheduled"
    completed = "completed"
    cancelled = "cancelled"


class LabStatusEnum(str, enum.Enum):
    normal = "normal"
    warning = "warning"
    critical = "critical"


class AlertTypeEnum(str, enum.Enum):
    critical = "critical"
    warning = "warning"
    info = "info"
    success = "success"


class TreatmentStatusEnum(str, enum.Enum):
    active = "active"
    completed = "completed"
    paused = "paused"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(128))
    role: Mapped[RoleEnum] = mapped_column(Enum(RoleEnum))
    email: Mapped[str | None] = mapped_column(String(128), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    avatar_initials: Mapped[str | None] = mapped_column(String(8), nullable=True)
    avatar_color: Mapped[str | None] = mapped_column(String(32), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    doctor_profile: Mapped["Doctor"] = relationship(back_populates="user", uselist=False)
    patient_profile: Mapped["Patient"] = relationship(back_populates="user", uselist=False)


class Doctor(Base):
    __tablename__ = "doctors"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, unique=True)
    full_name: Mapped[str] = mapped_column(String(128))
    specialty: Mapped[str] = mapped_column(String(128), default="Neyroonkolog")
    experience_years: Mapped[int] = mapped_column(Integer, default=0)
    success_rate: Mapped[float] = mapped_column(Float, default=0.0)
    avatar_color: Mapped[str | None] = mapped_column(String(32), nullable=True)

    user: Mapped["User"] = relationship(back_populates="doctor_profile")
    patients: Mapped[list["Patient"]] = relationship(back_populates="doctor")
    appointments: Mapped[list["Appointment"]] = relationship(back_populates="doctor")
    treatments: Mapped[list["Treatment"]] = relationship(back_populates="doctor")


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, unique=True)
    full_name: Mapped[str] = mapped_column(String(128))
    gender: Mapped[str] = mapped_column(String(16))
    age: Mapped[int] = mapped_column(Integer)
    diagnosis: Mapped[str] = mapped_column(String(128))
    stage: Mapped[StageEnum] = mapped_column(Enum(StageEnum))
    status: Mapped[PatientStatusEnum] = mapped_column(Enum(PatientStatusEnum))
    doctor_id: Mapped[int | None] = mapped_column(ForeignKey("doctors.id"), nullable=True)
    last_mri_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    tumor_growth_percent: Mapped[float] = mapped_column(Float, default=0.0)
    avatar_color: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="patient_profile")
    doctor: Mapped["Doctor"] = relationship(back_populates="patients")
    appointments: Mapped[list["Appointment"]] = relationship(back_populates="patient", cascade="all, delete-orphan")
    lab_results: Mapped[list["LabResult"]] = relationship(back_populates="patient", cascade="all, delete-orphan")
    treatments: Mapped[list["Treatment"]] = relationship(back_populates="patient", cascade="all, delete-orphan")
    scans: Mapped[list["MRIScan"]] = relationship(back_populates="patient", cascade="all, delete-orphan")
    alerts: Mapped[list["Alert"]] = relationship(back_populates="patient", cascade="all, delete-orphan")


class Appointment(Base):
    __tablename__ = "appointments"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"))
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id"))
    type: Mapped[str] = mapped_column(String(128))
    appt_date: Mapped[date] = mapped_column(Date)
    appt_time: Mapped[time] = mapped_column(Time)
    room: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[AppointmentStatusEnum] = mapped_column(Enum(AppointmentStatusEnum), default=AppointmentStatusEnum.scheduled)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    patient: Mapped["Patient"] = relationship(back_populates="appointments")
    doctor: Mapped["Doctor"] = relationship(back_populates="appointments")


class LabResult(Base):
    __tablename__ = "lab_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"))
    test_name: Mapped[str] = mapped_column(String(128))
    value: Mapped[str] = mapped_column(String(64))
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    reference_range: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[LabStatusEnum] = mapped_column(Enum(LabStatusEnum), default=LabStatusEnum.normal)
    result_date: Mapped[date] = mapped_column(Date, default=date.today)
    reviewed: Mapped[bool] = mapped_column(Boolean, default=False)
    lab_tech: Mapped[str | None] = mapped_column(String(128), nullable=True)

    patient: Mapped["Patient"] = relationship(back_populates="lab_results")


class Treatment(Base):
    __tablename__ = "treatments"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"))
    doctor_id: Mapped[int | None] = mapped_column(ForeignKey("doctors.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(128))
    protocol: Mapped[str | None] = mapped_column(String(128), nullable=True)
    medication: Mapped[str | None] = mapped_column(String(128), nullable=True)
    radiotherapy: Mapped[str | None] = mapped_column(String(128), nullable=True)
    sessions_done: Mapped[int] = mapped_column(Integer, default=0)
    sessions_total: Mapped[int] = mapped_column(Integer, default=0)
    next_session_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[TreatmentStatusEnum] = mapped_column(Enum(TreatmentStatusEnum), default=TreatmentStatusEnum.active)

    patient: Mapped["Patient"] = relationship(back_populates="treatments")
    doctor: Mapped["Doctor"] = relationship(back_populates="treatments")


class MRIScan(Base):
    __tablename__ = "mri_scans"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"))
    scan_date: Mapped[date] = mapped_column(Date, default=date.today)
    brain_region: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tumor_size_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    growth_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    signal_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tag: Mapped[str | None] = mapped_column(String(32), nullable=True)  # KRITIK / KUZATUV / NORMAL
    reviewed: Mapped[bool] = mapped_column(Boolean, default=False)
    radiologist_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    patient: Mapped["Patient"] = relationship(back_populates="scans")


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[AlertTypeEnum] = mapped_column(Enum(AlertTypeEnum))
    message: Mapped[str] = mapped_column(String(255))
    sub_message: Mapped[str | None] = mapped_column(String(255), nullable=True)
    patient_id: Mapped[int | None] = mapped_column(ForeignKey("patients.id"), nullable=True)
    target_role: Mapped[str | None] = mapped_column(String(16), nullable=True)  # admin/doctor/patient/None(all)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    patient: Mapped["Patient"] = relationship(back_populates="alerts")


class ClinicalTrial(Base):
    __tablename__ = "clinical_trials"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    phase: Mapped[str | None] = mapped_column(String(32), nullable=True)
    eligibility: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="Faol")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    role: Mapped[str] = mapped_column(String(8))  # "user" | "bot"
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class MLPrediction(Base):
    """MRI faylidan AI (ensemble CNN) o'sma turi bashorati natijasi."""
    __tablename__ = "ml_predictions"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"))
    uploaded_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    original_filename: Mapped[str] = mapped_column(String(255))
    source_format: Mapped[str] = mapped_column(String(16))
    predicted_class: Mapped[str] = mapped_column(String(64))
    confidence: Mapped[float] = mapped_column(Float)
    probabilities_json: Mapped[str] = mapped_column(Text)  # JSON: {class: prob}
    demo_mode: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    patient: Mapped["Patient"] = relationship()
    uploaded_by: Mapped["User"] = relationship()


class ClinicSettings(Base):
    """Singleton row (id always 1) holding the admin 'Sozlamalar' panel values."""
    __tablename__ = "clinic_settings"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    clinic_name: Mapped[str] = mapped_column(String(255), default="B-Cancer Tibbiy Markazi")
    address: Mapped[str] = mapped_column(String(255), default="Toshkent, Chilonzor, 17-mavze")
    email: Mapped[str] = mapped_column(String(128), default="admin@bcancer.uz")
    phone: Mapped[str] = mapped_column(String(32), default="+998 71 200 50 60")
    notify_new_patient: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_critical_lab: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_appt_reminder: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_daily_report: Mapped[bool] = mapped_column(Boolean, default=False)
