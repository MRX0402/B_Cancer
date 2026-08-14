import httpx
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models, schemas
from ..config import settings
from ..database import get_db
from ..deps import get_current_user

router = APIRouter(prefix="/api/chat", tags=["chat"])


DEMO_DISCLAIMER = (
    "\n\n_(🤖 Demo javob — ANTHROPIC_API_KEY sozlanmagan. Bu haqiqiy AI xulosasi emas, "
    "faqat namunaviy ma'lumot. Har doim shifokoringiz bilan maslahatlashing.)_"
)


def _greeting_name(user: "models.User") -> str:
    first = (user.full_name or "").split()[0] if user.full_name else ""
    return first or "Hurmatli foydalanuvchi"


def _mock_reply(message: str, user: "models.User" = None) -> str:
    """
    Demo/mock AI javoblari — ANTHROPIC_API_KEY sozlanmaganda ishlatiladi.
    Kalit so'zlarga qarab UI'dagi "Tez savollar" chiplariga mos, mavzu bo'yicha
    tayyor (canned) o'zbekcha javoblar qaytaradi, shunda demo rejim ham to'liq
    va foydali ko'rinadi.
    """
    m = message.lower()
    name = _greeting_name(user) if user else "Hurmatli foydalanuvchi"
    diagnosis = None
    if user is not None and getattr(user, "patient_profile", None):
        diagnosis = user.patient_profile.diagnosis

    def wrap(text: str) -> str:
        return text + DEMO_DISCLAIMER

    # --- Nojo'ya ta'sirlar / kimyoterapiya ---
    if any(k in m for k in ["nojo'ya", "nojoya", "yon ta'sir", "ta'sir", "kimyoterap", "chemo"]):
        return wrap(
            f"💊 Salom, {name}! Kimyoterapiya va radioterapiyaning eng ko'p uchraydigan nojo'ya ta'sirlari:\n\n"
            "• Charchoq va holsizlik — davolanish davomida energiya darajasi pasayishi mumkin\n"
            "• Ko'ngil aynishi/qusish — shifokoringiz maxsus antiemetik dorilar tayinlashi mumkin\n"
            "• Soch to'kilishi — vaqtinchalik, davolanish tugagach odatda tiklanadi\n"
            "• Immunitet pasayishi — infeksiyalardan ehtiyot bo'ling, olomondan uzoqroq yuring\n"
            "• Ishtaha pasayishi — kichik, tez-tez ovqatlanish tavsiya etiladi\n\n"
            "Agar alomatlar kuchli yoki bardosh berib bo'lmas darajada bo'lsa, darhol shifokoringizga murojaat qiling."
        )

    # --- MRI tushuntirish ---
    if any(k in m for k in ["mri", "rasm", "skan", "tasvir", "natij"]):
        extra = f" Sizning tashxisingiz — {diagnosis}." if diagnosis else ""
        return wrap(
            f"🔬 {name}, MRI natijalari haqida umumiy tushuntirish:{extra}\n\n"
            "• **O'sma o'lchami (sm)** — davolash samaradorligini kuzatish uchun har seansda solishtiriladi\n"
            "• **Signal turi (T1/T2/FLAIR)** — to'qima tarkibi va shishni ko'rsatadi\n"
            "• **O'sish foizi** — oldingi MRI bilan solishtirilganda o'zgarish darajasi\n"
            "• **Kontrast kuchayishi** — faol o'sma to'qimasini aniqlashga yordam beradi\n\n"
            "Aniq natijalarni faqat shifokoringiz to'liq klinik kontekstda izohlashi mumkin — "
            "\"MRI natijalari\" bo'limida so'nggi skaningizni ko'rishingiz mumkin."
        )

    # --- Bosh og'riq ---
    if any(k in m for k in ["bosh og'riq", "bosh ogriq", "og'riq", "ogriq", "migren", "dard"]):
        return wrap(
            f"🤕 {name}, bosh og'rig'i miya o'smasi bilan davolanuvchi bemorlarda tez-tez uchraydi. Umumiy tavsiyalar:\n\n"
            "• Dam oling, yorug'lik va shovqindan uzoqlashing\n"
            "• Shifokor tayinlagan og'riq qoldiruvchidan tashqari o'zboshimchalik bilan dori ichmang\n"
            "• Og'riq kuchi, davomiyligi va vaqtini kundalikka yozib boring — bu shifokoringizga yordam beradi\n"
            "• Ko'ngil aynishi, ko'rish o'zgarishi yoki behushlik bilan birga kelsa — DARHOL shifokoringizga murojaat qiling yoki tez yordam chaqiring\n\n"
            "Bosh og'rig'i kutilmaganda kuchaysa, bu jiddiy alomat bo'lishi mumkin — kechiktirmang."
        )

    # --- Ovqatlanish / parhez ---
    if any(k in m for k in ["ovqat", "parhez", "diet", "taom", "oziq"]):
        return wrap(
            f"🥗 {name}, davolanish davomida tavsiya etiladigan ovqatlanish tamoyillari:\n\n"
            "• Oqsilga boy taomlar (tuxum, baliq, dukkaklilar) — to'qimalarni tiklashga yordam beradi\n"
            "• Ko'p suyuqlik iching — kuniga kamida 1.5–2 litr suv\n"
            "• Yangi meva-sabzavotlar — antioksidantlar va vitaminlar manbai\n"
            "• Kam-kam, lekin tez-tez ovqatlaning — ko'ngil aynishini kamaytiradi\n"
            "• Xom baliq/go'sht va pasterizatsiya qilinmagan mahsulotlardan saqlaning (immunitet pasayganda xavfli)\n\n"
            "Individual parhez rejasi uchun klinikamizdagi dietolog bilan maslahatlashishni tavsiya qilamiz."
        )

    # --- Ruhiy holat / emotional support ---
    if any(k in m for k in ["ruhiy", "kayfiyat", "qo'rq", "qorq", "stress", "tashvish", "depress", "qiyin"]):
        return wrap(
            f"💙 {name}, his-tuyg'ularingiz — tashvish, qo'rquv yoki g'am — bu tashxis bilan yashayotgan ko'p odamlar uchun "
            "tabiiy va tushunarli reaksiya.\n\n"
            "• Bu tuyg'ularni yashirmang — oila, do'stlar yoki psixolog bilan bo'lishing\n"
            "• Kichik, boshqarsa bo'ladigan kunlik maqsadlar qo'ying\n"
            "• Nafas olish mashqlari va meditatsiya stressni kamaytirishga yordam beradi\n"
            "• Klinikamizda bemorlarni qo'llab-quvvatlash guruhlari va psixolog xizmati mavjud — administratordan so'rang\n\n"
            "Yolg'iz emassiz — jamoamiz sizni har qadamda qo'llab-quvvatlashga tayyor."
        )

    # --- Salomlashish ---
    if any(k in m for k in ["salom", "assalomu", "hi", "hello", "yaxshimisiz"]):
        return wrap(
            f"👋 Salom, {name}! Men B-Cancer platformasining yordamchi AI botiman. "
            "Sizga davolanish, MRI natijalari, dori-darmon nojo'ya ta'sirlari, ovqatlanish yoki ruhiy qo'llab-quvvatlash "
            "bo'yicha savollaringizga javob berishga tayyorman. Nima haqida bilmoqchisiz?"
        )

    # --- Rahmat ---
    if any(k in m for k in ["rahmat", "tashakkur", "thanks"]):
        return wrap(f"🙏 Arzimaydi, {name}! Yana savollaringiz bo'lsa, istalgan vaqtda murojaat qiling.")

    # --- Umumiy fallback ---
    return wrap(
        f"🤖 Salom, {name}! Savolingiz uchun rahmat: \"{message}\".\n\n"
        "Men quyidagi mavzularda yordam bera olaman: kimyoterapiya/nojo'ya ta'sirlar, MRI natijalarini tushuntirish, "
        "bosh og'riq va boshqa alomatlar, ovqatlanish tavsiyalari, hamda ruhiy qo'llab-quvvatlash. "
        "Yuqoridagi \"Tez savollar\" tugmalaridan birini bosishingiz yoki savolingizni boshqacha shaklda yozishingiz mumkin."
    )


def _call_anthropic(message: str, history: list[models.ChatMessage]) -> str:
    messages = [
        {"role": "user" if m.role == "user" else "assistant", "content": m.content}
        for m in history[-10:]
    ]
    messages.append({"role": "user", "content": message})

    resp = httpx.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": settings.ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": "claude-3-5-haiku-latest",
            "max_tokens": 512,
            "system": "Siz B-Cancer tibbiy platformasidagi yordamchi AI botsiz. "
                      "O'zbek tilida qisqa, foydali va tibbiy jihatdan ehtiyotkor javob bering. "
                      "Har doim yakuniy tashxis/davolashni shifokor tasdiqlashi kerakligini eslating.",
            "messages": messages,
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    return "".join(part.get("text", "") for part in data.get("content", []))


@router.get("/history", response_model=list[schemas.ChatMessageOut])
def chat_history(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return db.query(models.ChatMessage).filter(
        models.ChatMessage.user_id == current_user.id
    ).order_by(models.ChatMessage.created_at).all()


@router.post("", response_model=schemas.ChatMessageOut)
def chat(
    payload: schemas.ChatRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    history = db.query(models.ChatMessage).filter(
        models.ChatMessage.user_id == current_user.id
    ).order_by(models.ChatMessage.created_at).all()

    user_msg = models.ChatMessage(user_id=current_user.id, role="user", content=payload.message)
    db.add(user_msg)
    db.flush()

    if settings.ANTHROPIC_API_KEY:
        try:
            reply_text = _call_anthropic(payload.message, history)
        except Exception as exc:  # noqa: BLE001 - surface a friendly fallback
            reply_text = f"⚠️ AI xizmatiga ulanishda xatolik: {exc}"
    else:
        reply_text = _mock_reply(payload.message, current_user)

    bot_msg = models.ChatMessage(user_id=current_user.id, role="bot", content=reply_text)
    db.add(bot_msg)
    db.commit()
    db.refresh(bot_msg)
    return bot_msg
