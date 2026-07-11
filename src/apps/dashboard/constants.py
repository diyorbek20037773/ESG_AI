# -*- coding: utf-8 -*-
"""Green-finance evaluation domain — ported verbatim from the ESG risk platform
(esg-risk-development `analysis/services/evaluator.py` + `orchestrator.py`).

These are Uzbek bank green-finance regulatory items: 7 information questions,
12 exclusion (stop) factors, 9 green criteria, plus the eco-expertise checks.
The AI extracts answers/evidence; the verdict is computed deterministically by
`compute_verdict()` below, replicating the original `get_final_verdict()` logic.
"""

# 1-etap — asosiy ma'lumotlar
INFO_QUESTIONS = [
    "Buyurtmachi (kredit oluvchi) tashkilot nomi va STIR raqami nima?",
    "Buyurtmachi tashkilot qaysi viloyat, tuman, MFY va manzilda joylashgan?",
    "Buyurtmachi olgan kredit miqdori (so'mda yoki dollarda) qancha?",
    "Kredit mablag'i qaysi maqsadda — qanday uskuna, xom-ashyo yoki ish uchun olingan?",
    "Buyurtmachining asosiy faoliyat turi nima (ishlab chiqarish yo'nalishi)?",
    "Shartnoma bo'yicha sotib olinayotgan uskuna, ishlab chiqarish liniyasi, xizmat ko'rsatish va boshqalar nimalardan iborat?",
    "Loyiha bo'yicha EDGE, LEED yoki BREEAM yashil sertifikati mavjudmi?",
]

# 2-etap — stop-faktorlar (istisno faoliyatlar). (question, key_terms)
STOP_FACTORS = [
    ("Loyihada O'zbekiston Respublikasi qonunchiligi bo'yicha noqonuniy/taqiqlangan mahsulot yoki faoliyat turi aks etganmi?",
     ["taqiqlangan", "noqonuniy", "qonunga zid"]),
    ("Loyihada qurol-yaroq, o'q-dori, miltiq, patron yoki harbiy texnika ishlab chiqarish yoki sotish faoliyati mavjudmi?",
     ["qurol", "qurol-yaroq", "o'q-dori", "miltiq", "patron", "harbiy texnika"]),
    ("Loyihada spirtli ichimliklar (aroq, vino, pivo, konyak) ishlab chiqarish yoki sotish faoliyati mavjudmi?",
     ["spirtli ichimlik", "aroq", "vino", "pivo", "konyak", "alkogol", "spirt"]),
    ("Loyihada tamaki mahsulotlari (sigaret, papiros, nasvoy, tamaki) ishlab chiqarish yoki sotish faoliyati mavjudmi?",
     ["tamaki", "sigaret", "papiros", "nasvoy"]),
    ("Loyihada qimor o'yinlari, kazino, lotereya yoki tikish bilan bog'liq faoliyat mavjudmi?",
     ["qimor", "kazino", "lotereya", "tikish", "azart"]),
    ("Loyihada pornografik mahsulotlar yoki reklamasi faoliyati mavjudmi?",
     ["pornografik", "pornografiya"]),
    ("Loyihada yadroviy quvvat, atom energiyasi, AES (atom elektr stansiyasi) bilan bog'liq faoliyat mavjudmi?",
     ["yadro", "yadroviy", "atom energiya", "atom elektr", "AES"]),
    ("Loyihada radioaktiv mahsulot ishlab chiqarish yoki sotish faoliyati mavjudmi?",
     ["radioaktiv", "uran", "plutoniy"]),
    ("Loyihada bog'lanmagan asbest tolalari ishlab chiqarish yoki sotish faoliyati mavjudmi?",
     ["asbest"]),
    ("Loyihada neft yoki gaz qazib olish uskunalarini sotib olish faoliyati mavjudmi?",
     ["neft qazib", "gaz qazib", "neft burg'", "burg'ulash uskuna"]),
    ("Loyihada ko'mir qazib chiqarish, tashish, sotish, yoqish yoki ko'mirdan elektr/issiqlik olish faoliyati mavjudmi?",
     ["ko'mir", "ko'mir qazib", "ko'mir yoqish"]),
    ("Loyihada neft qazib chiqarish sanoati uchun quyosh panellari yoki shamol generatorlari sotib olish/o'rnatish faoliyati mavjudmi?",
     ["neft sanoat", "neft uchun quyosh", "neft uchun shamol"]),
]

# 3-etap — yashil mezonlar (qayta tiklanuvchi energiya). (question, key_terms)
GREEN_CRITERIA = [
    ("Loyihada shamol elektr stansiyalarini loyihalashtirish, o'rnatish yoki qurish faoliyati mavjudmi?",
     ["shamol elektr stansiya", "shamol energiya", "VES", "wind power"]),
    ("Loyihada quyosh elektr stansiyalarini loyihalashtirish, o'rnatish yoki qurish faoliyati mavjudmi?",
     ["quyosh elektr stansiya", "quyosh energiya", "QES", "fotoelektr", "solar"]),
    ("Loyihada geotermal energiya bilan bog'liq faoliyat mavjudmi?",
     ["geotermal", "geotermik", "yer issiqligi"]),
    ("Loyihada gidroelektrostansiya (GES) qurish yoki ishlatish faoliyati mavjudmi?",
     ["gidroelektr", "GES", "gidroenergiya", "suv elektr stansiya"]),
    ("Loyihada qayta tiklanuvchi manbalardan isitish/sovutish yoki kogeneratsiyalash ob'ektini qurish faoliyati mavjudmi?",
     ["qayta tiklanuvchi", "kogeneratsiya", "isitish-sovutish"]),
    ("Loyihada avtomobil/temir yo'l parkini past emissiyali yoqilg'i yoki nol emissiya texnologiyalari bilan almashtirish mavjudmi?",
     ["past emissiya", "elektromobil", "yashil vodorod", "siqilgan gaz", "CNG", "LNG", "elektr avtobus"]),
    ("Loyihada issiqxona gazlari emissiyasi nolga teng yangi transport vositalari yoki lokomotivlar sotib olish/ishlab chiqarish faoliyati mavjudmi?",
     ["nol emissiya", "elektrovoz", "elektr lokomotiv", "vodorod transport"]),
    ("Loyihada motorsiz transport infratuzilmasi (velosiped, piyodalar yo'li) rivojlantirish faoliyati mavjudmi?",
     ["velosiped", "piyodalar yo'li", "motorsiz transport"]),
    ("Loyihada mavjud binolarni kamida 20% energiya samaradorligi yoki uglerod emissiyasini kamaytirish uchun modernizatsiya faoliyati mavjudmi?",
     ["energiya samaradorlik", "20%", "energiya tejash", "issiqlik izolyatsiya", "bino modernizatsiya"]),
]

ECO_EXPERTISE_REQUIRED = (
    "Loyiha davlat ekologik ekspertizasi (I, II yoki III toifa) ijobiy xulosasi olish talab etiladigan toifaga tushadimi?",
    ["ekologik ekspertiza", "I toifa", "II toifa", "III toifa", "toifa", "ijobiy xulosa"],
)
ECO_EXPERTISE_OBTAINED = (
    "Loyiha bo'yicha davlat ekologik ekspertizasining ijobiy (musbat) xulosasi olinganmi?",
    ["ekologik ekspertiza", "ijobiy xulosa", "musbat xulosa", "xulosa olindi"],
)

# Verdict codes
VERDICT_GREEN = "green"
VERDICT_NOT_GREEN = "not_green"
VERDICT_UNKNOWN = "unknown"


def compute_verdict(eco_required, eco_obtained, stop_factors, green_criteria):
    """Deterministic verdict — ported from evaluator.get_final_verdict().

    Args are the parsed AI results:
      eco_required / eco_obtained : {"value": bool, ...}
      stop_factors / green_criteria : list of {"value": bool, ...}
    Returns {"code", "approved", "title", "summary"}.
    """
    eco_failed = bool(eco_required.get("value")) and not bool(eco_obtained.get("value"))
    triggered_stops = [s for s in stop_factors if s.get("value")]
    stopped = bool(triggered_stops) or eco_failed

    if stopped:
        reasons = []
        if eco_failed:
            reasons.append("davlat ekologik ekspertizasi xulosasi yo'q")
        if triggered_stops:
            reasons.append(f"{len(triggered_stops)} ta istisno faoliyat turi aniqlandi")
        return {
            "code": VERDICT_NOT_GREEN,
            "approved": False,
            "title": "LOYIHA RAD ETILDI",
            "summary": "Loyiha yashil moliyalashtirish mezonlariga mos kelmadi. "
                       f"Sabab: {', '.join(reasons)}.",
        }

    matched = [g for g in green_criteria if g.get("value")]
    if matched:
        return {
            "code": VERDICT_GREEN,
            "approved": True,
            "title": "LOYIHA TASDIQLANDI",
            "summary": f"Loyiha stop-faktorlardan muvaffaqiyatli o'tdi va {len(matched)} ta "
                       "yashil mezon bo'yicha mos keldi. Yashil moliyalashtirishga yaroqli.",
        }
    if green_criteria:
        return {
            "code": VERDICT_NOT_GREEN,
            "approved": False,
            "title": "LOYIHA YASHIL MEZONLARGA MOS KELMADI",
            "summary": "Loyiha stop-faktorlardan o'tdi, lekin hech bir yashil iqtisod mezoniga "
                       "to'g'ri kelmadi. Yashil moliyalashtirish uchun yaroqli emas.",
        }
    return {
        "code": VERDICT_UNKNOWN,
        "approved": False,
        "title": "NOMA'LUM NATIJA",
        "summary": "Tahlil uchun ma'lumot yetarli bo'lmadi.",
    }
