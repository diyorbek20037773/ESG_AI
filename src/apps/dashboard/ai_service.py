"""AI green-finance ESG analysis engine.

Reads project documents (PDF/image) or text directly — multimodal, long context, so no
OCR / embeddings / vector store is needed. Requests rotate across multiple API keys and
models with rate-limit fallback. The AI extracts structured answers; the final verdict is
computed deterministically in `constants.compute_verdict` (ported from the risk platform).
"""
import json
import logging
import re
import time

from django.conf import settings

from google import genai
from google.genai import types

from . import constants

logger = logging.getLogger(__name__)

MODELS = [
    "gemini-2.5-flash",       # strong default for reasoning-heavy verdicts
    "gemini-2.5-flash-lite",  # fast fallback
]

_rate_limited: dict[tuple[int, str], float] = {}

LANGUAGE_NAMES = {
    "uz": "Uzbek (o'zbek tilida)",
    "en": "English",
    "ru": "Russian (на русском языке)",
}


# ── keys / rotation ────────────────────────────────────────────

def _get_api_keys() -> list[str]:
    keys: list[str] = []
    for single in (getattr(settings, "GEMINI_API_KEY", ""),
                   getattr(settings, "GEMINI_API_KEY_2", ""),
                   getattr(settings, "GEMINI_API_KEY_3", "")):
        if single and single.strip():
            keys.append(single.strip())
    multi = getattr(settings, "GEMINI_API_KEYS", "")
    if multi:
        for part in re.split(r"[,\s]+", multi):
            if part.strip():
                keys.append(part.strip())
    seen, unique = set(), []
    for k in keys:
        if k not in seen:
            seen.add(k)
            unique.append(k)
    return unique


def _is_rate_limited(key_idx, model):
    key = (key_idx, model)
    if key not in _rate_limited:
        return False
    if time.time() - _rate_limited[key] > 86400:
        del _rate_limited[key]
        return False
    return True


def _mark_rate_limited(key_idx, model):
    _rate_limited[(key_idx, model)] = time.time()


def _ask_ai(system_prompt, user_message, files=None, max_tokens=8192):
    """Send a request to the AI, trying every key and model until one succeeds.

    `files` is an optional list of (bytes, mime_type) tuples for multimodal input.
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
                        client_kwargs["http_options"] = types.HttpOptions(timeout=90000)
                    except Exception:
                        pass
                client = genai.Client(**client_kwargs)
                cfg_kwargs = dict(
                    system_instruction=system_prompt,
                    temperature=0.2,
                    max_output_tokens=max_tokens,
                    response_mime_type="application/json",
                )
                if model.startswith("gemini-2.5-flash") and hasattr(types, "ThinkingConfig"):
                    cfg_kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=0)

                if files:
                    contents = [types.Part.from_bytes(data=data, mime_type=mime)
                                for (data, mime) in files]
                    contents.append(user_message)
                else:
                    contents = user_message

                response = client.models.generate_content(
                    model=model, contents=contents,
                    config=types.GenerateContentConfig(**cfg_kwargs),
                )
                text = (response.text or "").strip()
                text = re.sub(r"^```(?:json)?\s*\n?", "", text)
                text = re.sub(r"\n?```\s*$", "", text)
                logger.info("[key%s:%s] ok (%d chars)", key_idx, model, len(text))
                return text
            except Exception as e:
                msg = str(e)
                last_error = e
                logger.warning("[key%s:%s] error: %s", key_idx, model, msg[:160])
                if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
                    _mark_rate_limited(key_idx, model)
                    continue
                for m in MODELS:
                    _mark_rate_limited(key_idx, m)
                break
    if last_error:
        raise last_error
    raise ValueError("No AI API key configured")


def _parse_json(text):
    try:
        start = text.index("{")
        end = text.rindex("}") + 1
        js = text[start:end]
    except ValueError:
        logger.error("No JSON braces in: %s", text[:200])
        return None
    try:
        return json.loads(js)
    except json.JSONDecodeError:
        pass
    try:
        return json.loads(re.sub(r"(?<=[\w])'(?=[\w])", "’", js))
    except json.JSONDecodeError as e:
        logger.error("JSON parse failed: %s", e)
        return None


def _clamp(value):
    try:
        return max(0, min(100, int(round(float(value)))))
    except (TypeError, ValueError):
        return 0


def _as_bool(v):
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.strip().lower() in ("true", "ha", "yes", "1")
    return bool(v)


# ── green-finance analysis ─────────────────────────────────────

def _build_prompt(language):
    lang = LANGUAGE_NAMES.get(language, LANGUAGE_NAMES["en"])
    info_q = "\n".join(f"{i+1}. {q}" for i, q in enumerate(constants.INFO_QUESTIONS))
    stop_q = "\n".join(
        f"{i}. {q}  [kalit so'zlar: {', '.join(kt)}]"
        for i, (q, kt) in enumerate(constants.STOP_FACTORS))
    green_q = "\n".join(
        f"{i}. {q}  [kalit so'zlar: {', '.join(kt)}]"
        for i, (q, kt) in enumerate(constants.GREEN_CRITERIA))
    return f"""You are a rigorous green-finance ESG analyst for a bank in Uzbekistan.
You are given a borrower's project/credit documents (or text). Analyse ONLY what the
documents actually state — never invent facts. If information is missing, say so and set
boolean values to false.

Answer these INFORMATION questions (Uzbek), quoting exact figures/names when present:
{info_q}

Evaluate ECO-EXPERTISE:
- required: {constants.ECO_EXPERTISE_REQUIRED[0]}
- obtained: {constants.ECO_EXPERTISE_OBTAINED[0]}

Evaluate each STOP-FACTOR (exclusion activity). value=true ONLY if that activity is
genuinely part of the project:
{stop_q}

Evaluate each GREEN CRITERION (renewable/green activity). value=true ONLY if genuinely present:
{green_q}

Also give ESG pillar scores 0-100 (higher = better ESG). Write all `evidence`, `answer` and
`summary` text in {lang}.

Respond with ONLY this JSON (no other text):
{{
  "company_name": "<detected borrower name or empty>",
  "info": [{{"question": "<the question>", "answer": "<answer or 'Ma'lumot topilmadi'>"}} ... 7 items in order],
  "eco_expertise_required": {{"value": <bool>, "evidence": "<short>"}},
  "eco_expertise_obtained": {{"value": <bool>, "evidence": "<short>"}},
  "stop_factors": [{{"index": <int 0-11>, "value": <bool>, "evidence": "<short>"}} ... 12 items],
  "green_criteria": [{{"index": <int 0-8>, "value": <bool>, "evidence": "<short>"}} ... 9 items],
  "environmental_score": <int>, "social_score": <int>, "governance_score": <int>,
  "overall_score": <int>,
  "summary": "<3-5 sentence overall ESG summary>"
}}"""


def analyze_green_finance(*, files=None, text=None, client_name="", language="uz"):
    """Run the full green-finance ESG evaluation.

    `files`: list of (bytes, mime). Or `text`. Returns a normalized result dict with the
    deterministic verdict attached. Raises on total API failure.
    """
    system = _build_prompt(language)
    hint = f"Client (borrower) name hint: {client_name}\n\n" if client_name else ""
    if files:
        user_msg = f"{hint}Analyse the attached project documents and produce the JSON."
        raw = _ask_ai(system, user_msg, files=files)
    else:
        user_msg = f"{hint}Analyse the following project content and produce the JSON:\n\n{text or ''}"
        raw = _ask_ai(system, user_msg)

    parsed = _parse_json(raw) or {}

    # Attach canonical question text by index; normalize booleans.
    stop_by_idx = {}
    for item in parsed.get("stop_factors", []) or []:
        try:
            stop_by_idx[int(item.get("index"))] = item
        except (TypeError, ValueError):
            continue
    green_by_idx = {}
    for item in parsed.get("green_criteria", []) or []:
        try:
            green_by_idx[int(item.get("index"))] = item
        except (TypeError, ValueError):
            continue

    stop_factors = []
    for i, (q, _kt) in enumerate(constants.STOP_FACTORS):
        it = stop_by_idx.get(i, {})
        stop_factors.append({"question": q, "value": _as_bool(it.get("value")),
                             "evidence": (it.get("evidence") or "").strip()})
    green_criteria = []
    for i, (q, _kt) in enumerate(constants.GREEN_CRITERIA):
        it = green_by_idx.get(i, {})
        green_criteria.append({"question": q, "value": _as_bool(it.get("value")),
                               "evidence": (it.get("evidence") or "").strip()})

    eco_req = parsed.get("eco_expertise_required") or {}
    eco_obt = parsed.get("eco_expertise_obtained") or {}
    eco_required = {"value": _as_bool(eco_req.get("value")), "evidence": (eco_req.get("evidence") or "").strip()}
    eco_obtained = {"value": _as_bool(eco_obt.get("value")), "evidence": (eco_obt.get("evidence") or "").strip()}

    info = []
    parsed_info = parsed.get("info") or []
    for i, q in enumerate(constants.INFO_QUESTIONS):
        ans = parsed_info[i].get("answer") if i < len(parsed_info) and isinstance(parsed_info[i], dict) else ""
        info.append({"question": q, "answer": (ans or "").strip()})

    env = _clamp(parsed.get("environmental_score"))
    soc = _clamp(parsed.get("social_score"))
    gov = _clamp(parsed.get("governance_score"))
    overall = parsed.get("overall_score")
    overall = _clamp(overall) if overall is not None else round((env + soc + gov) / 3)

    verdict = constants.compute_verdict(eco_required, eco_obtained, stop_factors, green_criteria)

    return {
        "company_name": (parsed.get("company_name") or client_name or "").strip(),
        "verdict": verdict,
        "environmental_score": env, "social_score": soc,
        "governance_score": gov, "overall_score": overall,
        "summary": (parsed.get("summary") or verdict["summary"]).strip(),
        "info": info,
        "eco_required": eco_required, "eco_obtained": eco_obtained,
        "stop_factors": stop_factors, "green_criteria": green_criteria,
    }
