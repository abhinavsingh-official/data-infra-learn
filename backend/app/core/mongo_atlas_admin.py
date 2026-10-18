"""Atlas's free M0 tier won't accept a direct `db.command("createUser")`
for its own users - this goes through Atlas's Admin API instead (HTTP
Digest, org-level API key).

A new Atlas user takes a few seconds to actually start authenticating
(~5s measured, up to a minute per Atlas's docs), so
`create_scoped_db_user` blocks on a real connection before returning."""

import secrets
import string
import time

import requests
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from requests.auth import HTTPDigestAuth

from app.core.config import get_settings

ATLAS_API_BASE = "https://cloud.mongodb.com/api/atlas/v2"
ATLAS_API_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/vnd.atlas.2023-11-15+json",
}
PROPAGATION_POLL_INTERVAL_SECONDS = 1.0
PROPAGATION_TIMEOUT_SECONDS = 30.0


def _generate_password() -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(32))


def _auth() -> HTTPDigestAuth:
    settings = get_settings()
    return HTTPDigestAuth(settings.mongo_atlas_public_key, settings.mongo_atlas_private_key)


def _scoped_connection_uri(username: str, password: str, db_name: str) -> str:
    settings = get_settings()
    return f"mongodb+srv://{username}:{password}@{settings.mongo_atlas_host}/{db_name}?authSource=admin"


def _wait_until_usable(username: str, password: str, db_name: str) -> None:
    uri = _scoped_connection_uri(username, password, db_name)
    deadline = time.monotonic() + PROPAGATION_TIMEOUT_SECONDS
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            client: MongoClient = MongoClient(uri, serverSelectionTimeoutMS=3000)
            try:
                client.admin.command("ping")
                return
            finally:
                client.close()
        except PyMongoError as e:  # noqa: BLE001 - any auth/connection failure just means "not yet", so retry
            last_error = e
            time.sleep(PROPAGATION_POLL_INTERVAL_SECONDS)
    raise TimeoutError(
        f"Atlas database user '{username}' didn't become usable within "
        f"{PROPAGATION_TIMEOUT_SECONDS}s (last error: {last_error})"
    )


def create_scoped_db_user(db_name: str) -> str:
    """Returns the generated password once the new user is usable."""
    settings = get_settings()
    password = _generate_password()
    response = requests.post(
        f"{ATLAS_API_BASE}/groups/{settings.mongo_atlas_project_id}/databaseUsers",
        auth=_auth(),
        headers=ATLAS_API_HEADERS,
        json={
            "databaseName": "admin",
            "username": db_name,
            "password": password,
            "roles": [{"roleName": "readWrite", "databaseName": db_name}],
        },
        timeout=15,
    )
    response.raise_for_status()
    _wait_until_usable(db_name, password, db_name)
    return password


def delete_scoped_db_user(db_name: str) -> None:
    """A 404 (already gone) counts as success."""
    settings = get_settings()
    response = requests.delete(
        f"{ATLAS_API_BASE}/groups/{settings.mongo_atlas_project_id}/databaseUsers/admin/{db_name}",
        auth=_auth(),
        headers=ATLAS_API_HEADERS,
        timeout=15,
    )
    if response.status_code != 404:
        response.raise_for_status()
