# tests/test_signatures.py
"""
Tests for app/routes/signatures.py: create, edit, delete, preview, and
ownership enforcement (A01 - Broken Access Control).
"""

from flask import Flask
from flask.testing import FlaskClient

from app import db
from app.models.signature import Signature
from tests.conftest import register_via_client

def _create_signature(
    client: FlaskClient,
    name: str = "Work Signature",
    full_name: str = "Jane Doe",
    website: str = "",
    **extra: str,
):
    data = {"name": name, "full_name": full_name, "website": website, **extra}
    return client.post("/signatures/create", data=data, follow_redirects=False)


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


def test_create_requires_login(client: FlaskClient) -> None:
    response = _create_signature(client)
    assert response.status_code == 302
    assert "login" in response.headers["Location"].lower()


def test_create_succeeds_for_logged_in_user(app: Flask, client: FlaskClient) -> None:
    register_via_client(client, email="sig1@example.com")

    response = _create_signature(client, name="My Sig", full_name="Jane Doe")

    assert response.status_code == 302
    assert "dashboard" in response.headers["Location"].lower()

    with app.app_context():
        signature = Signature.query.filter_by(name="My Sig").first()
        assert signature is not None
        assert signature.full_name == "Jane Doe"
        assert signature.tracking_code is not None


def test_create_requires_name_and_full_name(client: FlaskClient) -> None:
    register_via_client(client, email="sig2@example.com")

    response = _create_signature(client, name="", full_name="")

    assert response.status_code == 200
    assert b"required" in response.data


def test_create_normalizes_bare_domain_to_https(
    app: Flask, client: FlaskClient
) -> None:
    register_via_client(client, email="sig3@example.com")

    _create_signature(
        client, name="URL Test", full_name="Jane Doe", website="google.com"
    )

    with app.app_context():
        signature = Signature.query.filter_by(name="URL Test").first()
        assert signature is not None
        assert signature.website == "https://google.com"


def test_free_tier_blocks_second_signature(app: Flask, client: FlaskClient) -> None:
    register_via_client(client, email="freetier@example.com")

    first = _create_signature(client, name="First", full_name="Jane Doe")
    assert first.status_code == 302

    response = client.get("/signatures/create", follow_redirects=False)

    assert response.status_code == 302
    assert "pricing" in response.headers["Location"].lower()


def test_deleting_signature_frees_free_tier_slot(
    app: Flask, client: FlaskClient
) -> None:
    register_via_client(client, email="freeslot@example.com")
    _create_signature(client, name="First", full_name="Jane Doe")

    with app.app_context():
        signature = Signature.query.filter_by(name="First").first()
        assert signature is not None
        signature_id = signature.id

    client.post(f"/signatures/{signature_id}/delete", follow_redirects=False)

    # Should now be allowed to create again
    response = client.get("/signatures/create")
    assert response.status_code == 200  # form renders, no redirect to pricing


# ---------------------------------------------------------------------------
# Ownership (A01)
# ---------------------------------------------------------------------------


def _create_signature_for_user(
    app: Flask, client: FlaskClient, email: str, sig_name: str = "Owned Sig"
) -> int:
    register_via_client(client, email=email)
    _create_signature(client, name=sig_name, full_name="Owner Name")
    with app.app_context():
        signature = Signature.query.filter_by(name=sig_name).first()
        assert signature is not None
        return signature.id


def test_user_cannot_edit_another_users_signature(
    app: Flask, client: FlaskClient
) -> None:
    owner_client = client
    signature_id = _create_signature_for_user(app, owner_client, "owner@example.com")
    owner_client.get("/auth/logout")

    register_via_client(owner_client, email="intruder@example.com")

    response = owner_client.get(f"/signatures/{signature_id}/edit")

    assert response.status_code == 404


def test_user_cannot_preview_another_users_signature(
    app: Flask, client: FlaskClient
) -> None:
    signature_id = _create_signature_for_user(app, client, "owner2@example.com")
    client.get("/auth/logout")
    register_via_client(client, email="intruder2@example.com")

    response = client.get(f"/signatures/{signature_id}/preview")

    assert response.status_code == 404


def test_user_cannot_delete_another_users_signature(
    app: Flask, client: FlaskClient
) -> None:
    signature_id = _create_signature_for_user(app, client, "owner3@example.com")
    client.get("/auth/logout")
    register_via_client(client, email="intruder3@example.com")

    response = client.post(f"/signatures/{signature_id}/delete")

    assert response.status_code == 404

    with app.app_context():
        # Signature must still exist — the delete must not have gone through
        assert db.session.get(Signature, signature_id) is not None


# ---------------------------------------------------------------------------
# Edit
# ---------------------------------------------------------------------------


def test_owner_can_edit_own_signature(app: Flask, client: FlaskClient) -> None:
    signature_id = _create_signature_for_user(app, client, "editor@example.com")

    response = client.post(
        f"/signatures/{signature_id}/edit",
        data={
            "name": "Renamed Signature",
            "full_name": "Jane Updated",
            "website": "",
        },
        follow_redirects=False,
    )

    assert response.status_code == 302
    with app.app_context():
        signature = db.session.get(Signature, signature_id)
        assert signature is not None
        assert signature.name == "Renamed Signature"
        assert signature.full_name == "Jane Updated"


def test_edit_requires_name_and_full_name(app: Flask, client: FlaskClient) -> None:
    signature_id = _create_signature_for_user(app, client, "editor2@example.com")

    response = client.post(
        f"/signatures/{signature_id}/edit",
        data={"name": "", "full_name": "", "website": ""},
    )

    assert response.status_code == 200
    assert b"required" in response.data
