"""Shared per-database-scoped Mongo user provisioning, used by both
nosql_phase's session provisioning and progress.mongo_node_practice's
per-check ephemeral grading databases - previously two near-identical
copies of the same createUser/dropUser/drop_database logic, unified here
because the two backends (self-hosted vs. Atlas) now need different
branches of that logic, and duplicating that branch twice would be worse
than factoring it out once.

`admin_client` is still passed in by callers (rather than opened here)
because they already open it via `get_mongo_admin_client()` as a context
manager for other reasons (e.g. seeding collections on the same
connection) - this module only owns the user-provisioning half."""

import secrets
import string

from pymongo import MongoClient
from pymongo.errors import OperationFailure

from app.core.config import get_settings
from app.core.mongo_atlas_admin import create_scoped_db_user, delete_scoped_db_user

# Mongo's error code for "no such user" (from dropUser against a
# nonexistent user) - only relevant on the self-hosted backend's direct
# dropUser command.
_USER_NOT_FOUND = 11


def provision_scoped_mongo_user(admin_client: MongoClient, db_name: str) -> str:
    """Creates a Mongo user scoped to readWrite on `db_name` only.
    Returns the generated password."""
    settings = get_settings()
    if settings.mongo_provisioning_backend == "atlas_api":
        return create_scoped_db_user(db_name)
    password = _generate_self_hosted_password()
    admin_client[db_name].command(
        "createUser",
        db_name,
        pwd=password,
        roles=[{"role": "readWrite", "db": db_name}],
    )
    return password


def deprovision_scoped_mongo_user(admin_client: MongoClient, db_name: str) -> None:
    settings = get_settings()
    if settings.mongo_provisioning_backend == "atlas_api":
        delete_scoped_db_user(db_name)
    else:
        try:
            admin_client[db_name].command("dropUser", db_name)
        except OperationFailure as e:
            if e.code != _USER_NOT_FOUND:
                raise
    admin_client.drop_database(db_name)


def _generate_self_hosted_password() -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(32))
