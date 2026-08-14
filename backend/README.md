# B-Cancer Backend API

B-Cancer — Miya o'smasi tibbiy platformasi uchun FastAPI backend. Frontend (`../frontend/index.html`) alohida statik fayl sifatida ishlaydi va bu API'ga fetch orqali ulanadi.

## Texnologiyalar

- FastAPI + Uvicorn
- SQLAlchemy 2.0 (SQLite default, `DATABASE_URL` orqali Postgres/MySQL ga o'tkazsa bo'ladi)
- JWT autentifikatsiya (python-jose + passlib/pbkdf2_sha256)
- Rol asosidagi ruxsatlar: `admin`, `doctor`, `patient`
- Ixtiyoriy: PyTorch ensemble model orqali MRI'dan o'sma turi bashorati (`app/ml/`)

## O'rnatish

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # kerak bo'lsa SECRET_KEY, CORS_ORIGINS, ANTHROPIC_API_KEY ni sozlang
```

## Demo ma'lumotlarni yuklash

```bash
python -m app.seed
```

| Username     | Parol       | Rol     |
|--------------|-------------|---------|
| admin        | Admin@123   | admin   |
| dr.alimova   | Doctor@123  | doctor  |
| bemor1       | Bemor@123   | patient |

## Ishga tushirish

```bash
uvicorn app.main:app --reload --port 8000
```

Interaktiv Swagger hujjatlari: http://localhost:8000/docs

Frontendni alohida serverda oching (masalan `cd ../frontend && python -m http.server 5500`) va `frontend/config.js` faylida `API_BASE`ni backend manziliga sozlang (default: `http://localhost:8000`).

## Asosiy endpointlar

- `POST /api/auth/login` — `{username, password}` → JWT token + user
- `GET  /api/auth/me` — joriy foydalanuvchi
- `GET  /api/dashboard/admin` | `/doctor` | `/patient` — panel statistikasi
- `GET/POST/PUT/DELETE /api/patients`, `/doctors`, `/appointments` — CRUD
- `GET/POST /api/lab-results`, `GET/POST/PUT /api/treatments`, `GET/POST/PUT /api/scans`
- `GET/POST /api/alerts`, `GET/POST/DELETE /api/trials`
- `POST /api/chat` — AI yordamchi. `ANTHROPIC_API_KEY` sozlangan bo'lsa haqiqiy Claude javobi, aks holda mavzu bo'yicha (nojo'ya ta'sirlar, MRI, bosh og'riq, ovqatlanish, ruhiy qo'llab-quvvatlash) tayyor o'zbekcha demo javoblar qaytaradi.
- `GET  /api/ml/status` — ML model holati (`loaded`, `torch_available`, `weights_path`, `error`)
- `POST /api/ml/predict` — `multipart/form-data`: `patient_id` + `file` (DICOM/.dcm, JPEG, PNG, NIfTI/.nii(.gz), yoki .mat). O'sma turini (Meningioma/Glioma/Pituitary) bashorat qiladi.
- `GET  /api/ml/predictions?patient_id=` — bashoratlar tarixi

Barcha `/api/*` endpointlar (login dan tashqari) `Authorization: Bearer <token>` sarlavhasini talab qiladi.

## MRI AI bashorat — demo va haqiqiy rejim

`POST /api/ml/predict` istalgan formatdagi (DICOM/JPEG/PNG/NIfTI/.mat) MRI faylini qabul qiladi, uni ichkarida `.mat` (Cheng brain-tumor dataset `cjdata` formati) ga o'giradi va ensemble model orqali (EfficientNet-B3 + ResNet-50 + DenseNet-121, `MRX8683/B_cancer` HuggingFace reposidan) tahlil qiladi.

**Ikki rejim mavjud:**

1. **Demo rejim** (o'rnatishdan keyin default) — `requirements-ml.txt` o'rnatilmagan yoki `ensemble_best.pth` vazn fayli yo'q bo'lsa, tizim tasvir statistikasidan deterministik "demo" bashorat qaytaradi va javobda **`demo_mode: true`** deb aniq belgilaydi. Bu HECH QACHON haqiqiy tibbiy xulosa emas — faqat interfeysni to'liq sinab ko'rish uchun.
2. **Haqiqiy rejim** — quyidagi qadamlar bajarilsa avtomatik yoqiladi:

   ```bash
   pip install -r requirements-ml.txt
   python scripts/download_model.py     # ensemble_best.pth ni HuggingFace'dan yuklaydi
   ```

   Vazn fayli qo'lda ham joylashtirilishi mumkin: `app/ml/weights/ensemble_best.pth`.

**Muhim eslatma preprocessing haqida:** Trening kodingizdagi (`dataset.py`) `A.Normalize(mean=[0.5], std=[0.25])` chaqiruvida `max_pixel_value` ko'rsatilmagan (default 255.0), shuning uchun haqiqiy normalizatsiya formulasi `(img - 127.5) / 63.75` bo'lgan (oddiy `(img-0.5)/0.25` EMAS). `app/ml/preprocess.py`dagi `to_model_tensor()` funksiyasi aynan shu formulani takrorlaydi — bu modelning haqiqiy trening taqsimotiga mos kelishi uchun zarur edi.

**Sandbox cheklovi:** Ushbu muhitda `huggingface.co` va katta PyPI paketlari (torch, opencv-python-headless)ga tarmoq ulanishi cheklangan/sekin bo'lgani sababli, haqiqiy rejim to'liq sinovdan o'tkazilmadi — faqat kod darajasida (arxitektura, preprocessing, checkpoint yuklash logikasi) tekshirildi. Internet ulanishi to'liq bo'lgan muhitda yuqoridagi qadamlarni bajarganingizdan so'ng `/api/ml/status` orqali `"loaded": true` ekanini tekshiring.

## Loyihaning tuzilishi

```
backend/
  app/
    main.py              - FastAPI ilova, routerlarni ulash (statik fayl mount YO'Q — API only)
    config.py            - .env sozlamalari (CORS_ORIGINS shu yerda)
    database.py          - SQLAlchemy engine/session
    models.py             - jadval modellar (MLPrediction ham shu yerda)
    schemas.py              - Pydantic request/response sxemalar
    security.py               - parol hash (pbkdf2_sha256), JWT
    deps.py                     - auth dependency, rol tekshiruv
    seed.py                      - demo ma'lumotlarni yuklovchi skript
    routers/
      auth.py, patients.py, doctors.py, appointments.py,
      lab_results.py, treatments.py, scans.py, alerts.py,
      trials.py, dashboard.py, chat.py, settings.py, reports.py, ml.py
    ml/
      config.py            - model/preprocessing konstantalari (trening bilan bir xil)
      architectures.py     - EfficientNetB3/ResNet50/DenseNet121/EnsembleModel
      preprocess.py         - format konvertatsiya (DICOM/JPEG/PNG/NIfTI → .mat → tensor)
      inference.py           - model yuklash + demo/haqiqiy bashorat
      weights/                 - ensemble_best.pth shu yerga joylashadi (git'ga qo'shilmaydi)
  scripts/
    download_model.py    - HuggingFace'dan vazn faylini yuklovchi skript
  requirements.txt        - asosiy (yengil) bog'liqliklar
  requirements-ml.txt     - ixtiyoriy og'ir ML bog'liqliklari (torch, opencv, va h.k.)
  .env.example

frontend/
  index.html            - to'liq SPA (login + admin/doctor/patient panellar)
  config.js             - window.API_BASE — backend manzili shu yerda sozlanadi
```
