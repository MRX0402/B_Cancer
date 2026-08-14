from typing import Optional
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user, require_roles

router = APIRouter(prefix="/api/appointments", tags=["appointments"])


def _to_out(a: models.Appointment) -> schemas.AppointmentOut:
    return schemas.AppointmentOut(
        id=a.id, patient_id=a.patient_id, doctor_id=a.doctor_id, type=a.type,
        appt_date=a.appt_date, appt_time=a.appt_time, room=a.room, status=a.status,
        notes=a.notes, patient_name=a.patient.full_name if a.patient else None,
        doctor_name=a.doctor.full_name if a.doctor else None,
    )


@router.get("", response_model=list[schemas.AppointmentOut])
def list_appointments(
    patient_id: Optional[int] = None,
    doctor_id: Optional[int] = None,
    on_date: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    q = db.query(models.Appointment)

    if current_user.role == models.RoleEnum.doctor and current_user.doctor_profile:
        q = q.filter(models.Appointment.doctor_id == current_user.doctor_profile.id)
    elif current_user.role == models.RoleEnum.patient and current_user.patient_profile:
        q = q.filter(models.Appointment.patient_id == current_user.patient_profile.id)

    if patient_id:
        q = q.filter(models.Appointment.patient_id == patient_id)
    if doctor_id:
        q = q.filter(models.Appointment.doctor_id == doctor_id)
    if on_date:
        q = q.filter(models.Appointment.appt_date == on_date)

    items = q.order_by(models.Appointment.appt_date, models.Appointment.appt_time).all()
    return [_to_out(a) for a in items]


@router.post("", response_model=schemas.AppointmentOut, dependencies=[Depends(require_roles("admin", "doctor"))])
def create_appointment(payload: schemas.AppointmentCreate, db: Session = Depends(get_db)):
    if not db.get(models.Patient, payload.patient_id):
        raise HTTPException(404, "Bemor topilmadi")
    if not db.get(models.Doctor, payload.doctor_id):
        raise HTTPException(404, "Shifokor topilmadi")
    a = models.Appointment(**payload.model_dump())
    db.add(a)
    db.commit()
    db.refresh(a)
    return _to_out(a)


@router.put("/{appointment_id}", response_model=schemas.AppointmentOut, dependencies=[Depends(require_roles("admin", "doctor"))])
def update_appointment(appointment_id: int, payload: schemas.AppointmentUpdate, db: Session = Depends(get_db)):
    a = db.get(models.Appointment, appointment_id)
    if not a:
        raise HTTPException(404, "Uchrashuv topilmadi")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(a, field, value)
    db.commit()
    db.refresh(a)
    return _to_out(a)


@router.delete("/{appointment_id}", dependencies=[Depends(require_roles("admin", "doctor"))])
def delete_appointment(appointment_id: int, db: Session = Depends(get_db)):
    a = db.get(models.Appointment, appointment_id)
    if not a:
        raise HTTPException(404, "Uchrashuv topilmadi")
    db.delete(a)
    db.commit()
    return {"ok": True}
