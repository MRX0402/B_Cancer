from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user, require_roles
from ..security import hash_password

router = APIRouter(prefix="/api/patients", tags=["patients"])


def _to_out(p: models.Patient) -> schemas.PatientOut:
    return schemas.PatientOut(
        id=p.id, full_name=p.full_name, gender=p.gender, age=p.age,
        diagnosis=p.diagnosis, stage=p.stage, status=p.status,
        doctor_id=p.doctor_id, last_mri_date=p.last_mri_date,
        tumor_growth_percent=p.tumor_growth_percent, avatar_color=p.avatar_color,
        doctor_name=p.doctor.full_name if p.doctor else None,
    )


@router.get("", response_model=schemas.PatientListResponse)
def list_patients(
    search: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    stage: Optional[str] = None,
    doctor_id: Optional[int] = None,
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    q = db.query(models.Patient)

    # Doctors only see their own patients; patients only see themselves.
    if current_user.role == models.RoleEnum.doctor and current_user.doctor_profile:
        q = q.filter(models.Patient.doctor_id == current_user.doctor_profile.id)
    elif current_user.role == models.RoleEnum.patient and current_user.patient_profile:
        q = q.filter(models.Patient.id == current_user.patient_profile.id)

    if search:
        like = f"%{search}%"
        q = q.filter(or_(models.Patient.full_name.ilike(like), models.Patient.diagnosis.ilike(like)))
    if status_filter:
        q = q.filter(models.Patient.status == status_filter)
    if stage:
        q = q.filter(models.Patient.stage == stage)
    if doctor_id:
        q = q.filter(models.Patient.doctor_id == doctor_id)

    total = q.count()
    items = q.order_by(models.Patient.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return schemas.PatientListResponse(
        total=total, page=page, page_size=page_size, items=[_to_out(p) for p in items]
    )


@router.get("/{patient_id}", response_model=schemas.PatientOut)
def get_patient(patient_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    p = db.get(models.Patient, patient_id)
    if not p:
        raise HTTPException(404, "Bemor topilmadi")
    if current_user.role == models.RoleEnum.patient and (
        not current_user.patient_profile or current_user.patient_profile.id != p.id
    ):
        raise HTTPException(403, "Ruxsat yo'q")
    return _to_out(p)


@router.post("", response_model=schemas.PatientOut, dependencies=[Depends(require_roles("admin", "doctor"))])
def create_patient(payload: schemas.PatientCreate, db: Session = Depends(get_db)):
    p = models.Patient(
        full_name=payload.full_name, gender=payload.gender, age=payload.age,
        diagnosis=payload.diagnosis, stage=payload.stage, status=payload.status,
        doctor_id=payload.doctor_id, last_mri_date=payload.last_mri_date,
        tumor_growth_percent=payload.tumor_growth_percent, avatar_color=payload.avatar_color,
    )
    db.add(p)
    db.flush()

    if payload.username and payload.password:
        if db.query(models.User).filter(models.User.username == payload.username).first():
            raise HTTPException(400, "Bu username band")
        user = models.User(
            username=payload.username, password_hash=hash_password(payload.password),
            full_name=payload.full_name, role=models.RoleEnum.patient, email=payload.email,
            avatar_initials="".join([w[0] for w in payload.full_name.split()[:2]]).upper(),
        )
        db.add(user)
        db.flush()
        p.user_id = user.id

    db.commit()
    db.refresh(p)
    return _to_out(p)


@router.put("/{patient_id}", response_model=schemas.PatientOut, dependencies=[Depends(require_roles("admin", "doctor"))])
def update_patient(patient_id: int, payload: schemas.PatientUpdate, db: Session = Depends(get_db)):
    p = db.get(models.Patient, patient_id)
    if not p:
        raise HTTPException(404, "Bemor topilmadi")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(p, field, value)
    db.commit()
    db.refresh(p)
    return _to_out(p)


@router.delete("/{patient_id}", dependencies=[Depends(require_roles("admin"))])
def delete_patient(patient_id: int, db: Session = Depends(get_db)):
    p = db.get(models.Patient, patient_id)
    if not p:
        raise HTTPException(404, "Bemor topilmadi")
    db.delete(p)
    db.commit()
    return {"ok": True}
