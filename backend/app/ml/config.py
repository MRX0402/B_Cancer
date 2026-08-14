"""
app/ml/config.py
=================
Foydalanuvchi bergan `configs/config.py` (train pipeline) bilan BIR XIL
qiymatlar — inference paytida ham xuddi shu preprocessing/arxitektura
ishlatilishi shart, aks holda model noto'g'ri bashorat qiladi.
"""
import os

# ── Sinf nomlari (configs/config.py bilan bir xil, tartib muhim!) ──
CLASS_NAMES = ['Meningioma', 'Glioma', 'Pituitary']
NUM_CLASSES = len(CLASS_NAMES)

# ── Tasvir parametrlari (train paytidagi bilan bir xil) ──
IMG_SIZE = 224
CLAHE_CLIP = 2.0
CLAHE_GRID = (8, 8)
GAUSS_KERNEL = (3, 3)
NORM_MEAN = 0.5
NORM_STD = 0.25

# ── Ensemble og'irliklari ──
ENSEMBLE_WEIGHTS = {
    'efficientnet_b3': 0.4,
    'resnet50': 0.3,
    'densenet121': 0.3,
}

# ── Model fayli ──
# Hugging Face: https://huggingface.co/MRX8683/B_cancer/blob/main/ensemble_best.pth
# `python backend/scripts/download_model.py` orqali yuklab shu papkaga qo'ying,
# yoki faylni qo'lda shu yerga joylashtiring.
ML_DIR = os.path.dirname(os.path.abspath(__file__))
WEIGHTS_DIR = os.path.join(ML_DIR, "weights")
MODEL_PATH = os.path.join(WEIGHTS_DIR, "ensemble_best.pth")
HF_REPO_ID = "MRX8683/B_cancer"
HF_FILENAME = "ensemble_best.pth"
