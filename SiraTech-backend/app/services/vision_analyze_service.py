"""
Orchestrates POST /api/vision/analyze (SiraTech Hidden Gems).

This module never talks to Gemini directly — that's entirely inside
vision_service.py. Here we only do SiraTech domain work: resolve an
optional landmark_id hint, find landmarks near an optional lat/lon, call
vision_service for the actual recognition, and try to cross-reference the
model's answer against SiraTech's own verified landmark data to produce a
`possible_landmark_id`. Same separation chat_service.py uses for
gemini_service.py.

`possible_landmark_id`, when present, is a valid id the frontend can pass
straight to GET /api/v1/guide/landmarks/<possible_landmark_id> to fetch the
verified historical record (curated data + images) for that landmark — as
opposed to the AI's own description, which is a best-effort visual read and
should be treated as provisional.
"""

import math

from app.errors import ServiceUnavailableError
from app.services import vision_service
from app.services.vision_service import VisionServiceError
from app.services.landmarks_service import get_landmark_by_id, get_all_landmarks
from app.services.locations_service import get_all_locations

# How close (in km) a visitor's reported lat/lon must be to one of our
# seeded locations for that location's landmarks to be offered to Gemini
# as match candidates. Generous on purpose — this is a hint, not a filter.
_NEARBY_RADIUS_KM = 75


def _haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(d_lambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _nearby_landmarks(latitude, longitude):
    if latitude is None or longitude is None:
        return []

    nearby = []
    for location in get_all_locations():
        distance = _haversine_km(latitude, longitude, location["latitude"], location["longitude"])
        if distance <= _NEARBY_RADIUS_KM:
            nearby.extend(get_all_landmarks(location_id=location["id"]))
    return nearby


def _name_matches(identified_name, landmark):
    if not identified_name:
        return False
    needle = identified_name.strip().lower()
    if not needle:
        return False
    for key in ("name_en", "name_ar"):
        haystack = (landmark.get(key) or "").strip().lower()
        if haystack and (needle in haystack or haystack in needle):
            return True
    return False


def _resolve_possible_landmark_id(identified_name, hint_landmark, nearby_landmarks):
    """
    Best-effort cross-reference of the model's guess against SiraTech's own
    data. Never invents an id: only returns one when a name actually
    matches a known landmark's name.
    """
    # A visitor-supplied landmark_id that the model's own guess corroborates
    # is the strongest possible signal.
    if hint_landmark and _name_matches(identified_name, hint_landmark):
        return hint_landmark["id"]

    # Otherwise, check landmarks near the visitor's reported location.
    for landmark in nearby_landmarks:
        if _name_matches(identified_name, landmark):
            return landmark["id"]

    return None


def analyze_image(image_bytes, mime_type, language, landmark_id=None, latitude=None, longitude=None):
    hint_landmark = None
    if landmark_id:
        # Raises NotFoundError itself (handled by the global error handler)
        # if the id doesn't exist — same behavior as every other endpoint
        # that accepts a landmark_id.
        hint_landmark = get_landmark_by_id(landmark_id)

    nearby_landmarks = _nearby_landmarks(latitude, longitude)

    try:
        result = vision_service.identify_landmark(
            image_bytes=image_bytes,
            mime_type=mime_type,
            language=language,
            hint_landmark_name=hint_landmark["name_en"] if hint_landmark else None,
            nearby_names=[lm["name_en"] for lm in nearby_landmarks] or None,
        )
    except VisionServiceError as exc:
        raise ServiceUnavailableError(
            "The landmark recognition service is temporarily unavailable. Please try again shortly.",
            details={"reason": str(exc)},
        ) from exc

    possible_landmark_id = None
    if not result["uncertain"]:
        possible_landmark_id = _resolve_possible_landmark_id(
            result["identified_name"], hint_landmark, nearby_landmarks
        )

    return {
        "identified_name": result["identified_name"],
        "category": result["category"],
        "description": result["description"],
        "possible_landmark_id": possible_landmark_id,
        "confidence": result["confidence"],
        "uncertain": result["uncertain"],
        "language": result["language"],
    }
