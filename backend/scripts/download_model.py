"""
scripts/download_model.py
==========================
Haqiqiy ensemble_best.pth vazn faylini Hugging Face'dan yuklab, app/ml/weights/
papkasiga joylashtiradi. Shundan keyin backend avtomatik "haqiqiy rejim"ga o'tadi
(hozir tarmoqqa ulanmagani/vazn fayli yo'qligi sababli backend "demo rejim"da ishlaydi).

Ishlatish:
    pip install -r requirements-ml.txt
    python scripts/download_model.py

Yoki faylni qo'lda yuklab, quyidagi joyga qo'ying:
    backend/app/ml/weights/ensemble_best.pth
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.ml.config import HF_REPO_ID, HF_FILENAME, WEIGHTS_DIR, MODEL_PATH  # noqa: E402


def main():
    try:
        from huggingface_hub import hf_hub_download
    except ImportError:
        print("Xato: 'huggingface_hub' o'rnatilmagan. Avval: pip install -r requirements-ml.txt")
        sys.exit(1)

    os.makedirs(WEIGHTS_DIR, exist_ok=True)
    print(f"Yuklanmoqda: {HF_REPO_ID}/{HF_FILENAME} ...")
    try:
        downloaded_path = hf_hub_download(repo_id=HF_REPO_ID, filename=HF_FILENAME, local_dir=WEIGHTS_DIR)
    except Exception as exc:  # noqa: BLE001
        print(f"Yuklab olishda xatolik: {exc}")
        print("Internet ulanishi yo'q bo'lishi mumkin (masalan sandbox muhitida).")
        print(f"Muqobil: faylni qo'lda yuklab, shu yo'lga qo'ying: {MODEL_PATH}")
        sys.exit(1)

    # huggingface_hub ba'zan nested papkaga saqlaydi -- to'g'ridan-to'g'ri kutilgan yo'lga ko'chiramiz
    if os.path.abspath(downloaded_path) != os.path.abspath(MODEL_PATH):
        import shutil
        shutil.copy(downloaded_path, MODEL_PATH)

    print(f"Tayyor: {MODEL_PATH}")
    print("Backend'ni qayta ishga tushiring — avtomatik haqiqiy rejimga o'tadi.")


if __name__ == "__main__":
    main()
