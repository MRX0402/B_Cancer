"""
Seed the database with demo data that mirrors the hardcoded content in the
original index.html (same patients, doctors, and the three demo login
accounts: admin / dr.alimova / bemor1).

Run with:  python -m app.seed
"""
from datetime import date, time, timedelta

from .database import Base, engine, SessionLocal
from . import models
from .security import hash_password

Base.metadata.create_all(bind=engine)


def run():
    db = SessionLocal()
    try:
        if db.query(models.User).count() > 0:
            print("Seed skipped: users already exist.")
            return

        today = date.today()

        # ---- Doctors + their login users ----
        doc_alimova_user = models.User(
            username="dr.alimova", password_hash=hash_password("Doctor@123"),
            full_name="Dr. Dilnoza Alimova", role=models.RoleEnum.doctor,
            avatar_initials="DA", avatar_color="#dbeafe",
        )
        doc_petrov_user = models.User(
            username="dr.petrov", password_hash=hash_password("Doctor@123"),
            full_name="Dr. Alexei Petrov", role=models.RoleEnum.doctor,
            avatar_initials="AP", avatar_color="#d1fae5",
        )
        doc_karimov_user = models.User(
            username="dr.karimov", password_hash=hash_password("Doctor@123"),
            full_name="Dr. Mirzo Karimov", role=models.RoleEnum.doctor,
            avatar_initials="MK", avatar_color="#ede9fe",
        )
        db.add_all([doc_alimova_user, doc_petrov_user, doc_karimov_user])
        db.flush()

        doc_alimova = models.Doctor(
            user_id=doc_alimova_user.id, full_name="Dr. Dilnoza Alimova",
            specialty="Neyroonkolog", experience_years=12, success_rate=98.0,
            avatar_color="#dbeafe",
        )
        doc_petrov = models.Doctor(
            user_id=doc_petrov_user.id, full_name="Dr. Alexei Petrov",
            specialty="Neyrojarrohi", experience_years=15, success_rate=95.0,
            avatar_color="#d1fae5",
        )
        doc_karimov = models.Doctor(
            user_id=doc_karimov_user.id, full_name="Dr. Mirzo Karimov",
            specialty="Radiolog", experience_years=8, success_rate=91.0,
            avatar_color="#ede9fe",
        )
        # Extra doctors shown in the UI's doctor grid (no login accounts needed for the demo)
        doc_yusupova = models.Doctor(
            full_name="Dr. Zarina Yusupova", specialty="Neyropatolog",
            experience_years=10, success_rate=93.0, avatar_color="#ccfbf1",
        )
        doc_nazarov = models.Doctor(
            full_name="Dr. Jasur Nazarov", specialty="Onkolog",
            experience_years=7, success_rate=89.0, avatar_color="#ffedd5",
        )
        doc_bekova = models.Doctor(
            full_name="Dr. Sofia Bekova", specialty="Radioonkolog",
            experience_years=6, success_rate=88.0, avatar_color="#fee2e2",
        )
        db.add_all([doc_alimova, doc_petrov, doc_karimov, doc_yusupova, doc_nazarov, doc_bekova])
        db.flush()

        # ---- Admin user ----
        admin_user = models.User(
            username="admin", password_hash=hash_password("Admin@123"),
            full_name="Super Admin", role=models.RoleEnum.admin,
            avatar_initials="SA", avatar_color="#3b82f6",
        )
        db.add(admin_user)

        # ---- Patients ----
        def mk_patient(full_name, gender, age, diagnosis, stage, status, doctor, mri_days_ago, growth, color):
            return models.Patient(
                full_name=full_name, gender=gender, age=age, diagnosis=diagnosis,
                stage=stage, status=status, doctor_id=doctor.id if doctor else None,
                last_mri_date=today - timedelta(days=mri_days_ago),
                tumor_growth_percent=growth, avatar_color=color,
            )

        alex = mk_patient("Alex Oxford", "Erkak", 32, "Glioblastoma", models.StageEnum.IV, models.PatientStatusEnum.kritik, doc_alimova, 0, 12.0, "#fee2e2")
        sarah = mk_patient("Sarah Johnson", "Ayol", 45, "Meningioma", models.StageEnum.II, models.PatientStatusEnum.davolanmoqda, doc_petrov, 4, 3.0, "#dbeafe")
        james = mk_patient("James Wilson", "Erkak", 58, "Astrocytoma", models.StageEnum.I, models.PatientStatusEnum.remissiya, doc_karimov, 6, -5.0, "#d1fae5")
        maria = mk_patient("Maria Garcia", "Ayol", 39, "Oligodendroglioma", models.StageEnum.III, models.PatientStatusEnum.davolanmoqda, doc_alimova, 9, 3.0, "#ede9fe")
        david = mk_patient("David Kim", "Erkak", 51, "Ependymoma", models.StageEnum.II, models.PatientStatusEnum.barqaror, doc_petrov, 12, 0.0, "#ccfbf1")
        lisa_a = mk_patient("Lisa Anderson", "Ayol", 66, "Glioblastoma", models.StageEnum.IV, models.PatientStatusEnum.kritik, doc_karimov, 14, 9.0, "#fee2e2")
        robert = mk_patient("Robert Brown", "Erkak", 44, "Meningioma", models.StageEnum.I, models.PatientStatusEnum.remissiya, doc_alimova, 16, -5.0, "#dbeafe")
        emma = mk_patient("Emma Davis", "Ayol", 29, "Astrocytoma", models.StageEnum.III, models.PatientStatusEnum.kuzatuv, doc_petrov, 19, 2.0, "#ffedd5")
        lisa_t = mk_patient("Lisa Thompson", "Ayol", 52, "Astrocytoma", models.StageEnum.II, models.PatientStatusEnum.barqaror, doc_alimova, 4, -2.0, "#d1fae5")
        kevin = mk_patient("Kevin Park", "Erkak", 47, "Meningioma", models.StageEnum.II, models.PatientStatusEnum.yangi, doc_alimova, 0, 0.0, "#ccfbf1")

        db.add_all([alex, sarah, james, maria, david, lisa_a, robert, emma, lisa_t, kevin])
        db.flush()

        # ---- Patient login user (bemor1 -> Alex Oxford) ----
        patient_user = models.User(
            username="bemor1", password_hash=hash_password("Bemor@123"),
            full_name="Alex Oxford", role=models.RoleEnum.patient,
            avatar_initials="AO", avatar_color="#fee2e2",
        )
        db.add(patient_user)
        db.flush()
        alex.user_id = patient_user.id

        # ---- Appointments ----
        appts = [
            models.Appointment(patient_id=alex.id, doctor_id=doc_alimova.id, type="MRI natijasi muhokama", appt_date=today, appt_time=time(8, 30), room="Xona 302", status=models.AppointmentStatusEnum.scheduled),
            models.Appointment(patient_id=maria.id, doctor_id=doc_alimova.id, type="Kimyoterapiya nazorat", appt_date=today, appt_time=time(11, 0), room="CT xona", status=models.AppointmentStatusEnum.scheduled),
            models.Appointment(patient_id=kevin.id, doctor_id=doc_alimova.id, type="Birinchi konsultatsiya", appt_date=today, appt_time=time(14, 0), room="Xona 105", status=models.AppointmentStatusEnum.scheduled),
            models.Appointment(patient_id=robert.id, doctor_id=doc_alimova.id, type="Oylik nazorat", appt_date=today + timedelta(days=1), appt_time=time(9, 30), room="Xona 201", status=models.AppointmentStatusEnum.scheduled),
            models.Appointment(patient_id=lisa_t.id, doctor_id=doc_alimova.id, type="MRI natijasi", appt_date=today + timedelta(days=2), appt_time=time(10, 0), room="Radiologiya", status=models.AppointmentStatusEnum.scheduled),
        ]
        db.add_all(appts)

        # ---- Lab results ----
        labs = [
            models.LabResult(patient_id=alex.id, test_name="MRI Brain", value="Anormal faollik, o'sma 4.2sm", status=models.LabStatusEnum.critical, result_date=today, lab_tech="Dr. Karimov", reviewed=False),
            models.LabResult(patient_id=alex.id, test_name="Leykotsitlar (WBC)", value="11.8", unit="K/uL", reference_range="4.5-11.0", status=models.LabStatusEnum.warning, result_date=today - timedelta(days=1), lab_tech="Lab texnik", reviewed=False),
            models.LabResult(patient_id=alex.id, test_name="Tumormarker (CEA)", value="24.6", unit="ng/mL", reference_range="< 5.0", status=models.LabStatusEnum.critical, result_date=today - timedelta(days=5), lab_tech="Dr. Alimova", reviewed=False),
            models.LabResult(patient_id=sarah.id, test_name="Qon tahlili CBC", value="WBC: 11.8", unit="K/uL", reference_range="4.5-11.0", status=models.LabStatusEnum.warning, result_date=today - timedelta(days=1), lab_tech="Lab texnik", reviewed=False),
            models.LabResult(patient_id=james.id, test_name="PET Scan", value="Faollik yo'q", status=models.LabStatusEnum.normal, result_date=today - timedelta(days=2), lab_tech="Dr. Karimov", reviewed=True),
            models.LabResult(patient_id=maria.id, test_name="Biopsiya", value="Malign hujayralar aniqlandi", status=models.LabStatusEnum.critical, result_date=today - timedelta(days=3), lab_tech="Dr. Yusupova", reviewed=False),
            models.LabResult(patient_id=david.id, test_name="Glyukoza", value="5.4", unit="mmol/L", reference_range="3.9-6.1", status=models.LabStatusEnum.normal, result_date=today - timedelta(days=4), lab_tech="Lab texnik", reviewed=True),
            models.LabResult(patient_id=lisa_a.id, test_name="Tumormarker (CEA)", value="24.6", unit="ng/mL", reference_range="< 5.0", status=models.LabStatusEnum.critical, result_date=today - timedelta(days=5), lab_tech="Dr. Alimova", reviewed=False),
        ]
        db.add_all(labs)

        # ---- Treatments ----
        treatments = [
            models.Treatment(patient_id=alex.id, doctor_id=doc_alimova.id, name="Stupp protokoli", protocol="Stupp protokoli · GBM IV bosqich", medication="Temozolomide 75 mg/m²", radiotherapy="60 Gy / 30 fraksiya", sessions_done=4, sessions_total=12, next_session_date=today + timedelta(days=7), status=models.TreatmentStatusEnum.active),
            models.Treatment(patient_id=maria.id, doctor_id=doc_alimova.id, name="Kimyoterapiya", protocol="PCV protokoli", medication="Procarbazine + CCNU + Vincristine", radiotherapy=None, sessions_done=2, sessions_total=6, next_session_date=today + timedelta(days=14), status=models.TreatmentStatusEnum.active),
        ]
        db.add_all(treatments)

        # ---- MRI scans ----
        scans = [
            models.MRIScan(patient_id=alex.id, scan_date=today, brain_region="Temporal lob", tumor_size_cm=4.2, growth_percent=12.0, signal_type="T2-hiper", tag="KRITIK", reviewed=False, radiologist_notes="GBM progressiyasi, o'sma 4.2 sm"),
            models.MRIScan(patient_id=maria.id, scan_date=today - timedelta(days=4), brain_region="Frontal lob", tumor_size_cm=2.8, growth_percent=3.0, signal_type="Barqaror", tag="KUZATUV", reviewed=False, radiologist_notes="Oligodendroglioma barqaror"),
            models.MRIScan(patient_id=david.id, scan_date=today - timedelta(days=12), brain_region="Parietal lob", tumor_size_cm=1.1, growth_percent=0.0, signal_type="Normal", tag="NORMAL", reviewed=True, radiologist_notes="Neyral faollik normal"),
        ]
        db.add_all(scans)

        # ---- Alerts ----
        alerts = [
            models.Alert(type=models.AlertTypeEnum.critical, message="Bemor #%d Alex Oxford — Kritik holat: GBM IV bosqich, o'sma 12%% kengaydi" % alex.id, sub_message="Dr. Alimova ko'rishi kerak", patient_id=alex.id, target_role=None),
            models.Alert(type=models.AlertTypeEnum.warning, message="5 ta MRI natijasi tahlil kutmoqda", sub_message="Radiology bo'limida", target_role="admin"),
            models.Alert(type=models.AlertTypeEnum.info, message="3 ta yangi bemor ro'yxatdan o'tdi", sub_message="Birlamchi tekshiruv kerak", target_role="admin"),
            models.Alert(type=models.AlertTypeEnum.success, message="James Wilson — Remissiya tasdiqlandi", sub_message="Dr. Karimov", patient_id=james.id, target_role=None),
        ]
        db.add_all(alerts)

        # ---- Clinical trials ----
        trials = [
            models.ClinicalTrial(name="GBM-AGILE", description="Adaptiv glioblastoma davolash sinovi", phase="II/III", eligibility="GBM IV bosqich, 18+ yosh", status="Faol"),
            models.ClinicalTrial(name="Temodar+Immunoterapiya", description="Temozolomide va immunoterapiya kombinatsiyasi", phase="II", eligibility="Yangi tashxis qo'yilgan GBM", status="Faol"),
        ]
        db.add_all(trials)

        # ---- Clinic settings (singleton) ----
        db.add(models.ClinicSettings(id=1))

        db.commit()
        print("Seed complete.")
        print("Demo accounts: admin/Admin@123, dr.alimova/Doctor@123, bemor1/Bemor@123")
    finally:
        db.close()


if __name__ == "__main__":
    run()
