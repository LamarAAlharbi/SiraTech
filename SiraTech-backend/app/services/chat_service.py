"""
Orchestrates the /api/guide/chat feature: looks up the landmark (reusing the
existing services, so it 404s cleanly like every other endpoint), then hands
off to gemini_service for the actual AI call. All Gemini-specific code stays
in gemini_service.py — this module only does SiraTech domain lookups.
"""

from app.errors import ServiceUnavailableError
from app.services import gemini_service
from app.services.gemini_service import GeminiServiceError
from app.services.landmarks_service import get_landmark_by_id
from app.services.locations_service import get_location_by_id


def get_chat_answer(landmark_id, user_message, language, conversation_context=None):
    # Raises NotFoundError itself (handled by the global error handler) if
    # the landmark id doesn't exist — same behavior as every other endpoint.
    landmark = get_landmark_by_id(landmark_id)
    location = get_location_by_id(landmark["location_id"])

    try:
        result = gemini_service.get_landmark_answer(
            landmark=landmark,
            location=location,
            user_message=user_message,
            language=language,
            conversation_context=conversation_context,
        )
    except GeminiServiceError as exc:
        raise ServiceUnavailableError(
            "The AI guide is temporarily unavailable. Please try again shortly.",
            details={"reason": str(exc)},
        ) from exc

    result["landmark_id"] = landmark_id
    return result
