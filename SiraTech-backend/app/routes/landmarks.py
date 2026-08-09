from flask import Blueprint, jsonify, request

from app.services import landmarks_service
from app.utils.validation import get_str_arg

landmarks_bp = Blueprint("landmarks", __name__, url_prefix="/api/v1/landmarks")


@landmarks_bp.get("")
def list_landmarks():
    location_id = get_str_arg(request.args, "location_id")
    category = get_str_arg(request.args, "category")
    unesco_arg = get_str_arg(request.args, "unesco", choices=["true", "false"])
    unesco_only = unesco_arg == "true"

    landmarks = landmarks_service.get_all_landmarks(
        location_id=location_id,
        category=category,
        unesco_only=unesco_only,
    )
    return jsonify({"count": len(landmarks), "results": landmarks})


@landmarks_bp.get("/categories")
def list_categories():
    categories = landmarks_service.list_categories()
    return jsonify({"count": len(categories), "results": categories})


@landmarks_bp.get("/<string:landmark_id>")
def get_landmark(landmark_id):
    landmark = landmarks_service.get_landmark_by_id(landmark_id)
    return jsonify(landmark)
