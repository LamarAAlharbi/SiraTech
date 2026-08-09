from flask import Blueprint, jsonify, request

from app.services import gamification_service
from app.utils.validation import get_body_str, get_json_body, require_body_str

gamification_bp = Blueprint("gamification", __name__, url_prefix="/api/gamification")


@gamification_bp.get("/profile/<string:user_id>")
def get_profile(user_id):
    profile = gamification_service.get_profile(user_id)
    return jsonify(profile)


@gamification_bp.post("/discover")
def discover():
    body = get_json_body(request)
    user_id = require_body_str(body, "user_id")
    discovery_type = require_body_str(body, "type")
    item_id = require_body_str(body, "item_id")
    location_id = get_body_str(body, "location_id")

    result = gamification_service.record_discovery(
        user_id=user_id,
        discovery_type=discovery_type,
        item_id=item_id,
        location_id=location_id,
    )
    return jsonify(result)
