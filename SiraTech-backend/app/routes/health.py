from flask import Blueprint, jsonify, current_app

health_bp = Blueprint("health", __name__)


@health_bp.get("/health")
def health():
    return jsonify(
        {
            "status": "ok",
            "service": "sirategide-backend",
            "env": current_app.config.get("ENV"),
        }
    )
