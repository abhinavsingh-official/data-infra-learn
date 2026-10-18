"""MongoDB Atlas Administration API client for the two operations the
self-hosted provisioning path covers with a direct `db.command("createUser"
/"dropUser", ...)` call - Atlas's free M0 tier doesn't accept that
database command for its own cluster-level database users, so creating/
deleting one has to go through this HTTP API instead, authenticated with
an org-level API key pair (HTTP Digest, not the data-plane credentials).

Measured against a real M0 cluster: a newly created Atlas database user
takes a few seconds (seen ~5s, Atlas's own docs say up to ~1 minute
worst-case) to actually propagate to the cluster and start authenticating
- `create_scoped_db_user` blocks until a real connection with the new
credentials succeeds (or the retry budget runs out), so callers never see
a freshly-"created" user that isn't actually usable yet."""

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
        except PyMongoError as e:  # noqa: BLE001 - genuinely any auth/connection failure means "not yet", retry
            last_error = e
            time.sleep(PROPAGATION_POLL_INTERVAL_SECONDS)
    raise TimeoutError(
        f"Atlas database user '{username}' didn't become usable within "
        f"{PROPAGATION_TIMEOUT_SECONDS}s (last error: {last_error})"
    )


def create_scoped_db_user(db_name: str) -> str:
    """Creates an Atlas database user named `db_name` with readWrite on
    that one database, blocking until it's actually usable. Returns the
    generated password."""
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
    """Deletes the Atlas database user named `db_name` - a 404 (already
    gone) is treated as success, same resilience contract as the
    self-hosted path's `dropUser`-ignoring-"no such user" behavior."""
    settings = get_settings()
    response = requests.delete(
        f"{ATLAS_API_BASE}/groups/{settings.mongo_atlas_project_id}/databaseUsers/admin/{db_name}",
        auth=_auth(),
        headers=ATLAS_API_HEADERS,
        timeout=15,
    )
    if response.status_code != 404:
        response.raise_for_status()
