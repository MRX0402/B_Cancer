import json
import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user
from ..ml import inference
from ..ml.preprocess import process_upload, PreprocessError, SUPPORTED_EXTENSIONS

router = APIRouter(prefix="/api/ml", tags=["ml"])

MAX_UPLOAD_MB = 60


def _to_out(p: models.MLPrediction) -> schemas.MLPredictionOut:
    return schemas.MLPredictionOut(
        id=p.id, patient_id=p.patient_id,
        patient_name=p.patient.full_name if p.patient else None,
        original_filename=p.original_filename, source_format=p.source_format,
        predicted_class=p.predicted_class, confidence=p.confidence,
        probabilities=json.loads(p.probabilities_json), demo_mode=p.demo_mode,
        created_at=p.created_at,
    )


@router.get("/status", response_model=schemas.MLModelStatus)
def status(current_user: models.User = Depends(get_current_user)):
    return inference.model_status()


@router.post("/predict", response_model=schemas.MLPredictionOut)
async def predict(
    patient_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    # Bemor faqat o'zi uchun yuklay oladi; admin/doctor istalgan bemor uchun.
    if current_user.role == models.RoleEnum.patient:
        if not current_user.patient_profile or current_user.patient_profile.id != patient_id:
            raise HTTPException(403, "Faqat o'zingiz uchun MRI yuklashingiz mumkin")

    patient = db.get(models.Patient, patient_id)
    if not patient:
        raise HTTPException(404, "Bemor topilmadi")

    ext = os.path.splitext(file.filename.lower())[1]
    if file.filename.lower().endswith(".nii.gz"):
        ext = ".nii.gz"
    if ext not in SUPPORTED_EXTENSIONS and ext != ".nii.gz":
        raise HTTPException(
            400,
            "Qo'llab-quvvatlanmaydigan format. Ruxsat etilgan: DICOM (.dcm), JPEG (.jpg/.jpeg), "
            "PNG (.png), NIfTI (.nii/.nii.gz), .mat",
        )

    data = await file.read()
    if len(data) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(400, f"Fayl juda katta (max {MAX_UPLOAD_MB} MB)")

    mat_path = None
    try:
        processed_image, mat_path = process_upload(data, file.filename)
        result = inference.predict(processed_image)
    except PreprocessError as e:
        raise HTTPException(400, str(e))
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        raise HTTPException(500, f"Bashorat qilishda xatolik: {e}")
    finally:
        if mat_path and os.path.exists(mat_path):
            try:
                os.remove(mat_path)
            except OSError:
                pass

    record = models.MLPrediction(
        patient_id=patient_id,
        uploaded_by_id=current_user.id,
        original_filename=file.filename,
        source_format=ext.lstrip("."),
        predicted_class=result["predicted_class"],
        confidence=result["confidence"],
        probabilities_json=json.dumps(result["probabilities"]),
        demo_mode=result["demo_mode"],
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    out = _to_out(record)
    out.demo_reason = result.get("demo_reason")
    return out


@router.get("/predictions", response_model=list[schemas.MLPredictionOut])
def list_predictions(
    patient_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    q = db.query(models.MLPrediction)
    if current_user.role == models.RoleEnum.patient and current_user.patient_profile:
        q = q.filter(models.MLPrediction.patient_id == current_user.patient_profile.id)
    elif current_user.role == models.RoleEnum.doctor and current_user.doctor_profile:
        q = q.join(models.Patient).filter(models.Patient.doctor_id == current_user.doctor_profile.id)
        if patient_id:
            q = q.filter(models.MLPrediction.patient_id == patient_id)
    elif patient_id:
        q = q.filter(models.MLPrediction.patient_id == patient_id)
    items = q.order_by(models.MLPrediction.created_at.desc()).all()
    return [_to_out(p) for p in items]
