from datetime import date, time, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from .models import (
    RoleEnum, StageEnum, PatientStatusEnum, AppointmentStatusEnum,
    LabStatusEnum, AlertTypeEnum, TreatmentStatusEnum,
)


# ---------- Auth ----------

class LoginRequest(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    full_name: str
    role: RoleEnum
    email: Optional[str] = None
    phone: Optional[str] = None
    avatar_initials: Optional[str] = None
    avatar_color: Optional[str] = None
    doctor_id: Optional[int] = None
    patient_id: Optional[int] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------- Doctor ----------

class DoctorBase(BaseModel):
    full_name: str
    specialty: str = "Neyroonkolog"
    experience_years: int = 0
    success_rate: float = 0.0
    avatar_color: Optional[str] = None


class DoctorCreate(DoctorBase):
    username: Optional[str] = None
    password: Optional[str] = None
    email: Optional[str] = None


class DoctorUpdate(BaseModel):
    full_name: Optional[str] = None
    specialty: Optional[str] = None
    experience_years: Optional[int] = None
    success_rate: Optional[float] = None
    avatar_color: Optional[str] = None


class DoctorOut(DoctorBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    patients_count: int = 0


# ---------- Patient ----------

class PatientBase(BaseModel):
    full_name: str
    gender: str
    age: int
    diagnosis: str
    stage: StageEnum
    status: PatientStatusEnum
    doctor_id: Optional[int] = None
    last_mri_date: Optional[date] = None
    tumor_growth_percent: float = 0.0
    avatar_color: Optional[str] = None


class PatientCreate(PatientBase):
    username: Optional[str] = None
    password: Optional[str] = None
    email: Optional[str] = None


class PatientUpdate(BaseModel):
    full_name: Optional[str] = None
    gender: Optional[str] = None
    age: Optional[int] = None
    diagnosis: Optional[str] = None
    stage: Optional[StageEnum] = None
    status: Optional[PatientStatusEnum] = None
    doctor_id: Optional[int] = None
    last_mri_date: Optional[date] = None
    tumor_growth_percent: Optional[float] = None


class PatientOut(PatientBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    doctor_name: Optional[str] = None


class PatientListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[PatientOut]


# ---------- Appointment ----------

class AppointmentBase(BaseModel):
    patient_id: int
    doctor_id: int
    type: str
    appt_date: date
    appt_time: time
    room: Optional[str] = None
    status: AppointmentStatusEnum = AppointmentStatusEnum.scheduled
    notes: Optional[str] = None


class AppointmentCreate(AppointmentBase):
    pass


class AppointmentUpdate(BaseModel):
    type: Optional[str] = None
    appt_date: Optional[date] = None
    appt_time: Optional[time] = None
    room: Optional[str] = None
    status: Optional[AppointmentStatusEnum] = None
    notes: Optional[str] = None


class AppointmentOut(AppointmentBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    patient_name: Optional[str] = None
    doctor_name: Optional[str] = None


# ---------- Lab result ----------

class LabResultBase(BaseModel):
    patient_id: int
    test_name: str
    value: str
    unit: Optional[str] = None
    reference_range: Optional[str] = None
    status: LabStatusEnum = LabStatusEnum.normal
    result_date: date = date.today()
    lab_tech: Optional[str] = None


class LabResultCreate(LabResultBase):
    pass


class LabResultUpdate(BaseModel):
    status: Optional[LabStatusEnum] = None
    reviewed: Optional[bool] = None


class LabResultOut(LabResultBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    reviewed: bool = False
    patient_name: Optional[str] = None


# ---------- Treatment ----------

class TreatmentBase(BaseModel):
    patient_id: int
    doctor_id: Optional[int] = None
    name: str
    protocol: Optional[str] = None
    medication: Optional[str] = None
    radiotherapy: Optional[str] = None
    sessions_done: int = 0
    sessions_total: int = 0
    next_session_date: Optional[date] = None
    status: TreatmentStatusEnum = TreatmentStatusEnum.active


class TreatmentCreate(TreatmentBase):
    pass


class TreatmentUpdate(BaseModel):
    name: Optional[str] = None
    protocol: Optional[str] = None
    medication: Optional[str] = None
    radiotherapy: Optional[str] = None
    sessions_done: Optional[int] = None
    sessions_total: Optional[int] = None
    next_session_date: Optional[date] = None
    status: Optional[TreatmentStatusEnum] = None


class TreatmentOut(TreatmentBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    patient_name: Optional[str] = None
    doctor_name: Optional[str] = None


# ---------- MRI scan ----------

class MRIScanBase(BaseModel):
    patient_id: int
    scan_date: date = date.today()
    brain_region: Optional[str] = None
    tumor_size_cm: Optional[float] = None
    growth_percent: Optional[float] = None
    signal_type: Optional[str] = None
    tag: Optional[str] = None
    reviewed: bool = False
    radiologist_notes: Optional[str] = None


class MRIScanCreate(MRIScanBase):
    pass


class MRIScanUpdate(BaseModel):
    reviewed: Optional[bool] = None
    radiologist_notes: Optional[str] = None
    tag: Optional[str] = None


class MRIScanOut(MRIScanBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    patient_name: Optional[str] = None


# ---------- Alert ----------

class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    type: AlertTypeEnum
    message: str
    sub_message: Optional[str] = None
    patient_id: Optional[int] = None
    target_role: Optional[str] = None
    is_read: bool
    created_at: datetime


class AlertCreate(BaseModel):
    type: AlertTypeEnum
    message: str
    sub_message: Optional[str] = None
    patient_id: Optional[int] = None
    target_role: Optional[str] = None


# ---------- Clinical trial ----------

class ClinicalTrialBase(BaseModel):
    name: str
    description: Optional[str] = None
    phase: Optional[str] = None
    eligibility: Optional[str] = None
    status: str = "Faol"


class ClinicalTrialCreate(ClinicalTrialBase):
    pass


class ClinicalTrialOut(ClinicalTrialBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


# ---------- Chat ----------

class ChatRequest(BaseModel):
    message: str


class ChatMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    role: str
    content: str
    created_at: datetime


# ---------- Settings / account ----------

class ClinicSettingsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    clinic_name: str
    address: str
    email: str
    phone: str
    notify_new_patient: bool
    notify_critical_lab: bool
    notify_appt_reminder: bool
    notify_daily_report: bool


class ClinicSettingsUpdate(BaseModel):
    clinic_name: Optional[str] = None
    address: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    notify_new_patient: Optional[bool] = None
    notify_critical_lab: Optional[bool] = None
    notify_appt_reminder: Optional[bool] = None
    notify_daily_report: Optional[bool] = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


# ---------- ML prediction ----------

class MLPredictionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    patient_id: int
    patient_name: Optional[str] = None
    original_filename: str
    source_format: str
    predicted_class: str
    confidence: float
    probabilities: dict[str, float]
    demo_mode: bool
    demo_reason: Optional[str] = None
    created_at: datetime


class MLModelStatus(BaseModel):
    loaded: bool
    torch_available: bool
    weights_path: str
    error: Optional[str] = None


# ---------- Dashboard ----------

class StatCard(BaseModel):
    label: str
    value: str
    change: Optional[str] = None
    trend: Optional[str] = None  # up/down/neutral


class AdminDashboardOut(BaseModel):
    stats: list[StatCard]
    stage_distribution: dict[str, float]
    monthly_cases: dict[str, list]
    tumor_types: dict[str, list]
    alerts: list[AlertOut]


class DoctorDashboardOut(BaseModel):
    stats: list[StatCard]
    critical_patients: list[PatientOut]
    today_appointments: list[AppointmentOut]
    alerts: list[AlertOut]


class PatientDashboardOut(BaseModel):
    profile: PatientOut
    upcoming_appointments: list[AppointmentOut]
    latest_scan: Optional[MRIScanOut] = None
    active_treatment: Optional[TreatmentOut] = None
    lab_results: list[LabResultOut]
