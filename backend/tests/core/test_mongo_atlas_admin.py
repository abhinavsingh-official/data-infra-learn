"""Unit tests for the Atlas Administration API client, mocking the HTTP
calls and the propagation-wait connection check - exercised against a
real M0 cluster by hand during the deployment work (confirmed: create
succeeds, a freshly-created user takes a few real seconds before it's
usable, delete is idempotent against an already-gone user), but a live
third-party network dependency has no place in the regular test suite."""

from unittest.mock import MagicMock, patch

import pytest
import requests

from app.core import mongo_atlas_admin


@pytest.fixture(autouse=True)
def _settings(monkeypatch):
    monkeypatch.setenv("MONGO_ATLAS_PUBLIC_KEY", "pub")
    monkeypatch.setenv("MONGO_ATLAS_PRIVATE_KEY", "priv")
    monkeypatch.setenv("MONGO_ATLAS_PROJECT_ID", "proj123")
    monkeypatch.setenv("MONGO_ATLAS_HOST", "cluster0.example.mongodb.net")
    from app.core.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_create_scoped_db_user_posts_and_waits_for_usability():
    with patch("app.core.mongo_atlas_admin.requests.post") as mock_post, patch(
        "app.core.mongo_atlas_admin.MongoClient"
    ) as mock_client_cls:
        mock_post.return_value = MagicMock(status_code=201, raise_for_status=lambda: None)
        mock_client_cls.return_value = MagicMock()

        password = mongo_atlas_admin.create_scoped_db_user("session_abc")

        assert len(password) == 32
        _, kwargs = mock_post.call_args
        assert kwargs["json"]["username"] == "session_abc"
        assert kwargs["json"]["roles"] == [{"roleName": "readWrite", "databaseName": "session_abc"}]
        mock_client_cls.return_value.admin.command.assert_called_once_with("ping")


def test_create_scoped_db_user_retries_until_usable():
    from pymongo.errors import PyMongoError

    attempts = {"n": 0}

    def _flaky_ping(*_args, **_kwargs):
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise PyMongoError("not ready yet")
        return {"ok": 1}

    with patch("app.core.mongo_atlas_admin.requests.post") as mock_post, patch(
        "app.core.mongo_atlas_admin.MongoClient"
    ) as mock_client_cls, patch("app.core.mongo_atlas_admin.time.sleep"):
        mock_post.return_value = MagicMock(status_code=201, raise_for_status=lambda: None)
        mock_client_cls.return_value.admin.command.side_effect = _flaky_ping

        mongo_atlas_admin.create_scoped_db_user("session_retry")

        assert attempts["n"] == 3


def test_create_scoped_db_user_gives_up_after_timeout():
    from pymongo.errors import PyMongoError

    with patch("app.core.mongo_atlas_admin.requests.post") as mock_post, patch(
        "app.core.mongo_atlas_admin.MongoClient"
    ) as mock_client_cls, patch("app.core.mongo_atlas_admin.time.sleep"), patch(
        "app.core.mongo_atlas_admin.time.monotonic", side_effect=[0, 1, 31]
    ):
        mock_post.return_value = MagicMock(status_code=201, raise_for_status=lambda: None)
        mock_client_cls.return_value.admin.command.side_effect = PyMongoError("still not ready")

        with pytest.raises(TimeoutError):
            mongo_atlas_admin.create_scoped_db_user("session_slow")


def test_create_scoped_db_user_surfaces_http_errors():
    with patch("app.core.mongo_atlas_admin.requests.post") as mock_post:
        response = MagicMock(status_code=409)
        response.raise_for_status.side_effect = requests.HTTPError("409 conflict")
        mock_post.return_value = response

        with pytest.raises(requests.HTTPError):
            mongo_atlas_admin.create_scoped_db_user("session_dup")


def test_delete_scoped_db_user_treats_404_as_success():
    with patch("app.core.mongo_atlas_admin.requests.delete") as mock_delete:
        mock_delete.return_value = MagicMock(status_code=404)
        mongo_atlas_admin.delete_scoped_db_user("session_already_gone")  # must not raise


def test_delete_scoped_db_user_surfaces_other_errors():
    with patch("app.core.mongo_atlas_admin.requests.delete") as mock_delete:
        response = MagicMock(status_code=500)
        response.raise_for_status.side_effect = requests.HTTPError("500 server error")
        mock_delete.return_value = response

        with pytest.raises(requests.HTTPError):
            mongo_atlas_admin.delete_scoped_db_user("session_broken")
