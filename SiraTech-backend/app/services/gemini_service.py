"""
All Gemini (Google GenAI) integration lives in this file. Nothing outside
this module talks to Gemini directly — routes and other services only ever
call `get_landmark_answer()` below.

Design goals for the /api/guide/chat feature:
  - Stay strictly scoped to the selected landmark (no itinerary/pricing/
    booking/transportation content, even if asked).
  - Never invent historical facts; say so plainly when unsure.
  - Prefer grounded, search-supported claims (Gemini's Google Search tool),
    and surface that grounding metadata back to the caller when present.
  - Support Arabic and English output.
  - Fail cleanly (a typed exception) if Gemini/the API key/the SDK is
    unavailable, instead of leaking a raw stack trace to the client.
"""

import re

from flask import current_app

# The Google GenAI SDK is imported lazily/defensively: importing this module
# must never fail just because the package (or network) isn't available in
# a given environment — callers get a clean GeminiServiceError instead, and
# it keeps this module testable without the real SDK installed.
try:
    from google import genai
    from google.genai import types as genai_types

    _SDK_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised only when SDK truly missing
    genai = None
    genai_types = None
    _SDK_AVAILABLE = False


class GeminiServiceError(Exception):
    """Raised for any Gemini-related failure: missing config, SDK, or API error."""


LANGUAGE_NAMES = {
    "ar": "Arabic",
    "en": "English",
}

_ANSWER_MARKER = "ANSWER:"
_SPEECH_MARKER = "SPEECH:"

_MAX_SPEECH_FALLBACK_CHARS = 220


def _build_system_instruction(landmark_name, location_name, language_code):
    language_name = LANGUAGE_NAMES.get(language_code, "English")
    return (
        "You are the official AI cultural guide inside the SiraTech app, speaking "
        f"specifically about \"{landmark_name}\" in {location_name}, Saudi Arabia.\n\n"
        "STRICT SCOPE:\n"
        f"- Only discuss {landmark_name}: its history, culture, architecture, "
        "significance, people connected to it, and directly related context.\n"
        "- If the user asks about itineraries, trip planning, multi-day schedules, "
        "prices, costs, packages, hotels, accommodation, transportation, or booking, "
        "do NOT answer that part. Briefly say it's outside what this guide covers, "
        "and steer the conversation back to the landmark itself.\n"
        "- If asked about a different landmark or place, briefly say you can only "
        "speak about this specific site, and invite a follow-up question about it.\n\n"
        "ACCURACY RULES:\n"
        "- Never invent historical facts, dates, names, or figures.\n"
        "- Prefer information you can verify or that is supported by search grounding "
        "for factual claims (dates, names, events, measurements).\n"
        "- If reliable information isn't available to you, say so plainly instead of "
        "guessing — do not fabricate an answer to sound complete.\n\n"
        "LANGUAGE:\n"
        f"- Respond ONLY in {language_name}, regardless of the language the user wrote in.\n\n"
        "RESPONSE FORMAT (follow exactly, plain text, no markdown headers):\n"
        f"{_ANSWER_MARKER}\n"
        "<a helpful, complete answer, a few sentences to a short paragraph>\n"
        f"{_SPEECH_MARKER}\n"
        "<the same answer compressed into one short, natural spoken sentence, "
        "suitable for text-to-speech, in the same language>"
    )


def _build_contents(conversation_context, user_message):
    """Turn prior turns + the new message into Gemini `contents`."""
    contents = []
    for turn in conversation_context or []:
        role = "model" if turn["role"] == "assistant" else "user"
        contents.append(
            genai_types.Content(role=role, parts=[genai_types.Part(text=turn["content"])])
        )
    contents.append(genai_types.Content(role="user", parts=[genai_types.Part(text=user_message)]))
    return contents


def _parse_answer_and_speech(raw_text, language_code):
    """
    Parse the model's ANSWER:/SPEECH: formatted text. Falls back gracefully
    if the model didn't follow the format exactly (still returns something
    useful rather than erroring).
    """
    raw_text = (raw_text or "").strip()

    answer_match = re.search(
        rf"{_ANSWER_MARKER}\s*(.*?)\s*(?:{_SPEECH_MARKER}|$)", raw_text, re.DOTALL
    )
    speech_match = re.search(rf"{_SPEECH_MARKER}\s*(.*)", raw_text, re.DOTALL)

    answer = answer_match.group(1).strip() if answer_match else raw_text
    speech = speech_match.group(1).strip() if speech_match else None

    if not answer:
        answer = raw_text

    if not speech:
        speech = answer[:_MAX_SPEECH_FALLBACK_CHARS].strip()
        if len(answer) > _MAX_SPEECH_FALLBACK_CHARS:
            speech += "…" if language_code == "ar" else "..."

    return answer, speech


def _extract_grounding(response):
    """
    Pull grounding/source metadata off a Gemini response, if present.
    Returns None when the model didn't use search grounding for this answer.
    """
    try:
        candidates = getattr(response, "candidates", None) or []
        if not candidates:
            return None

        metadata = getattr(candidates[0], "grounding_metadata", None)
        if not metadata:
            return None

        sources = []
        for chunk in getattr(metadata, "grounding_chunks", None) or []:
            web = getattr(chunk, "web", None)
            if web is not None:
                sources.append(
                    {
                        "title": getattr(web, "title", None),
                        "uri": getattr(web, "uri", None),
                    }
                )

        search_queries = list(getattr(metadata, "web_search_queries", None) or [])

        if not sources and not search_queries:
            return None

        return {"sources": sources, "search_queries": search_queries}
    except Exception:  # pragma: no cover - defensive, metadata shape can vary by SDK version
        return None


def _get_client():
    api_key = current_app.config.get("GEMINI_API_KEY")
    if not api_key:
        raise GeminiServiceError("GEMINI_API_KEY is not configured on the server.")

    if not _SDK_AVAILABLE:
        raise GeminiServiceError(
            "The google-genai package is not installed. Run: pip install -r requirements.txt"
        )

    try:
        return genai.Client(api_key=api_key)
    except Exception as exc:
        raise GeminiServiceError(f"Failed to initialize the Gemini client: {exc}") from exc


def get_landmark_answer(landmark, location, user_message, language, conversation_context=None):
    """
    Ask Gemini a question about a specific landmark, grounded in Google Search
    when possible, strictly scoped to that landmark.

    Args:
        landmark: dict with at least "name_en" / "name_ar".
        location: dict with at least "name_en" / "name_ar".
        user_message: the visitor's question, as free text.
        language: "ar" or "en" — the language to respond in.
        conversation_context: optional list of {"role", "content"} prior turns.

    Returns:
        dict: {
            "answer": str,
            "short_answer_for_speech": str,
            "language": "ar" | "en",
            "grounding": dict | None,
        }

    Raises:
        GeminiServiceError: on any configuration, SDK, or upstream API failure.
            Callers should map this to a clean 503 — never let it bubble up
            as a raw exception to the client.
    """
    client = _get_client()
    model_name = current_app.config.get("GEMINI_MODEL", "gemini-2.5-flash")

    landmark_name = landmark["name_ar"] if language == "ar" else landmark["name_en"]
    location_name = location["name_ar"] if language == "ar" else location["name_en"]

    system_instruction = _build_system_instruction(landmark_name, location_name, language)

    try:
        contents = _build_contents(conversation_context, user_message)
        response = client.models.generate_content(
            model=model_name,
            contents=contents,
            config=genai_types.GenerateContentConfig(
                system_instruction=system_instruction,
                tools=[genai_types.Tool(google_search=genai_types.GoogleSearch())],
                temperature=0.3,
            ),
        )
    except GeminiServiceError:
        raise
    except Exception as exc:
        # Covers auth errors, network errors, quota/rate-limit errors, etc.
        # from the SDK — normalized into one clean, typed error.
        raise GeminiServiceError(f"Gemini request failed: {exc}") from exc

    raw_text = getattr(response, "text", None)
    if not raw_text:
        raise GeminiServiceError("Gemini returned an empty response.")

    answer, speech = _parse_answer_and_speech(raw_text, language)
    grounding = _extract_grounding(response)

    return {
        "answer": answer,
        "short_answer_for_speech": speech,
        "language": language,
        "grounding": grounding,
    }
