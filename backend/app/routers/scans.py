from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user, require_roles

router = APIRouter(prefix="/api/scans", tags=["scans"])


def _to_out(s: models.MRIScan) -> schemas.MRIScanOut:
    return schemas.MRIScanOut(
        id=s.id, patient_id=s.patient_id, scan_date=s.scan_date,
        brain_region=s.brain_region, tumor_size_cm=s.tumor_size_cm,
        growth_percent=s.growth_percent, signal_type=s.signal_type, tag=s.tag,
        reviewed=s.reviewed, radiologist_notes=s.radiologist_notes,
        patient_name=s.patient.full_name if s.patient else None,
    )


@router.get("", response_model=list[schemas.MRIScanOut])
def list_scans(
    patient_id: Optional[int] = None,
    reviewed: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    q = db.query(models.MRIScan)
    if current_user.role == models.RoleEnum.patient and current_user.patient_profile:
        q = q.filter(models.MRIScan.patient_id == current_user.patient_profile.id)
    elif patient_id:
        q = q.filter(models.MRIScan.patient_id == patient_id)
    if reviewed is not None:
        q = q.filter(models.MRIScan.reviewed == reviewed)
    items = q.order_by(models.MRIScan.scan_date.desc()).all()
    return [_to_out(s) for s in items]


@router.post("", response_model=schemas.MRIScanOut, dependencies=[Depends(require_roles("admin", "doctor"))])
def create_scan(payload: schemas.MRIScanCreate, db: Session = Depends(get_db)):
    if not db.get(models.Patient, payload.patient_id):
        raise HTTPException(404, "Bemor topilmadi")
    s = models.MRIScan(**payload.model_dump())
    db.add(s)
    db.commit()
    db.refresh(s)
    return _to_out(s)


@router.put("/{scan_id}", response_model=schemas.MRIScanOut, dependencies=[Depends(require_roles("admin", "doctor"))])
def update_scan(scan_id: int, payload: schemas.MRIScanUpdate, db: Session = Depends(get_db)):
    s = db.get(models.MRIScan, scan_id)
    if not s:
        raise HTTPException(404, "Skaner topilmadi")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(s, field, value)
    db.commit()
    db.refresh(s)
    return _to_out(s)
