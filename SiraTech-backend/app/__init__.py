"""
Application factory for the SiraTech Guide backend.

Usage:
    from app import create_app
    app = create_app()
"""

from flask import Flask, jsonify
from flask_cors import CORS

from app.config import Config
from app.errors import register_error_handlers


def create_app(config_object=Config):
    app = Flask(__name__)
    app.config.from_object(config_object)

    # CORS: only allow the configured frontend origin(s), read from .env
    CORS(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}, r"/health": {"origins": "*"}})

    register_error_handlers(app)
    register_blueprints(app)

    @app.get("/")
    def index():
        return jsonify(
            {
                "service": "SiraTech Guide API",
                "scope": "Cultural tourism guide: locations, landmarks, and historical images only.",
                "docs": "/health for status; see README for full endpoint list.",
            }
        )

    return app


def register_blueprints(app):
    from app.routes.health import health_bp
    from app.routes.locations import locations_bp
    from app.routes.landmarks import landmarks_bp
    from app.routes.images import images_bp
    from app.routes.guide import guide_bp
    from app.routes.chat import chat_bp
    from app.routes.vision import vision_bp
    from app.routes.history import history_bp
    from app.routes.tts import tts_bp
    from app.routes.gamification import gamification_bp

    app.register_blueprint(health_bp)
    app.register_blueprint(locations_bp)
    app.register_blueprint(landmarks_bp)
    app.register_blueprint(images_bp)
    app.register_blueprint(guide_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(vision_bp)
    app.register_blueprint(history_bp)
    app.register_blueprint(tts_bp)
    app.register_blueprint(gamification_bp)
