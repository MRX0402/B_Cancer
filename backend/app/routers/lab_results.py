from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user, require_roles

router = APIRouter(prefix="/api/lab-results", tags=["lab-results"])


def _to_out(lr: models.LabResult) -> schemas.LabResultOut:
    return schemas.LabResultOut(
        id=lr.id, patient_id=lr.patient_id, test_name=lr.test_name, value=lr.value,
        unit=lr.unit, reference_range=lr.reference_range, status=lr.status,
        result_date=lr.result_date, lab_tech=lr.lab_tech, reviewed=lr.reviewed,
        patient_name=lr.patient.full_name if lr.patient else None,
    )


@router.get("", response_model=list[schemas.LabResultOut])
def list_lab_results(
    patient_id: Optional[int] = None,
    unreviewed_only: bool = False,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    q = db.query(models.LabResult)
    if current_user.role == models.RoleEnum.patient and current_user.patient_profile:
        q = q.filter(models.LabResult.patient_id == current_user.patient_profile.id)
    elif current_user.role == models.RoleEnum.doctor and current_user.doctor_profile:
        q = q.join(models.Patient).filter(models.Patient.doctor_id == current_user.doctor_profile.id)
        if patient_id:
            q = q.filter(models.LabResult.patient_id == patient_id)
    elif patient_id:
        q = q.filter(models.LabResult.patient_id == patient_id)
    if unreviewed_only:
        q = q.filter(models.LabResult.reviewed.is_(False))
    items = q.order_by(models.LabResult.result_date.desc()).all()
    return [_to_out(lr) for lr in items]


@router.post("", response_model=schemas.LabResultOut, dependencies=[Depends(require_roles("admin", "doctor"))])
def create_lab_result(payload: schemas.LabResultCreate, db: Session = Depends(get_db)):
    if not db.get(models.Patient, payload.patient_id):
        raise HTTPException(404, "Bemor topilmadi")
    lr = models.LabResult(**payload.model_dump())
    db.add(lr)
    db.commit()
    db.refresh(lr)
    return _to_out(lr)


@router.patch("/{lab_result_id}", response_model=schemas.LabResultOut, dependencies=[Depends(require_roles("admin", "doctor"))])
def update_lab_result(lab_result_id: int, payload: schemas.LabResultUpdate, db: Session = Depends(get_db)):
    lr = db.get(models.LabResult, lab_result_id)
    if not lr:
        raise HTTPException(404, "Natija topilmadi")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(lr, field, value)
    db.commit()
    db.refresh(lr)
    return _to_out(lr)


@router.delete("/{lab_result_id}", dependencies=[Depends(require_roles("admin", "doctor"))])
def delete_lab_result(lab_result_id: int, db: Session = Depends(get_db)):
    lr = db.get(models.LabResult, lab_result_id)
    if not lr:
        raise HTTPException(404, "Natija topilmadi")
    db.delete(lr)
    db.commit()
    return {"ok": True}
