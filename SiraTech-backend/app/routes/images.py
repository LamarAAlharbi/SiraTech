from flask import Blueprint, jsonify, request

from app.services import images_service
from app.utils.validation import get_str_arg

images_bp = Blueprint("images", __name__, url_prefix="/api/v1/images")


@images_bp.get("")
def list_images():
    landmark_id = get_str_arg(request.args, "landmark_id")
    images = images_service.get_all_images(landmark_id=landmark_id)
    return jsonify({"count": len(images), "results": images})


@images_bp.get("/<string:image_id>")
def get_image(image_id):
    image = images_service.get_image_by_id(image_id)
    return jsonify(image)
