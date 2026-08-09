"""
All Gemini vision integration for the "Hidden Gems" landmark-recognition
feature lives in this file. Nothing outside this module talks to the
vision-capable Gemini model directly — routes and other services only ever
call `identify_landmark()` below. This mirrors the isolation pattern used
by gemini_service.py (for /api/guide/chat), so the module stays swappable
and fully mockable in tests without a real API key or network access.

Design goals:
  - Never guess: if the model isn't reasonably confident, surface
    uncertain=True and identified_name=None instead of a fabricated name.
  - Never leak the API key — it's read from server-side config only and
    never appears in any request/response payload.
  - Ask for strict JSON output so parsing is predictable, but fail
    cleanly (a typed exception) if the model doesn't comply.
  - Support Arabic and English output.
"""

import json

from flask import current_app

# The Google GenAI SDK is imported lazily/defensively: importing this module
# must never fail just because the package (or network) isn't available in
# a given environment — callers get a clean VisionServiceError instead, and
# it keeps this module testable without the real SDK installed.
try:
    from google import genai
    from google.genai import types as genai_types

    _SDK_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised only when SDK truly missing
    genai = None
    genai_types = None
    _SDK_AVAILABLE = False


class VisionServiceError(Exception):
    """Raised for any vision-related failure: missing config, SDK, upstream API error, or unparsable output."""


LANGUAGE_NAMES = {
    "ar": "Arabic",
    "en": "English",
}

CONFIDENCE_LEVELS = ("high", "medium", "low")


def _build_prompt(language_code, hint_landmark_name=None, nearby_names=None):
    language_name = LANGUAGE_NAMES.get(language_code, "English")

    hint_line = ""
    if hint_landmark_name:
        hint_line = (
            f'The visitor believes they are at "{hint_landmark_name}" — treat this only as a '
            "possible hint, not a confirmed fact. Verify it against what the photo actually shows; "
            "do not simply confirm it if the image doesn't support it.\n"
        )

    nearby_line = ""
    if nearby_names:
        nearby_line = (
            "Known SiraTech landmarks near the visitor's reported location: "
            f"{', '.join(nearby_names)}. Treat these only as possible candidates if they visually "
            "match — do not favor them over what you actually see.\n"
        )

    return (
        "You are the landmark-recognition assistant for the SiraTech Hidden Gems feature, "
        "part of a Saudi Arabia cultural tourism app. Look at the attached photo and try to "
        "identify a visible landmark, monument, or notable architectural feature.\n\n"
        f"{hint_line}{nearby_line}\n"
        "RULES:\n"
        "- Never guess or invent a specific landmark name if you are not reasonably confident.\n"
        "- If you cannot confidently identify a specific, real landmark, set \"uncertain\" to "
        "true, set \"identified_name\" to null, and briefly describe what IS visible instead "
        "(e.g. general architectural style) without naming a place.\n"
        "- Set \"confidence\" to how certain you actually are: \"high\", \"medium\", or \"low\". "
        "Use \"low\" (and uncertain=true) whenever there's real doubt.\n"
        "- Do not invent historical facts, dates, or figures — keep the description limited to "
        "what's visually apparent plus only well-established general knowledge.\n\n"
        f"Respond in {language_name}. Respond with ONLY strict JSON, no markdown code fences, no "
        "commentary before or after, matching exactly this shape:\n"
        "{\n"
        '  "identified_name": string or null,\n'
        '  "category": string or null,\n'
        '  "description": string,\n'
        '  "confidence": "high" | "medium" | "low",\n'
        '  "uncertain": boolean\n'
        "}"
    )


def _get_client():
    api_key = current_app.config.get("GEMINI_API_KEY")
    if not api_key:
        raise VisionServiceError("GEMINI_API_KEY is not configured on the server.")

    if not _SDK_AVAILABLE:
        raise VisionServiceError(
            "The google-genai package is not installed. Run: pip install -r requirements.txt"
        )

    try:
        # api_key is passed straight into the SDK client and never stored,
        # logged, or included in any value this module returns.
        return genai.Client(api_key=api_key)
    except Exception as exc:
        raise VisionServiceError(f"Failed to initialize the Gemini client: {exc}") from exc


def _strip_code_fence(raw_text):
    text = raw_text.strip()
    if text.startswith("```"):
        text = text.strip("`").strip()
        if text.lower().startswith("json"):
            text = text[4:].strip()
    return text


def _parse_json_response(raw_text):
    raw_text = _strip_code_fence((raw_text or "").strip())
    try:
        data = json.loads(raw_text)
    except (json.JSONDecodeError, TypeError) as exc:
        raise VisionServiceError(f"Gemini returned non-JSON output: {exc}") from exc

    if not isinstance(data, dict):
        raise VisionServiceError("Gemini's JSON response was not an object.")
    return data


def _normalize_result(data, language):
    """
    Turn the model's raw JSON into a predictable shape and enforce the
    "never guess" rule server-side too — a name is only surfaced when the
    model both gave one AND reported at least medium confidence.
    """
    identified_name = data.get("identified_name")
    if identified_name is not None and not str(identified_name).strip():
        identified_name = None

    category = data.get("category")
    if category is not None and not str(category).strip():
        category = None

    description = str(data.get("description") or "").strip()
    if not description:
        description = "Not enough visual detail to describe this confidently."

    confidence = data.get("confidence")
    if confidence not in CONFIDENCE_LEVELS:
        confidence = "low"

    uncertain = bool(data.get("uncertain"))
    if identified_name is None or confidence == "low":
        uncertain = True

    return {
        "identified_name": None if uncertain else identified_name,
        "category": category,
        "description": description,
        "confidence": confidence,
        "uncertain": uncertain,
        "language": language,
    }


def identify_landmark(image_bytes, mime_type, language, hint_landmark_name=None, nearby_names=None):
    """
    Send an image to the configured Gemini vision model and ask it to
    identify a visible landmark or architectural feature.

    Args:
        image_bytes: raw image bytes (already validated by the caller).
        mime_type: e.g. "image/jpeg" — passed straight to Gemini.
        language: "ar" or "en" — the language of the returned text fields.
        hint_landmark_name: optional display name of a landmark the visitor
            claims to be at. Used only as an unverified hint.
        nearby_names: optional list of landmark display names near the
            visitor's reported location. Used only as candidates.

    Returns:
        dict: {
            "identified_name": str | None,
            "category": str | None,
            "description": str,
            "confidence": "high" | "medium" | "low",
            "uncertain": bool,
            "language": "ar" | "en",
        }

    Raises:
        VisionServiceError: on any configuration, SDK, or upstream API
            failure, or if the model's output can't be parsed. Callers
            should map this to a clean 503 — never let it bubble up as a
            raw exception to the client.
    """
    client = _get_client()
    model_name = current_app.config.get("GEMINI_VISION_MODEL") or current_app.config.get(
        "GEMINI_MODEL", "gemini-2.5-flash"
    )

    prompt = _build_prompt(language, hint_landmark_name=hint_landmark_name, nearby_names=nearby_names)

    try:
        response = client.models.generate_content(
            model=model_name,
            contents=[
                genai_types.Content(
                    role="user",
                    parts=[
                        genai_types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                        genai_types.Part(text=prompt),
                    ],
                )
            ],
            config=genai_types.GenerateContentConfig(
                temperature=0.2,
                response_mime_type="application/json",
            ),
        )
    except VisionServiceError:
        raise
    except Exception as exc:
        # Covers auth errors, network errors, quota/rate-limit errors, an
        # unsupported/rejected image, etc. — normalized into one clean,
        # typed error so nothing raw (including the API key) ever leaks.
        raise VisionServiceError(f"Gemini vision request failed: {exc}") from exc

    raw_text = getattr(response, "text", None)
    if not raw_text:
        raise VisionServiceError("Gemini returned an empty response.")

    data = _parse_json_response(raw_text)
    return _normalize_result(data, language)
