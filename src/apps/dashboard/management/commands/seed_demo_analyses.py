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
        "client": ("Quyosh Vodiy Solar LLC", "300100200", "Qayta tiklanuvchi energiya", "Jizzax"),
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
        "client": ("Oqtosh Energo LLC", "300300400", "Energetika", "Navoiy"),
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
            name, stir, industry, region = d["client"]
            client = Client.objects.create(name=name, stir=stir, industry=industry, region=region)
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

        self.stdout.write(self.style.SUCCESS(
            f"Demo analyses reset: removed {removed}, seeded {len(DEMO)} synthetic "
            f"({Analysis.objects.filter(verdict='green').count()} green, "
            f"{Analysis.objects.filter(verdict='not_green').count()} not-green)."))
