"""
Centralized error handling.

Every error the API returns — expected (validation, not found) or
unexpected (500) — comes back in the same JSON shape:

{
  "error": {
    "code": "NOT_FOUND",
    "message": "Landmark 'lm-xyz' was not found.",
    "details": {}
  }
}
"""

from flask import jsonify


class APIError(Exception):
    """Base exception for all expected API errors."""

    status_code = 500
    code = "INTERNAL_ERROR"

    def __init__(self, message, status_code=None, code=None, details=None):
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        if code is not None:
            self.code = code
        self.details = details or {}

    def to_dict(self):
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details,
            }
        }


class NotFoundError(APIError):
    status_code = 404
    code = "NOT_FOUND"


class ValidationError(APIError):
    status_code = 400
    code = "VALIDATION_ERROR"


class ServiceUnavailableError(APIError):
    """Raised when an upstream dependency (e.g. Gemini) can't fulfill the request."""

    status_code = 503
    code = "AI_SERVICE_UNAVAILABLE"


def register_error_handlers(app):
    @app.errorhandler(APIError)
    def handle_api_error(err: APIError):
        response = jsonify(err.to_dict())
        response.status_code = err.status_code
        return response

    @app.errorhandler(404)
    def handle_404(err):
        response = jsonify(
            {
                "error": {
                    "code": "NOT_FOUND",
                    "message": "The requested resource was not found.",
                    "details": {},
                }
            }
        )
        response.status_code = 404
        return response

    @app.errorhandler(405)
    def handle_405(err):
        response = jsonify(
            {
                "error": {
                    "code": "METHOD_NOT_ALLOWED",
                    "message": "This HTTP method is not allowed for this endpoint.",
                    "details": {},
                }
            }
        )
        response.status_code = 405
        return response

    @app.errorhandler(Exception)
    def handle_unexpected_error(err):
        # Fallback for anything not already an APIError. Keeps the API
        # from ever leaking a raw stack trace / HTML error page.
        app.logger.exception("Unhandled exception")
        response = jsonify(
            {
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred.",
                    "details": {},
                }
            }
        )
        response.status_code = 500
        return response
