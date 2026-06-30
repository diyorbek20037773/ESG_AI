"""AI-based ESG analysis engine.

The engine reads PDF/image documents and free text directly (multimodal, long context),
so no separate OCR, embedding or vector-store step is required. Requests rotate across
multiple API keys and models with rate-limit fallback.
"""
import json
import logging
import re
import time

from django.conf import settings

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# Multi-key + multi-model fallback
# ──────────────────────────────────────────────

MODELS = [
    "gemini-2.5-flash-lite",  # fastest — higher RPM/RPD
    "gemini-2.5-flash",       # fallback — stronger reasoning
]

# Remember rate-limited (key_index, model) pairs; cleared after 24h.
_rate_limited: dict[tuple[int, str], float] = {}

LANGUAGE_NAMES = {
    "uz": "Uzbek (o'zbek tilida)",
    "en": "English",
    "ru": "Russian (на русском языке)",
}


def _get_api_keys() -> list[str]:
    """Collect every configured API key.

    Supports:
      - GEMINI_API_KEY / GEMINI_API_KEY_2 / GEMINI_API_KEY_3 (separate)
      - GEMINI_API_KEYS (one variable, comma/space/newline separated)
    """
    keys: list[str] = []
    for single in (
        getattr(settings, "GEMINI_API_KEY", ""),
        getattr(settings, "GEMINI_API_KEY_2", ""),
        getattr(settings, "GEMINI_API_KEY_3", ""),
    ):
        if single and single.strip():
            keys.append(single.strip())

    multi = getattr(settings, "GEMINI_API_KEYS", "")
    if multi:
        for part in re.split(r"[,\s]+", multi):
            part = part.strip()
            if part:
                keys.append(part)

    seen: set[str] = set()
    unique: list[str] = []
    for k in keys:
        if k not in seen:
            seen.add(k)
            unique.append(k)
    return unique


def _is_rate_limited(key_idx: int, model: str) -> bool:
    key = (key_idx, model)
    if key not in _rate_limited:
        return False
    if time.time() - _rate_limited[key] > 86400:
        del _rate_limited[key]
        return False
    return True


def _mark_rate_limited(key_idx: int, model: str):
    _rate_limited[(key_idx, model)] = time.time()


def _ask_ai(
    system_prompt: str,
    user_message: str,
    file_bytes: bytes | None = None,
    file_mime: str = "application/pdf",
    max_tokens: int = 4096,
) -> str:
    """Send a request to the AI engine, trying every key and model until one succeeds.

    If file_bytes is given (PDF or image), the request is multimodal.
    Returns the raw response text (JSON string).
    """
    keys = _get_api_keys()
    if not keys:
        raise ValueError("AI API keys are not configured (set GEMINI_API_KEYS)")

    last_error = None

    for key_idx, api_key in enumerate(keys):
        for model in MODELS:
            if _is_rate_limited(key_idx, model):
                continue

            try:
                client_kwargs = {"api_key": api_key}
                if hasattr(types, "HttpOptions"):
                    try:
                        # Per-attempt cap so a slow/stuck key fails over fast.
                        client_kwargs["http_options"] = types.HttpOptions(timeout=45000)
                    except Exception:
                        pass
                client = genai.Client(**client_kwargs)

                cfg_kwargs = dict(
                    system_instruction=system_prompt,
                    temperature=0.3,
                    max_output_tokens=max_tokens,
                    response_mime_type="application/json",
                )
                if model.startswith("gemini-2.5-flash") and hasattr(types, "ThinkingConfig"):
                    cfg_kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=0)

                if file_bytes:
                    contents = [
                        types.Part.from_bytes(data=file_bytes, mime_type=file_mime),
                        user_message,
                    ]
                else:
                    contents = user_message

                response = client.models.generate_content(
                    model=model,
                    contents=contents,
                    config=types.GenerateContentConfig(**cfg_kwargs),
                )
                result_text = (response.text or "").strip()
                result_text = re.sub(r"^```(?:json)?\s*\n?", "", result_text)
                result_text = re.sub(r"\n?```\s*$", "", result_text)

                logger.info("[key%s:%s] ESG ok (first 200): %s",
                            key_idx, model, result_text[:200])
                return result_text

            except Exception as e:
                error_msg = str(e)
                last_error = e
                logger.warning("[key%s:%s] error: %s", key_idx, model, error_msg[:160])

                if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                    _mark_rate_limited(key_idx, model)
                    continue
                if any(c in error_msg for c in (
                    "403", "PERMISSION_DENIED", "400", "API_KEY_INVALID", "INVALID_ARGUMENT",
                )):
                    for m in MODELS:
                        _mark_rate_limited(key_idx, m)
                    break
                # Any other error (5xx, timeout): skip this key, move on.
                for m in MODELS:
                    _mark_rate_limited(key_idx, m)
                break

    if last_error:
        raise last_error
    raise ValueError("No AI API key configured")


def _parse_json(text: str) -> dict | None:
    """Safely extract a JSON object from the AI response."""
    try:
        start = text.index("{")
        end = text.rindex("}") + 1
        json_str = text[start:end]
    except ValueError:
        logger.error("No JSON braces found in: %s", text[:200])
        return None

    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        pass

    # Uzbek apostrophe inside words breaks JSON — replace with a typographic one.
    try:
        fixed = re.sub(r"(?<=[\w])'(?=[\w])", "’", json_str)
        return json.loads(fixed)
    except json.JSONDecodeError as e:
        logger.error("JSON parse failed: %s. Text: %s", e, json_str[:300])
        return None


# ──────────────────────────────────────────────
# ESG analysis
# ──────────────────────────────────────────────

def _clamp_score(value) -> int:
    try:
        n = int(round(float(value)))
    except (TypeError, ValueError):
        return 0
    return max(0, min(100, n))


def _build_system_prompt(language: str) -> str:
    lang_name = LANGUAGE_NAMES.get(language, LANGUAGE_NAMES["en"])
    return f"""You are an expert ESG (Environmental, Social, Governance) analyst.
You are given a company document (report, filing, sustainability report) or free text.
Analyse it and produce a rigorous ESG assessment.

Score each pillar from 0 to 100 (higher = better ESG performance). Base every score and
finding ONLY on evidence in the provided content. If the content lacks information for a
pillar, give a low-confidence mid-range score and say so in that pillar's summary — do not
invent facts.

Write ALL human-readable text (summaries, findings, risks, recommendations) in {lang_name}.

Respond with ONLY a JSON object, no other text, in exactly this shape:
{{
  "company_name": "<detected company name or empty string>",
  "environmental_score": <int 0-100>,
  "social_score": <int 0-100>,
  "governance_score": <int 0-100>,
  "overall_score": <int 0-100>,
  "overall_summary": "<3-5 sentence overall ESG summary>",
  "environmental_summary": "<2-3 sentences on the Environmental pillar>",
  "social_summary": "<2-3 sentences on the Social pillar>",
  "governance_summary": "<2-3 sentences on the Governance pillar>",
  "key_findings": ["<finding>", "..."],
  "risks": ["<material ESG risk>", "..."],
  "recommendations": ["<concrete, actionable recommendation>", "..."]
}}

Give 3-6 items each for key_findings, risks, and recommendations. overall_score should
roughly reflect the three pillar scores."""


def analyze_esg(
    *,
    text: str | None = None,
    file_bytes: bytes | None = None,
    file_mime: str | None = None,
    company_name: str = "",
    language: str = "uz",
) -> dict:
    """Run an ESG analysis.

    Provide either `text` or (`file_bytes` + `file_mime`). Returns a normalized dict with
    integer scores plus the structured analysis fields. Raises on total API failure.
    """
    system = _build_system_prompt(language)

    hint = f"Company name hint: {company_name}\n\n" if company_name else ""
    if file_bytes:
        user_msg = (
            f"{hint}Analyse the attached document and produce the ESG assessment JSON."
        )
        raw = _ask_ai(system, user_msg, file_bytes=file_bytes,
                      file_mime=file_mime or "application/pdf")
    else:
        user_msg = (
            f"{hint}Analyse the following content and produce the ESG assessment JSON:\n\n"
            f"{text or ''}"
        )
        raw = _ask_ai(system, user_msg)

    parsed = _parse_json(raw) or {}

    env = _clamp_score(parsed.get("environmental_score"))
    soc = _clamp_score(parsed.get("social_score"))
    gov = _clamp_score(parsed.get("governance_score"))
    overall = parsed.get("overall_score")
    overall = _clamp_score(overall) if overall is not None else round((env + soc + gov) / 3)

    def _as_list(v):
        if isinstance(v, list):
            return [str(x) for x in v if str(x).strip()]
        if isinstance(v, str) and v.strip():
            return [v.strip()]
        return []

    return {
        "company_name": (parsed.get("company_name") or company_name or "").strip(),
        "environmental_score": env,
        "social_score": soc,
        "governance_score": gov,
        "overall_score": overall,
        "overall_summary": (parsed.get("overall_summary") or "").strip(),
        "environmental_summary": (parsed.get("environmental_summary") or "").strip(),
        "social_summary": (parsed.get("social_summary") or "").strip(),
        "governance_summary": (parsed.get("governance_summary") or "").strip(),
        "key_findings": _as_list(parsed.get("key_findings")),
        "risks": _as_list(parsed.get("risks")),
        "recommendations": _as_list(parsed.get("recommendations")),
    }
