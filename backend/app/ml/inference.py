"""
app/ml/inference.py
====================
Model yuklash + bashorat.

Ikki rejim:
  • HAQIQIY rejim — agar `ensemble_best.pth` app/ml/weights/ papkasida bo'lsa
    va torch/torchvision o'rnatilgan bo'lsa, haqiqiy EnsembleModel yuklanadi.
  • DEMO rejim — aks holda (masalan hozirgi sandbox'da tarmoq huggingface.co'ga
    ulanmagani uchun vazn fayli yo'q), tizim buzilmasin deb, tasvir
    statistikasidan deterministik "demo" bashorat qaytaradi va javobda
    `demo_mode: true` deb aniq belgilaydi — bu HECH QACHON haqiqiy tibbiy
    xulosa sifatida ko'rsatilmasligi kerak.
"""
import hashlib

import numpy as np

from .config import CLASS_NAMES, MODEL_PATH, ENSEMBLE_WEIGHTS

_model = None
_model_load_attempted = False
_model_load_error = None

TORCH_AVAILABLE = False
try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    pass


def _try_load_model():
    global _model, _model_load_attempted, _model_load_error
    if _model_load_attempted:
        return
    _model_load_attempted = True

    import os
    if not TORCH_AVAILABLE:
        _model_load_error = "torch/torchvision o'rnatilmagan"
        return
    if not os.path.exists(MODEL_PATH):
        _model_load_error = f"Model fayli topilmadi: {MODEL_PATH} (backend/scripts/download_model.py ishlatib yuklang)"
        return

    try:
        from .architectures import EnsembleModel
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model = EnsembleModel(weights=ENSEMBLE_WEIGHTS, device=device)
        checkpoint = torch.load(MODEL_PATH, map_location=device)
        state = checkpoint.get("model_state", checkpoint) if isinstance(checkpoint, dict) else checkpoint
        model.load_state_dict(state)
        model.to(device)
        model.eval()
        _model = model
    except Exception as exc:  # noqa: BLE001
        _model_load_error = f"Model yuklashda xatolik: {exc}"
        _model = None


def is_real_model_loaded() -> bool:
    _try_load_model()
    return _model is not None


def model_status() -> dict:
    _try_load_model()
    return {
        "loaded": _model is not None,
        "torch_available": TORCH_AVAILABLE,
        "weights_path": MODEL_PATH,
        "error": _model_load_error,
    }


def _demo_predict(image_2d: np.ndarray) -> dict:
    """
    Model vaznlari yo'qligida ishlatiladigan DEMO bashorat.
    Bir xil tasvir uchun doim bir xil natija qaytaradi (tasvir statistikasidan
    hosil qilingan seed orqali), lekin bu HAQIQIY tibbiy tahlil EMAS.
    """
    stats = f"{image_2d.mean():.6f}-{image_2d.std():.6f}-{image_2d.shape}"
    seed = int(hashlib.sha256(stats.encode()).hexdigest(), 16) % (2 ** 32)
    rng = np.random.default_rng(seed)

    base = rng.dirichlet(alpha=[2.5, 1.5, 1.5])
    # Eng katta qiymatni biroz "ishonchliroq" qilib beramiz (demo uchun realistik ko'rinish)
    idx = int(np.argmax(base))
    boost = rng.uniform(0.15, 0.35)
    base[idx] += boost
    base = base / base.sum()

    probs = {CLASS_NAMES[i]: float(base[i]) for i in range(len(CLASS_NAMES))}
    predicted = CLASS_NAMES[idx]
    return {
        "predicted_class": predicted,
        "confidence": probs[predicted],
        "probabilities": probs,
        "demo_mode": True,
    }


def _real_predict(image_2d: np.ndarray) -> dict:
    from .preprocess import to_model_tensor

    device = next(_model.parameters()).device
    tensor = to_model_tensor(image_2d).to(device)

    with torch.no_grad():
        probs_tensor = _model.get_probabilities(tensor)[0]

    probs = {CLASS_NAMES[i]: float(probs_tensor[i]) for i in range(len(CLASS_NAMES))}
    idx = int(torch.argmax(probs_tensor).item())
    predicted = CLASS_NAMES[idx]
    return {
        "predicted_class": predicted,
        "confidence": probs[predicted],
        "probabilities": probs,
        "demo_mode": False,
    }


def predict(image_2d: np.ndarray) -> dict:
    """image_2d — medical_preprocess() dan chiqqan (IMG_SIZE, IMG_SIZE) float [0,1] massiv."""
    _try_load_model()
    if _model is not None:
        return _real_predict(image_2d)
    result = _demo_predict(image_2d)
    result["demo_reason"] = _model_load_error
    return result
