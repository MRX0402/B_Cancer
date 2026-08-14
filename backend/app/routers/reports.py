import csv
import io
from collections import Counter

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..deps import require_roles

router = APIRouter(prefix="/api/reports", tags=["reports"])


def _csv_response(rows: list[list], header: list[str], filename: str) -> StreamingResponse:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(header)
    writer.writerows(rows)
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/export/patients.csv", dependencies=[Depends(require_roles("admin", "doctor"))])
def export_patients_csv(db: Session = Depends(get_db)):
    patients = db.query(models.Patient).all()
    rows = [
        [p.id, p.full_name, p.gender, p.age, p.diagnosis, p.stage.value, p.status.value,
         p.doctor.full_name if p.doctor else "", p.last_mri_date, p.tumor_growth_percent]
        for p in patients
    ]
    header = ["ID", "Ism", "Jins", "Yosh", "Tashxis", "Bosqich", "Holat", "Shifokor", "So'nggi MRI", "O'sish %"]
    return _csv_response(rows, header, "bemorlar_royxati.csv")


@router.get("/export/monthly.csv", dependencies=[Depends(require_roles("admin"))])
def export_monthly_csv(db: Session = Depends(get_db)):
    patients = db.query(models.Patient).all()
    counts = Counter(p.created_at.strftime("%Y-%m") for p in patients if p.created_at)
    rows = [[month, count] for month, count in sorted(counts.items())]
    return _csv_response(rows, ["Oy", "Yangi bemorlar"], "oylik_statistika.csv")
