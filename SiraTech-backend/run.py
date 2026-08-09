"""
Local dev entry point.

Loads environment variables from .env (never committed) before the app
config is read, then runs Flask's built-in dev server.

For hackathon/prototype use only — use gunicorn or similar in real prod.
"""

from dotenv import load_dotenv

load_dotenv()  # must happen before `from app import create_app`

from app import create_app  # noqa: E402

app = create_app()

if __name__ == "__main__":
    app.run(host=app.config["HOST"], port=app.config["PORT"], debug=app.config["DEBUG"])
