"""
app/ml/preprocess.py
=====================
Foydalanuvchi/shifokor DCM, JPEG, PNG yoki NIfTI fayl yuklaydi — model esa
FAQAT .mat (Cheng brain-tumor dataset "cjdata" strukturasi) qabul qiladi.
Shu sababli bu modul:

  1. Har qanday formatni 2D grayscale numpy massiviga o'giradi
  2. Uni haqiqiy `cjdata` .mat fayliga yozadi (vaqtinchalik)
  3. O'sha .mat faylni foydalanuvchining `dataset.py`sidagi bilan AYNAN bir xil
     `load_mat_file()` + `medical_preprocess()` orqali o'qib, modelga tayyorlaydi

Shunday qilib model doim faqat .mat'dan "oziqlanadi" — talab qilingani shu edi.
"""
import io
import os
import tempfile
import uuid

import numpy as np

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import scipy.io as sio
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

try:
    import h5py
    H5PY_AVAILABLE = True
except ImportError:
    H5PY_AVAILABLE = False

from .config import IMG_SIZE, CLAHE_CLIP, CLAHE_GRID, GAUSS_KERNEL, NORM_MEAN, NORM_STD

SUPPORTED_EXTENSIONS = {".dcm", ".dicom", ".jpg", ".jpeg", ".png", ".nii", ".gz", ".mat"}


class PreprocessError(Exception):
    pass


# ══════════════════════════════════════════════════════════════
# 1. HAR XIL FORMATNI 2D GRAYSCALE MASSIVGA O'GIRISH
# ══════════════════════════════════════════════════════════════

def _from_dicom(data: bytes) -> np.ndarray:
    try:
        import pydicom
    except ImportError:
        raise PreprocessError("DICOM (.dcm) o'qish uchun 'pydicom' o'rnatilishi kerak: pip install pydicom")
    ds = pydicom.dcmread(io.BytesIO(data))
    arr = ds.pixel_array.astype(np.float64)
    if arr.ndim == 3:  # multi-frame -> o'rtadagi kadr
        arr = arr[arr.shape[0] // 2]
    slope = float(getattr(ds, "RescaleSlope", 1.0))
    intercept = float(getattr(ds, "RescaleIntercept", 0.0))
    arr = arr * slope + intercept
    return arr


def _from_image(data: bytes) -> np.ndarray:
    """JPEG/PNG o'qish. cv2 bo'lsa o'sha, aks holda Pillow (ancha yengil paket)."""
    if CV2_AVAILABLE:
        arr = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_GRAYSCALE)
        if arr is None:
            raise PreprocessError("Rasm fayli o'qilmadi — fayl buzilgan bo'lishi mumkin")
        return arr.astype(np.float64)

    if PIL_AVAILABLE:
        try:
            img = Image.open(io.BytesIO(data)).convert("L")
            return np.asarray(img, dtype=np.float64)
        except Exception as exc:  # noqa: BLE001
            raise PreprocessError(f"Rasm fayli o'qilmadi: {exc}")

    raise PreprocessError(
        "JPEG/PNG o'qish uchun 'pillow' o'rnatilishi kerak: pip install pillow"
    )


def _from_nifti(data: bytes, filename: str) -> np.ndarray:
    try:
        import nibabel as nib
    except ImportError:
        raise PreprocessError("NIfTI (.nii/.nii.gz) o'qish uchun 'nibabel' o'rnatilishi kerak: pip install nibabel")
    suffix = ".nii.gz" if filename.lower().endswith(".gz") else ".nii"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name
    try:
        img = nib.load(tmp_path)
        vol = np.asarray(img.dataobj, dtype=np.float64)
        if vol.ndim == 4:
            vol = vol[..., vol.shape[-1] // 2]
        if vol.ndim == 3:
            mid = vol.shape[2] // 2
            arr = vol[:, :, mid]
        elif vol.ndim == 2:
            arr = vol
        else:
            raise PreprocessError(f"Kutilmagan NIfTI o'lchami: {vol.shape}")
        return arr
    finally:
        os.unlink(tmp_path)


def _load_mat_image(data: bytes) -> np.ndarray:
    """Foydalanuvchi to'g'ridan-to'g'ri .mat yuklasa — mavjud cjdata'dan o'qiymiz."""
    with tempfile.NamedTemporaryFile(suffix=".mat", delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name
    try:
        result = load_mat_file(tmp_path)
        return result["image"]
    finally:
        os.unlink(tmp_path)


def extract_2d_image(data: bytes, filename: str) -> np.ndarray:
    """Fayl kengaytmasiga qarab tegishli o'quvchini tanlaydi."""
    ext = os.path.splitext(filename.lower())[1]
    lower = filename.lower()

    if lower.endswith(".nii.gz") or ext == ".nii":
        return _from_nifti(data, filename)
    if ext in (".dcm", ".dicom"):
        return _from_dicom(data)
    if ext in (".jpg", ".jpeg", ".png"):
        return _from_image(data)
    if ext == ".mat":
        return _load_mat_image(data)
    if ext == ".gz":  # masalan "scan.nii.gz" ni .gz deb topgan bo'lsa
        return _from_nifti(data, filename)

    raise PreprocessError(
        f"Qo'llab-quvvatlanmaydigan fayl formati: '{ext}'. "
        "Faqat DICOM (.dcm), JPEG (.jpg/.jpeg), PNG (.png), NIfTI (.nii/.nii.gz) yoki .mat qabul qilinadi."
    )


# ══════════════════════════════════════════════════════════════
# 2. 2D MASSIVNI HAQIQIY cjdata .mat FAYLGA YOZISH
#    (model faqat .mat'dan oziqlanishi uchun)
# ══════════════════════════════════════════════════════════════

def save_as_cjdata_mat(image: np.ndarray, out_path: str, label: int = 0) -> None:
    if not SCIPY_AVAILABLE:
        raise PreprocessError("'.mat' yozish uchun 'scipy' o'rnatilishi kerak: pip install scipy")
    dtype = [("image", "O"), ("label", "O"), ("tumorMask", "O")]
    arr = np.zeros((1, 1), dtype=dtype)
    arr[0, 0]["image"] = image.astype(np.float64)
    arr[0, 0]["label"] = np.array([[label + 1]], dtype=np.float64)  # load_mat_file -1 qiladi
    arr[0, 0]["tumorMask"] = np.zeros_like(image, dtype=np.float64)
    sio.savemat(out_path, {"cjdata": arr})


# ══════════════════════════════════════════════════════════════
# 3. .MAT O'QISH — foydalanuvchining dataset.py bilan bir xil logika
# ══════════════════════════════════════════════════════════════

def load_mat_file(path: str) -> dict:
    if H5PY_AVAILABLE:
        try:
            with h5py.File(path, "r") as f:
                data = f["cjdata"]
                image = np.array(data["image"])
                label = int(np.array(data["label"]).flat[0]) - 1
                mask = np.array(data["tumorMask"]) if "tumorMask" in data else None
            return {"image": image, "label": label, "mask": mask}
        except OSError:
            pass

    if SCIPY_AVAILABLE:
        mat = sio.loadmat(path)
        cj = mat["cjdata"][0, 0]
        image = cj["image"].astype(np.float64)
        label = int(cj["label"].flat[0]) - 1
        mask = cj["tumorMask"] if "tumorMask" in cj.dtype.names else None
        return {"image": image, "label": label, "mask": mask}

    raise PreprocessError("'.mat' o'qish uchun h5py yoki scipy kerak")


# ══════════════════════════════════════════════════════════════
# 4. PREPROCESSING — train paytidagi bilan bir xil (dataset.py)
# ══════════════════════════════════════════════════════════════

def _clahe_numpy(img: np.ndarray, clip_limit: float, grid: tuple) -> np.ndarray:
    """
    OpenCV'ning CLAHE algoritmini numpy'da takrorlaydi:
    tile'larga bo'lish -> gistogramma -> clip + qayta taqsimlash -> CDF/LUT
    -> tile'lar orasida bilinear interpolyatsiya.
    """
    h, w = img.shape
    gx, gy = int(grid[0]), int(grid[1])
    th = int(np.ceil(h / gy))
    tw = int(np.ceil(w / gx))

    pad_h, pad_w = th * gy - h, tw * gx - w
    img_p = np.pad(img, ((0, pad_h), (0, pad_w)), mode="reflect") if (pad_h or pad_w) else img

    tile_area = th * tw
    clip = max(1, int(clip_limit * tile_area / 256.0))

    luts = np.empty((gy, gx, 256), dtype=np.float64)
    for i in range(gy):
        for j in range(gx):
            tile = img_p[i * th:(i + 1) * th, j * tw:(j + 1) * tw]
            hist = np.bincount(tile.ravel(), minlength=256).astype(np.int64)
            excess = int(np.maximum(hist - clip, 0).sum())
            hist = np.minimum(hist, clip)
            if excess > 0:
                incr = excess // 256
                hist += incr
                residual = excess - incr * 256
                if residual > 0:
                    hist[:residual] += 1
            luts[i, j] = np.clip(np.cumsum(hist) * (255.0 / tile_area), 0, 255)

    # Tile markazlariga nisbatan bilinear interpolyatsiya
    yf = (np.arange(h) + 0.5) / th - 0.5
    xf = (np.arange(w) + 0.5) / tw - 0.5
    y0 = np.floor(yf).astype(np.int64)
    x0 = np.floor(xf).astype(np.int64)
    wy = (yf - y0)[:, None]
    wx = (xf - x0)[None, :]
    y0c, y1c = np.clip(y0, 0, gy - 1), np.clip(y0 + 1, 0, gy - 1)
    x0c, x1c = np.clip(x0, 0, gx - 1), np.clip(x0 + 1, 0, gx - 1)

    idx = img.astype(np.int64)
    l00 = luts[y0c[:, None], x0c[None, :], idx]
    l01 = luts[y0c[:, None], x1c[None, :], idx]
    l10 = luts[y1c[:, None], x0c[None, :], idx]
    l11 = luts[y1c[:, None], x1c[None, :], idx]

    out = (1 - wy) * ((1 - wx) * l00 + wx * l01) + wy * ((1 - wx) * l10 + wx * l11)
    return np.clip(np.round(out), 0, 255).astype(np.uint8)


def _gaussian_blur3_numpy(img: np.ndarray) -> np.ndarray:
    """cv2.GaussianBlur(img,(3,3),0) ekvivalenti: [1,2,1]/4 separable, BORDER_REFLECT_101."""
    k = np.array([1.0, 2.0, 1.0]) / 4.0
    p = np.pad(img.astype(np.float64), ((0, 0), (1, 1)), mode="reflect")
    tmp = k[0] * p[:, :-2] + k[1] * p[:, 1:-1] + k[2] * p[:, 2:]
    p = np.pad(tmp, ((1, 1), (0, 0)), mode="reflect")
    out = k[0] * p[:-2, :] + k[1] * p[1:-1, :] + k[2] * p[2:, :]
    return np.clip(np.round(out), 0, 255).astype(np.uint8)


def _resize_bilinear_numpy(img: np.ndarray, out_h: int, out_w: int) -> np.ndarray:
    """cv2.resize(..., INTER_LINEAR) ekvivalenti (antialias YO'Q — cv2 ham qilmaydi)."""
    h, w = img.shape
    sy, sx = h / out_h, w / out_w
    yf = np.clip((np.arange(out_h) + 0.5) * sy - 0.5, 0, h - 1)
    xf = np.clip((np.arange(out_w) + 0.5) * sx - 0.5, 0, w - 1)
    y0 = np.floor(yf).astype(np.int64)
    x0 = np.floor(xf).astype(np.int64)
    y1 = np.minimum(y0 + 1, h - 1)
    x1 = np.minimum(x0 + 1, w - 1)
    wy = (yf - y0)[:, None]
    wx = (xf - x0)[None, :]

    src = img.astype(np.float64)
    a = src[y0[:, None], x0[None, :]]
    b = src[y0[:, None], x1[None, :]]
    c = src[y1[:, None], x0[None, :]]
    d = src[y1[:, None], x1[None, :]]
    out = (1 - wy) * ((1 - wx) * a + wx * b) + wy * ((1 - wx) * c + wx * d)
    return np.clip(np.round(out), 0, 255).astype(np.uint8)


def medical_preprocess(image: np.ndarray) -> np.ndarray:
    """
    Trening paytidagi (dataset.py) bilan bir xil preprocessing:
      min-max -> uint8, CLAHE, Gaussian blur, resize, float32 [0,1].

    cv2 o'rnatilgan bo'lsa o'sha ishlatiladi (aniq mos keladi), aks holda
    yuqoridagi numpy ekvivalentlari — natija amalda bir xil bo'ladi va
    og'ir opencv paketini o'rnatish shart emas.
    """
    mn, mx = image.min(), image.max()
    if mx - mn < 1e-8:
        image = np.zeros(image.shape, dtype=np.uint8)
    else:
        image = ((image - mn) / (mx - mn) * 255).astype(np.uint8)

    if CV2_AVAILABLE:
        clahe = cv2.createCLAHE(clipLimit=CLAHE_CLIP, tileGridSize=CLAHE_GRID)
        image = clahe.apply(image)
        image = cv2.GaussianBlur(image, GAUSS_KERNEL, 0)
        image = cv2.resize(image, (IMG_SIZE, IMG_SIZE))
    else:
        image = _clahe_numpy(image, CLAHE_CLIP, CLAHE_GRID)
        image = _gaussian_blur3_numpy(image)
        image = _resize_bilinear_numpy(image, IMG_SIZE, IMG_SIZE)

    return image.astype(np.float32) / 255.0


def to_model_tensor(image_2d_float01: np.ndarray):
    """
    (H,W) float [0,1] -> normallashtirilgan torch tensor (1,1,H,W).

    MUHIM: trainer.py/dataset.py'da albumentations'ning
    `A.Normalize(mean=[0.5], std=[0.25])` ishlatilgan, lekin `max_pixel_value`
    parametri ko'rsatilmagan — u DEFAULT holda 255.0 bo'ladi. Albumentations
    buni ichkarida `(img - mean*max_pixel_value) / (std*max_pixel_value)`
    deb hisoblaydi. Bizning `medical_preprocess()` esa tasvirni allaqachon
    [0,1] oralig'iga skalalagan (255'ga BO'LINGAN) holda uzatadi — ya'ni
    trening paytida haqiqiy formula (img - 0.5*255) / (0.25*255) bo'lgan,
    oddiy (img - 0.5) / 0.25 EMAS. Model xuddi shu taqsimotga o'rgatilgan,
    shuning uchun inference paytida ham AYNAN shu formula qo'llanilishi
    shart — aks holda model noto'g'ri/tasodifiy natija beradi.
    """
    import torch
    mean_scaled = NORM_MEAN * 255.0
    std_scaled = NORM_STD * 255.0
    normalized = (image_2d_float01 - mean_scaled) / std_scaled
    tensor = torch.from_numpy(normalized).unsqueeze(0).unsqueeze(0).float()
    return tensor


# ══════════════════════════════════════════════════════════════
# 5. TO'LIQ PIPELINE: yuklangan fayl -> model tensor
# ══════════════════════════════════════════════════════════════

def process_upload(data: bytes, filename: str, tmp_dir: str = None):
    """
    Qaytaradi: (tensor_ready_image[np.ndarray HxW float01], mat_path[str])
    mat_path — audit/tekshiruv uchun saqlangan vaqtinchalik .mat fayl yo'li.
    """
    image_2d = extract_2d_image(data, filename)

    # Talab bo'yicha model faqat .mat'dan "oziqlanadi": tasvirni haqiqiy cjdata
    # .mat fayliga yozib, keyin o'sha fayldan qayta o'qiymiz.
    # scipy o'rnatilmagan bo'lsa bu bosqich o'tkazib yuboriladi — .mat faqat
    # oraliq konteyner bo'lgani uchun yakuniy natija bir xil bo'ladi.
    mat_path = None
    if SCIPY_AVAILABLE:
        tmp_dir = tmp_dir or tempfile.gettempdir()
        mat_path = os.path.join(tmp_dir, f"upload_{uuid.uuid4().hex}.mat")
        save_as_cjdata_mat(image_2d, mat_path)
        image_2d = load_mat_file(mat_path)["image"]

    processed = medical_preprocess(image_2d)
    return processed, mat_path
