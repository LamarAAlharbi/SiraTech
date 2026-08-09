from flask import Blueprint, jsonify, request

from app.services import guide_service
from app.utils.validation import get_int_arg, get_str_arg, require_non_empty_str

guide_bp = Blueprint("guide", __name__, url_prefix="/api/v1/guide")


@guide_bp.get("/search")
def search():
    query = require_non_empty_str(get_str_arg(request.args, "q"), "q")
    limit = get_int_arg(request.args, "limit", default=20, minimum=1, maximum=100)

    results = guide_service.search(query, limit=limit)
    return jsonify(results)


@guide_bp.get("/landmarks/<string:landmark_id>")
def landmark_guide(landmark_id):
    guide = guide_service.get_landmark_guide(landmark_id)
    return jsonify(guide)


@guide_bp.get("/locations/<string:location_id>")
def location_guide(location_id):
    guide = guide_service.get_location_guide(location_id)
    return jsonify(guide)
