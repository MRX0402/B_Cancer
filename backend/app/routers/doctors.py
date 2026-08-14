from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user, require_roles
from ..security import hash_password

router = APIRouter(prefix="/api/doctors", tags=["doctors"])


def _to_out(d: models.Doctor) -> schemas.DoctorOut:
    return schemas.DoctorOut(
        id=d.id, full_name=d.full_name, specialty=d.specialty,
        experience_years=d.experience_years, success_rate=d.success_rate,
        avatar_color=d.avatar_color, patients_count=len(d.patients),
    )


@router.get("", response_model=list[schemas.DoctorOut])
def list_doctors(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return [_to_out(d) for d in db.query(models.Doctor).all()]


@router.get("/{doctor_id}", response_model=schemas.DoctorOut)
def get_doctor(doctor_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    d = db.get(models.Doctor, doctor_id)
    if not d:
        raise HTTPException(404, "Shifokor topilmadi")
    return _to_out(d)


@router.post("", response_model=schemas.DoctorOut, dependencies=[Depends(require_roles("admin"))])
def create_doctor(payload: schemas.DoctorCreate, db: Session = Depends(get_db)):
    d = models.Doctor(
        full_name=payload.full_name, specialty=payload.specialty,
        experience_years=payload.experience_years, success_rate=payload.success_rate,
        avatar_color=payload.avatar_color,
    )
    db.add(d)
    db.flush()

    if payload.username and payload.password:
        if db.query(models.User).filter(models.User.username == payload.username).first():
            raise HTTPException(400, "Bu username band")
        user = models.User(
            username=payload.username, password_hash=hash_password(payload.password),
            full_name=payload.full_name, role=models.RoleEnum.doctor, email=payload.email,
            avatar_initials="".join([w[0] for w in payload.full_name.split()[:2]]).upper(),
        )
        db.add(user)
        db.flush()
        d.user_id = user.id

    db.commit()
    db.refresh(d)
    return _to_out(d)


@router.put("/{doctor_id}", response_model=schemas.DoctorOut, dependencies=[Depends(require_roles("admin"))])
def update_doctor(doctor_id: int, payload: schemas.DoctorUpdate, db: Session = Depends(get_db)):
    d = db.get(models.Doctor, doctor_id)
    if not d:
        raise HTTPException(404, "Shifokor topilmadi")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(d, field, value)
    db.commit()
    db.refresh(d)
    return _to_out(d)


@router.delete("/{doctor_id}", dependencies=[Depends(require_roles("admin"))])
def delete_doctor(doctor_id: int, db: Session = Depends(get_db)):
    d = db.get(models.Doctor, doctor_id)
    if not d:
        raise HTTPException(404, "Shifokor topilmadi")
    db.delete(d)
    db.commit()
    return {"ok": True}
