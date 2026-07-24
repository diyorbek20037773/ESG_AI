# -*- coding: utf-8 -*-
"""Reset the demo dashboard to purely SYNTHETIC data.

Removes every real Analysis (and its Clients) and inserts exactly two invented
demo projects — one Green, one Not-green — built through the same deterministic
`compute_verdict()` used in production so their structure is identical to a real
run. No real firm names or data are ever seeded here.

Idempotent: safe to run on every deploy (wipes + reseeds the two demo rows).
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from src.apps.dashboard import constants
from src.apps.dashboard.models import Analysis, Client


def _info(answers):
    return [{"question": q, "answer": a, "evidence": ""}
            for q, a in zip(constants.INFO_QUESTIONS, answers)]


def _stops(triggered_idx, evidence=None):
    """Build the 12 stop-factors; only indexes in `triggered_idx` are True."""
    ev = evidence or {}
    return [{"question": q, "value": (i in triggered_idx), "evidence": ev.get(i, "")}
            for i, (q, _terms) in enumerate(constants.STOP_FACTORS)]


def _green(matched_idx, evidence=None):
    """Build the 9 green criteria; only indexes in `matched_idx` are True."""
    ev = evidence or {}
    return [{"question": q, "value": (i in matched_idx), "evidence": ev.get(i, "")}
            for i, (q, _terms) in enumerate(constants.GREEN_CRITERIA)]


# ── Two invented demo projects ────────────────────────────────────────────────
DEMO = [
    {
        # GREEN — a solar PV project that passes all stop-factors and matches a
        # renewable-energy green criterion.
        "number": "202600001",
        "company_name": "QUYOSH VODIY SOLAR LLC",
        "client": {
            "name": "Quyosh Vodiy Solar LLC", "stir": "300100200",
            "industry": "Qayta tiklanuvchi energiya", "region": "Jizzax",
            "region_code": "25", "segment": "Yirik biznes", "contract_id": "KR-2026-0142",
            "currency": "UZS", "credit_rate": "14.00", "credit_purpose": "Quyosh panellari xaridi",
            "green_direction": "Qayta tiklanuvchi energiya", "green_mark": "EM1",
            "credit_product": "Yashil kredit", "sector": "Energetika", "field": "Elektr ishlab chiqarish",
        },
        "language": "uz",
        "filenames": ["quyosh-vodiy-loyiha.pdf"],
        "scores": (72, 78, 70, 74),
        "info": [
            "Quyosh Vodiy Solar MChJ — STIR 300100200",
            "Jizzax viloyati, Zomin tumani, Yangihayot MFY",
            "45 000 000 000 so'm",
            "100 MVt quyosh elektr stansiyasi uchun fotoelektr panellari va inverterlar",
            "Qayta tiklanuvchi energiya ishlab chiqarish",
            "Fotoelektr panellar, inverterlar, transformator va montaj xizmatlari",
            "Loyiha bo'yicha EDGE yashil sertifikati rejalashtirilgan",
        ],
        "eco_required": {"value": True, "evidence": "II toifa ekologik ekspertiza talab etiladi"},
        "eco_obtained": {"value": True, "evidence": "Davlat ekologik ekspertizasi ijobiy xulosasi olingan"},
        "stops": _stops(set()),
        "green": _green({1}, {1: "100 MVt quyosh elektr stansiyasi (fotoelektr)"}),
    },
    {
        # NOT-GREEN — a project that trips a stop-factor (coal), so it is rejected.
        "number": "202600002",
        "company_name": "OQTOSH ENERGO LLC",
        "client": {
            "name": "Oqtosh Energo LLC", "stir": "300300400",
            "industry": "Energetika", "region": "Navoiy",
            "region_code": "08", "segment": "O'rta biznes", "contract_id": "KR-2026-0287",
            "currency": "USD", "credit_rate": "9.50", "credit_purpose": "Qozon uskunalari xaridi",
            "green_direction": "—", "green_mark": "EM2",
            "credit_product": "Investitsiya krediti", "sector": "Energetika", "field": "Issiqlik energetikasi",
        },
        "language": "uz",
        "filenames": ["oqtosh-energo-loyiha.pdf"],
        "scores": (48, 62, 58, 55),
        "info": [
            "Oqtosh Energo MChJ — STIR 300300400",
            "Navoiy viloyati, Konimex tumani",
            "30 000 000 000 so'm",
            "Issiqlik elektr stansiyasi uchun ko'mir yoqish qozonlari",
            "Issiqlik va elektr energiya ishlab chiqarish",
            "Ko'mirda ishlaydigan qozon uskunalari va yordamchi jihozlar",
            "Yashil sertifikat mavjud emas",
        ],
        "eco_required": {"value": True, "evidence": "I toifa ekologik ekspertiza talab etiladi"},
        "eco_obtained": {"value": True, "evidence": "Ijobiy xulosa olingan"},
        "stops": _stops({10}, {10: "Loyihada ko'mir yoqish orqali issiqlik/elektr olish aniqlandi"}),
        "green": _green(set()),
    },
]

# Extra synthetic green-portfolio rows (no analysis) — richer loan-book table.
PORTFOLIO = [
    {"name": "Yashil Agro Klaster LLC", "stir": "301400500", "industry": "Qishloq xo'jaligi",
     "region": "Buxoro", "region_code": "12", "segment": "O'rta biznes", "contract_id": "KR-2026-0311",
     "currency": "UZS", "credit_rate": "13.50", "credit_purpose": "Tomchilatib sug'orish tizimi",
     "green_direction": "Suv resurslarini tejash", "green_mark": "EM1",
     "credit_product": "Yashil kredit", "sector": "Agrosanoat", "field": "Sug'orma dehqonchilik"},
    {"name": "Chorvoq Gidro MChJ", "stir": "301600700", "industry": "Gidroenergetika",
     "region": "Toshkent", "region_code": "27", "segment": "Yirik biznes", "contract_id": "KR-2026-0356",
     "currency": "UZS", "credit_rate": "12.00", "credit_purpose": "Kichik GES modernizatsiyasi",
     "green_direction": "Gidroenergetika", "green_mark": "EM1",
     "credit_product": "Yashil kredit", "sector": "Energetika", "field": "Suv elektr stansiyasi"},
    {"name": "EkoBino Devkon LLC", "stir": "301800900", "industry": "Qurilish",
     "region": "Samarqand", "region_code": "18", "segment": "Kichik biznes", "contract_id": "KR-2026-0402",
     "currency": "UZS", "credit_rate": "15.00", "credit_purpose": "Energiya-samarali bino qurilishi",
     "green_direction": "Energiya samaradorligi", "green_mark": "EM2",
     "credit_product": "Yashil ipoteka", "sector": "Qurilish", "field": "Turar-joy qurilishi"},
]


class Command(BaseCommand):
    help = "Wipe real analyses and seed two synthetic demo projects (1 green, 1 not-green)."

    @transaction.atomic
    def handle(self, *args, **options):
        removed = Analysis.objects.count()
        Analysis.objects.all().delete()
        Client.objects.all().delete()

        for d in DEMO:
            verdict = constants.compute_verdict(
                d["eco_required"], d["eco_obtained"], d["stops"], d["green"],
            )
            client = Client.objects.create(**d["client"])
            Analysis.objects.create(
                kind=Analysis.KIND_BANK,
                client=client,
                number=d["number"],
                company_name=d["company_name"],
                source_type=Analysis.SOURCE_FILE,
                filenames=d["filenames"],
                verdict=verdict["code"],
                verdict_title=verdict["title"],
                summary=verdict["summary"],
                environmental_score=d["scores"][0],
                social_score=d["scores"][1],
                governance_score=d["scores"][2],
                overall_score=d["scores"][3],
                result_json={
                    "info": _info(d["info"]),
                    "eco_required": d["eco_required"],
                    "eco_obtained": d["eco_obtained"],
                    "stop_factors": d["stops"],
                    "green_criteria": d["green"],
                    "verdict": verdict,
                },
                language=d["language"],
            )

        for c in PORTFOLIO:
            Client.objects.create(**c)

        self.stdout.write(self.style.SUCCESS(
            f"Demo reset: removed {removed} analyses, seeded {len(DEMO)} synthetic analyses "
            f"({Analysis.objects.filter(verdict='green').count()} green, "
            f"{Analysis.objects.filter(verdict='not_green').count()} not-green) and "
            f"{Client.objects.count()} portfolio clients."))
