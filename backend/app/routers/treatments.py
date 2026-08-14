from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user, require_roles

router = APIRouter(prefix="/api/treatments", tags=["treatments"])


def _to_out(t: models.Treatment) -> schemas.TreatmentOut:
    return schemas.TreatmentOut(
        id=t.id, patient_id=t.patient_id, doctor_id=t.doctor_id, name=t.name,
        protocol=t.protocol, medication=t.medication, radiotherapy=t.radiotherapy,
        sessions_done=t.sessions_done, sessions_total=t.sessions_total,
        next_session_date=t.next_session_date, status=t.status,
        patient_name=t.patient.full_name if t.patient else None,
        doctor_name=t.doctor.full_name if t.doctor else None,
    )


@router.get("", response_model=list[schemas.TreatmentOut])
def list_treatments(
    patient_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    q = db.query(models.Treatment)
    if current_user.role == models.RoleEnum.patient and current_user.patient_profile:
        q = q.filter(models.Treatment.patient_id == current_user.patient_profile.id)
    elif current_user.role == models.RoleEnum.doctor and current_user.doctor_profile:
        q = q.filter(models.Treatment.doctor_id == current_user.doctor_profile.id)
    elif patient_id:
        q = q.filter(models.Treatment.patient_id == patient_id)
    return [_to_out(t) for t in q.all()]


@router.post("", response_model=schemas.TreatmentOut, dependencies=[Depends(require_roles("admin", "doctor"))])
def create_treatment(payload: schemas.TreatmentCreate, db: Session = Depends(get_db)):
    if not db.get(models.Patient, payload.patient_id):
        raise HTTPException(404, "Bemor topilmadi")
    t = models.Treatment(**payload.model_dump())
    db.add(t)
    db.commit()
    db.refresh(t)
    return _to_out(t)


@router.put("/{treatment_id}", response_model=schemas.TreatmentOut, dependencies=[Depends(require_roles("admin", "doctor"))])
def update_treatment(treatment_id: int, payload: schemas.TreatmentUpdate, db: Session = Depends(get_db)):
    t = db.get(models.Treatment, treatment_id)
    if not t:
        raise HTTPException(404, "Davolash rejasi topilmadi")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(t, field, value)
    db.commit()
    db.refresh(t)
    return _to_out(t)


@router.delete("/{treatment_id}", dependencies=[Depends(require_roles("admin", "doctor"))])
def delete_treatment(treatment_id: int, db: Session = Depends(get_db)):
    t = db.get(models.Treatment, treatment_id)
    if not t:
        raise HTTPException(404, "Davolash rejasi topilmadi")
    db.delete(t)
    db.commit()
    return {"ok": True}
