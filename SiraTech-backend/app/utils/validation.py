"""Small, dependency-free validation helpers for query parameters."""

import os

from flask import current_app

from app.errors import ValidationError


def get_int_arg(args, name, default=None, minimum=None, maximum=None):
    """Parse and validate an integer query param, raising ValidationError on bad input."""
    raw = args.get(name, None)
    if raw is None or raw == "":
        return default

    try:
        value = int(raw)
    except (TypeError, ValueError):
        raise ValidationError(
            f"Query parameter '{name}' must be an integer.",
            details={"param": name, "received": raw},
        )

    if minimum is not None and value < minimum:
        raise ValidationError(
            f"Query parameter '{name}' must be >= {minimum}.",
            details={"param": name, "received": value},
        )
    if maximum is not None and value > maximum:
        raise ValidationError(
            f"Query parameter '{name}' must be <= {maximum}.",
            details={"param": name, "received": value},
        )
    return value


def get_float_arg(args, name, default=None, minimum=None, maximum=None):
    """Parse and validate a float query/form param, raising ValidationError on bad input."""
    raw = args.get(name, None)
    if raw is None or raw == "":
        return default

    try:
        value = float(raw)
    except (TypeError, ValueError):
        raise ValidationError(
            f"'{name}' must be a number.",
            details={"param": name, "received": raw},
        )

    if minimum is not None and value < minimum:
        raise ValidationError(
            f"'{name}' must be >= {minimum}.",
            details={"param": name, "received": value},
        )
    if maximum is not None and value > maximum:
        raise ValidationError(
            f"'{name}' must be <= {maximum}.",
            details={"param": name, "received": value},
        )
    return value


def get_str_arg(args, name, default=None, choices=None, strip=True):
    """Parse and validate a string query param, optionally restricted to `choices`."""
    raw = args.get(name, default)
    if raw is None:
        return default

    value = raw.strip() if strip else raw
    if value == "":
        return default

    if choices is not None and value not in choices:
        raise ValidationError(
            f"Query parameter '{name}' must be one of: {', '.join(choices)}.",
            details={"param": name, "received": value, "allowed": list(choices)},
        )
    return value


def require_non_empty_str(value, field_name):
    """Validate a required string field (e.g. a search query)."""
    if value is None or not str(value).strip():
        raise ValidationError(
            f"'{field_name}' is required and cannot be empty.",
            details={"param": field_name},
        )
    return str(value).strip()


SUPPORTED_LANGUAGES = ("ar", "en")


def get_json_body(request):
    """Parse and validate the request body as a JSON object."""
    body = request.get_json(silent=True)
    if body is None or not isinstance(body, dict):
        raise ValidationError(
            "Request body must be valid JSON with Content-Type: application/json.",
            details={},
        )
    return body


def require_body_str(body, field_name, max_length=None):
    """Validate a required non-empty string field on a parsed JSON body."""
    value = body.get(field_name)
    if value is None or not isinstance(value, str) or not value.strip():
        raise ValidationError(
            f"'{field_name}' is required and must be a non-empty string.",
            details={"param": field_name},
        )
    value = value.strip()
    if max_length is not None and len(value) > max_length:
        raise ValidationError(
            f"'{field_name}' must be at most {max_length} characters.",
            details={"param": field_name, "max_length": max_length},
        )
    return value


def get_body_str(body, field_name, default=None, max_length=None):
    """Validate an optional string field on a parsed JSON body (None/absent is fine)."""
    value = body.get(field_name, default)
    if value is None:
        return default
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(
            f"'{field_name}' must be a non-empty string when provided.",
            details={"param": field_name},
        )
    value = value.strip()
    if max_length is not None and len(value) > max_length:
        raise ValidationError(
            f"'{field_name}' must be at most {max_length} characters.",
            details={"param": field_name, "max_length": max_length},
        )
    return value


def require_language(body, field_name="language"):
    """Validate the 'language' field is one of the supported codes."""
    value = body.get(field_name)
    if value is None or value not in SUPPORTED_LANGUAGES:
        raise ValidationError(
            f"'{field_name}' is required and must be one of: {', '.join(SUPPORTED_LANGUAGES)}.",
            details={"param": field_name, "received": value, "allowed": list(SUPPORTED_LANGUAGES)},
        )
    return value


def validate_conversation_context(body, field_name="context", max_turns=8):
    """
    Validate the optional conversation-context list.

    Expected shape (optional; omit or pass [] for no prior context):
        [{"role": "user" | "assistant", "content": "..."}, ...]
    """
    value = body.get(field_name)
    if value is None:
        return []

    if not isinstance(value, list):
        raise ValidationError(
            f"'{field_name}' must be a list of {{role, content}} turns.",
            details={"param": field_name},
        )

    if len(value) > max_turns:
        raise ValidationError(
            f"'{field_name}' supports at most {max_turns} prior turns.",
            details={"param": field_name, "received_count": len(value), "max_turns": max_turns},
        )

    cleaned = []
    for i, turn in enumerate(value):
        if (
            not isinstance(turn, dict)
            or turn.get("role") not in ("user", "assistant")
            or not isinstance(turn.get("content"), str)
            or not turn.get("content").strip()
        ):
            raise ValidationError(
                f"'{field_name}[{i}]' must look like "
                '{"role": "user"|"assistant", "content": "..."}.',
                details={"param": field_name, "index": i},
            )
        cleaned.append({"role": turn["role"], "content": turn["content"].strip()})
    return cleaned


# Fallbacks used only if the app config keys below aren't set (they always
# are, via app/config.py) — kept here so this module has no hard dependency
# on that config existing, e.g. in isolated unit tests.
_DEFAULT_ALLOWED_IMAGE_TYPES = ("image/jpeg", "image/png", "image/webp")
_DEFAULT_MAX_IMAGE_BYTES = 8 * 1024 * 1024  # 8 MB


def require_image_file(request, field_name="image"):
    """
    Validate a required image upload on a multipart/form-data request:
    present, non-empty, an allowed content type, and within the configured
    size limit. Raises ValidationError (→ 400) on any failure; never lets
    an oversized or wrong-type file reach the vision service.
    """
    file = request.files.get(field_name)
    if file is None or file.filename == "":
        raise ValidationError(
            f"'{field_name}' is required and must be an uploaded image file "
            "(multipart/form-data).",
            details={"param": field_name},
        )

    allowed_types = current_app.config.get("VISION_ALLOWED_MIME_TYPES", _DEFAULT_ALLOWED_IMAGE_TYPES)
    content_type = (file.mimetype or "").lower()
    if content_type not in allowed_types:
        raise ValidationError(
            f"'{field_name}' must be one of: {', '.join(allowed_types)}.",
            details={"param": field_name, "received": content_type, "allowed": list(allowed_types)},
        )

    max_bytes = current_app.config.get("VISION_MAX_IMAGE_BYTES", _DEFAULT_MAX_IMAGE_BYTES)
    file.stream.seek(0, os.SEEK_END)
    size = file.stream.tell()
    file.stream.seek(0)

    if size == 0:
        raise ValidationError(
            f"'{field_name}' is empty.",
            details={"param": field_name},
        )
    if size > max_bytes:
        raise ValidationError(
            f"'{field_name}' exceeds the maximum allowed size of {max_bytes // (1024 * 1024)}MB.",
            details={"param": field_name, "received_bytes": size, "max_bytes": max_bytes},
        )

    return file
