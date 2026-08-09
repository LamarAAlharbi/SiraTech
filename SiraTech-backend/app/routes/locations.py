from flask import Blueprint, jsonify, request

from app.services import locations_service
from app.utils.validation import get_str_arg

locations_bp = Blueprint("locations", __name__, url_prefix="/api/v1/locations")


@locations_bp.get("")
def list_locations():
    region = get_str_arg(request.args, "region")
    locations = locations_service.get_all_locations(region=region)
    return jsonify({"count": len(locations), "results": locations})


@locations_bp.get("/regions")
def list_regions():
    regions = locations_service.list_regions()
    return jsonify({"count": len(regions), "results": regions})


@locations_bp.get("/<string:location_id>")
def get_location(location_id):
    location = locations_service.get_location_by_id(location_id)
    return jsonify(location)
