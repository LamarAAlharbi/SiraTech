import pytest

from app import create_app
from app.config import Config
from app.services import data_loader


class TestConfig(Config):
    TESTING = True
    DEBUG = False


@pytest.fixture()
def app(tmp_path):
    # Each test gets its own throwaway SQLite file for gamification data,
    # so discovery/badge state never leaks between tests or into the dev DB.
    class IsolatedTestConfig(TestConfig):
        GAMIFICATION_DB_PATH = str(tmp_path / "gamification-test.sqlite3")

    application = create_app(IsolatedTestConfig)
    with application.app_context():
        data_loader.clear_cache()
    yield application


@pytest.fixture()
def client(app):
    return app.test_client()
