from collections import Counter
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user, require_roles
from .patients import _to_out as patient_to_out
from .appointments import _to_out as appt_to_out
from .scans import _to_out as scan_to_out
from .lab_results import _to_out as lab_to_out
from .treatments import _to_out as tx_to_out

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def _stage_distribution(db: Session, patients: list[models.Patient]) -> dict[str, float]:
    total = len(patients) or 1
    counts = Counter(p.stage.value for p in patients)
    return {stage.value: round(counts.get(stage.value, 0) / total * 100, 1) for stage in models.StageEnum}


def _monthly_cases(patients: list[models.Patient]) -> dict[str, list]:
    counts = Counter(p.created_at.strftime("%Y-%m") for p in patients if p.created_at)
    labels = sorted(counts.keys())
    return {"labels": labels, "data": [counts[k] for k in labels]}


def _tumor_types(patients: list[models.Patient]) -> dict[str, list]:
    counts = Counter(p.diagnosis for p in patients)
    labels = list(counts.keys())
    return {"labels": labels, "data": [counts[k] for k in labels]}


@router.get("/admin", response_model=schemas.AdminDashboardOut, dependencies=[Depends(require_roles("admin"))])
def admin_dashboard(db: Session = Depends(get_db)):
    patients = db.query(models.Patient).all()
    doctors = db.query(models.Doctor).all()
    today = date.today()
    today_appts = db.query(models.Appointment).filter(models.Appointment.appt_date == today).count()
    critical = sum(1 for p in patients if p.status == models.PatientStatusEnum.kritik)
    remission = sum(1 for p in patients if p.status == models.PatientStatusEnum.remissiya)
    success_rate = round((remission / len(patients) * 100), 1) if patients else 0.0
    pending_labs = db.query(models.LabResult).filter(models.LabResult.reviewed.is_(False)).count()
    chemo_today = db.query(models.Treatment).filter(models.Treatment.next_session_date == today).count()

    stats = [
        schemas.StatCard(label="Jami bemorlar", value=str(len(patients)), change=None, trend="neutral"),
        schemas.StatCard(label="Faol davolanish", value=str(sum(1 for p in patients if p.status in (models.PatientStatusEnum.davolanmoqda, models.PatientStatusEnum.kritik))), change=f"{critical} kritik holat", trend="dn" if critical else "neutral"),
        schemas.StatCard(label="Shifokorlar", value=str(len(doctors)), trend="neutral"),
        schemas.StatCard(label="Muvaffaqiyat darajasi", value=f"{success_rate}%", trend="up"),
        schemas.StatCard(label="Bugungi uchrashuvlar", value=str(today_appts), trend="neutral"),
        schemas.StatCard(label="Kutilayotgan tahlil", value=str(pending_labs), trend="dn" if pending_labs else "neutral"),
        schemas.StatCard(label="Kimyoterapiya seansi", value=str(chemo_today), trend="neutral"),
    ]

    alerts = db.query(models.Alert).filter(
        (models.Alert.target_role.is_(None)) | (models.Alert.target_role == "admin")
    ).order_by(models.Alert.created_at.desc()).limit(10).all()

    return schemas.AdminDashboardOut(
        stats=stats,
        stage_distribution=_stage_distribution(db, patients),
        monthly_cases=_monthly_cases(patients),
        tumor_types=_tumor_types(patients),
        alerts=alerts,
    )


@router.get("/doctor", response_model=schemas.DoctorDashboardOut, dependencies=[Depends(require_roles("doctor"))])
def doctor_dashboard(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    doctor = current_user.doctor_profile
    if not doctor:
        raise HTTPException(400, "Shifokor profili topilmadi")

    patients = db.query(models.Patient).filter(models.Patient.doctor_id == doctor.id).all()
    today = date.today()
    today_appts_q = db.query(models.Appointment).filter(
        models.Appointment.doctor_id == doctor.id, models.Appointment.appt_date == today
    )
    today_appts = today_appts_q.all()
    completed_today = sum(1 for a in today_appts if a.status == models.AppointmentStatusEnum.completed)
    pending_labs = db.query(models.LabResult).join(models.Patient).filter(
        models.Patient.doctor_id == doctor.id, models.LabResult.reviewed.is_(False)
    ).count()

    stats = [
        schemas.StatCard(label="Bemorlarim", value=str(len(patients)), trend="neutral"),
        schemas.StatCard(label="Bugungi uchrashuvlar", value=str(len(today_appts)), change=f"{completed_today} tugallandi", trend="neutral"),
        schemas.StatCard(label="Kutilayotgan tahlil", value=str(pending_labs), trend="dn" if pending_labs else "neutral"),
        schemas.StatCard(label="Bu oy davolanganlar", value=str(sum(1 for p in patients if p.status == models.PatientStatusEnum.remissiya)), trend="up"),
    ]

    critical_patients = [p for p in patients if p.status == models.PatientStatusEnum.kritik][:5]

    alerts = db.query(models.Alert).filter(
        (models.Alert.target_role.is_(None)) | (models.Alert.target_role == "doctor")
    ).order_by(models.Alert.created_at.desc()).limit(10).all()

    return schemas.DoctorDashboardOut(
        stats=stats,
        critical_patients=[patient_to_out(p) for p in critical_patients],
        today_appointments=[appt_to_out(a) for a in today_appts],
        alerts=alerts,
    )


@router.get("/patient", response_model=schemas.PatientDashboardOut, dependencies=[Depends(require_roles("patient"))])
def patient_dashboard(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    patient = current_user.patient_profile
    if not patient:
        raise HTTPException(400, "Bemor profili topilmadi")

    today = date.today()
    upcoming = db.query(models.Appointment).filter(
        models.Appointment.patient_id == patient.id, models.Appointment.appt_date >= today
    ).order_by(models.Appointment.appt_date).all()

    latest_scan = db.query(models.MRIScan).filter(
        models.MRIScan.patient_id == patient.id
    ).order_by(models.MRIScan.scan_date.desc()).first()

    active_treatment = db.query(models.Treatment).filter(
        models.Treatment.patient_id == patient.id, models.Treatment.status == models.TreatmentStatusEnum.active
    ).first()

    lab_results = db.query(models.LabResult).filter(
        models.LabResult.patient_id == patient.id
    ).order_by(models.LabResult.result_date.desc()).all()

    return schemas.PatientDashboardOut(
        profile=patient_to_out(patient),
        upcoming_appointments=[appt_to_out(a) for a in upcoming],
        latest_scan=scan_to_out(latest_scan) if latest_scan else None,
        active_treatment=tx_to_out(active_treatment) if active_treatment else None,
        lab_results=[lab_to_out(lr) for lr in lab_results],
    )
