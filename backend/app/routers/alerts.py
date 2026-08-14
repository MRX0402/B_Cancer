from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user, require_roles

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.get("", response_model=list[schemas.AlertOut])
def list_alerts(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    q = db.query(models.Alert)
    q = q.filter(
        (models.Alert.target_role.is_(None)) | (models.Alert.target_role == current_user.role.value)
    )
    if current_user.role == models.RoleEnum.patient and current_user.patient_profile:
        q = q.filter(
            (models.Alert.patient_id.is_(None)) | (models.Alert.patient_id == current_user.patient_profile.id)
        )
    return q.order_by(models.Alert.created_at.desc()).limit(50).all()


@router.post("", response_model=schemas.AlertOut, dependencies=[Depends(require_roles("admin", "doctor"))])
def create_alert(payload: schemas.AlertCreate, db: Session = Depends(get_db)):
    a = models.Alert(**payload.model_dump())
    db.add(a)
    db.commit()
    db.refresh(a)
    return a


@router.post("/{alert_id}/read", response_model=schemas.AlertOut)
def mark_read(alert_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    a = db.get(models.Alert, alert_id)
    if not a:
        raise HTTPException(404, "Ogohlantirish topilmadi")
    a.is_read = True
    db.commit()
    db.refresh(a)
    return a
