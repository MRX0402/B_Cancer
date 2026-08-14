from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..security import verify_password, create_access_token, hash_password
from ..deps import get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _user_out(user: models.User) -> schemas.UserOut:
    return schemas.UserOut(
        id=user.id,
        username=user.username,
        full_name=user.full_name,
        role=user.role,
        email=user.email,
        phone=user.phone,
        avatar_initials=user.avatar_initials,
        avatar_color=user.avatar_color,
        doctor_id=user.doctor_profile.id if user.doctor_profile else None,
        patient_id=user.patient_profile.id if user.patient_profile else None,
    )


@router.post("/login", response_model=schemas.TokenResponse)
def login(payload: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == payload.username).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Login yoki parol noto'g'ri",
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Hisob faol emas")

    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    return schemas.TokenResponse(access_token=token, user=_user_out(user))


@router.post("/token", response_model=schemas.TokenResponse, include_in_schema=False)
def login_oauth2_form(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """OAuth2-compatible token endpoint (used automatically by /docs 'Authorize' button)."""
    return login(schemas.LoginRequest(username=form_data.username, password=form_data.password), db)


@router.get("/me", response_model=schemas.UserOut)
def me(current_user: models.User = Depends(get_current_user)):
    return _user_out(current_user)


@router.post("/change-password")
def change_password(
    payload: schemas.ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Joriy parol noto'g'ri")
    current_user.password_hash = hash_password(payload.new_password)
    db.commit()
    return {"ok": True}
