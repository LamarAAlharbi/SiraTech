from flask import Blueprint, jsonify, request

from app.errors import ValidationError
from app.services import vision_analyze_service
from app.utils.validation import (
    get_float_arg,
    get_str_arg,
    require_image_file,
    require_language,
)

vision_bp = Blueprint("vision", __name__, url_prefix="/api/vision")


@vision_bp.post("/analyze")
def analyze():
    """
    Identify a visible landmark/architectural feature in an uploaded photo
    (SiraTech Hidden Gems).

    Expects multipart/form-data:
      - image (required): the photo file (jpeg/png/webp, size-limited).
      - language (required): "ar" or "en".
      - landmark_id (optional): a landmark the visitor believes they're at —
        used only as an unverified hint.
      - latitude / longitude (optional, must be given together): the
        visitor's reported location — used only to narrow match candidates.

    This is a recognition step only. Once it returns a possible_landmark_id,
    the frontend should call GET /api/v1/guide/landmarks/<possible_landmark_id>
    to fetch the verified historical record for that landmark.
    """
    image_file = require_image_file(request, "image")
    language = require_language(request.form, "language")

    landmark_id = get_str_arg(request.form, "landmark_id")
    latitude = get_float_arg(request.form, "latitude", minimum=-90, maximum=90)
    longitude = get_float_arg(request.form, "longitude", minimum=-180, maximum=180)

    if (latitude is None) != (longitude is None):
        raise ValidationError(
            "'latitude' and 'longitude' must be provided together.",
            details={"latitude": latitude, "longitude": longitude},
        )

    image_bytes = image_file.read()

    result = vision_analyze_service.analyze_image(
        image_bytes=image_bytes,
        mime_type=image_file.mimetype,
        language=language,
        landmark_id=landmark_id,
        latitude=latitude,
        longitude=longitude,
    )
    return jsonify(result)
