from flask import Blueprint, jsonify, request

from app.services import chat_service
from app.utils.validation import (
    get_json_body,
    require_body_str,
    require_language,
    validate_conversation_context,
)

chat_bp = Blueprint("chat", __name__, url_prefix="/api/guide")


@chat_bp.post("/chat")
def chat():
    body = get_json_body(request)

    landmark_id = require_body_str(body, "landmark_id")
    user_message = require_body_str(body, "user_message", max_length=2000)
    language = require_language(body, "language")
    context = validate_conversation_context(body, "context")

    result = chat_service.get_chat_answer(
        landmark_id=landmark_id,
        user_message=user_message,
        language=language,
        conversation_context=context,
    )
    return jsonify(result)
