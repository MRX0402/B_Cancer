from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user, require_roles

router = APIRouter(prefix="/api/trials", tags=["trials"])


@router.get("", response_model=list[schemas.ClinicalTrialOut])
def list_trials(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return db.query(models.ClinicalTrial).all()


@router.post("", response_model=schemas.ClinicalTrialOut, dependencies=[Depends(require_roles("admin", "doctor"))])
def create_trial(payload: schemas.ClinicalTrialCreate, db: Session = Depends(get_db)):
    t = models.ClinicalTrial(**payload.model_dump())
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


@router.delete("/{trial_id}", dependencies=[Depends(require_roles("admin"))])
def delete_trial(trial_id: int, db: Session = Depends(get_db)):
    t = db.get(models.ClinicalTrial, trial_id)
    if not t:
        raise HTTPException(404, "Klinik sinov topilmadi")
    db.delete(t)
    db.commit()
    return {"ok": True}
