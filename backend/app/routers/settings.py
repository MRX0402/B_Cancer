from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import require_roles

router = APIRouter(prefix="/api/settings", tags=["settings"])


def _get_or_create(db: Session) -> models.ClinicSettings:
    s = db.get(models.ClinicSettings, 1)
    if not s:
        s = models.ClinicSettings(id=1)
        db.add(s)
        db.commit()
        db.refresh(s)
    return s


@router.get("", response_model=schemas.ClinicSettingsOut, dependencies=[Depends(require_roles("admin"))])
def get_settings(db: Session = Depends(get_db)):
    return _get_or_create(db)


@router.put("", response_model=schemas.ClinicSettingsOut, dependencies=[Depends(require_roles("admin"))])
def update_settings(payload: schemas.ClinicSettingsUpdate, db: Session = Depends(get_db)):
    s = _get_or_create(db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(s, field, value)
    db.commit()
    db.refresh(s)
    return s
