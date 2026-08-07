# app/routes/tracking.py
"""
Tracking endpoints — open pixel and click redirect.

These routes are intentionally public (no @login_required).
They are called by email clients and recipients, not by the logged-in user.

Security notes:
- A10 (SSRF): Redirects only go to URLs stored in our own database.
  No user-supplied URL is ever followed at request time.
- A01: tracking_code is a random secret token; no user ID is exposed in URLs.
- A09: All increments are logged at DEBUG level for future monitoring.
- Silent fail on unknown codes: do not reveal whether a code is valid.
"""

import logging
from datetime import datetime, timezone
from typing import Union

from flask import Blueprint, make_response, redirect, request, url_for
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.wrappers import Response

from app import db
from app.models.signature import Signature
from app.models.analytics import SignatureOpen, SignatureClick

from app.services.ip_range_service import is_office365_ip

logger = logging.getLogger(__name__)

tracking_bp = Blueprint("tracking", __name__, url_prefix="/track")

# Minimal 1×1 transparent GIF (43 bytes — no external dependency needed)
_TRANSPARENT_GIF: bytes = (
    b"\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00"
    b"\xff\xff\xff\x00\x00\x00\x21\xf9\x04\x00\x00\x00\x00"
    b"\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02"
    b"\x44\x01\x00\x3b"
)

# Maps the <platform> path segment to the corresponding Signature column name.
# Only platforms that exist on the model are accepted (positive allow-list — A10).
_PLATFORM_FIELD: dict[str, str] = {
    "linkedin": "linkedin_url",
    "twitter": "twitter_url",
    "facebook": "facebook_url",
    "instagram": "instagram_url",
    "website": "website",
}

# User-agent substrings that identify known email privacy proxies and security
# scanners. Requests from these are silently ignored — the GIF/redirect still
# fires so the client never sees an error, but no analytics row is written.
_PROXY_SIGNATURES: tuple[str, ...] = (
    "GoogleImageProxy",
    "Apple Mail Privacy Protection",
    "Applebot",
    "Proofpoint",
    "Barracuda",
    "Nexus 5 Build/MRA58N",  # Gmail image caching proxy
)


def _is_scanner_request(user_agent: str) -> bool:
    """
    True if this request looks like a security-scanner pre-visit rather
    than a real recipient — either a known proxy/scanner User-Agent, or a
    source IP inside Microsoft's published Office 365 Safe Links ranges.
    """
    if any(proxy in user_agent for proxy in _PROXY_SIGNATURES):
        return True
    return is_office365_ip(request.remote_addr or "")


@tracking_bp.route("/pixel/<string:tracking_code>.gif")
def pixel(tracking_code: str) -> Response:
    """
    Serve a 1×1 transparent GIF and increment the open counter.

    Always returns the GIF regardless of whether the code is valid —
    this prevents email clients from showing broken-image icons and
    avoids leaking whether a tracking code exists.

    No authentication required: called by the recipient's email client.
    """
    signature: Signature | None = Signature.query.filter_by(
        tracking_code=tracking_code
    ).first()

    if signature is not None:
        ua: str = request.headers.get("User-Agent", "")
        logger.warning(
            "PIXEL HIT DEBUG — signature_id=%s ua=%r referer=%r remote_addr=%s",
            signature.id,
            ua,
            request.headers.get("Referer", ""),
            request.remote_addr,
        )
        if not _is_scanner_request(ua):
            try:
                signature.increment_opens()
                db.session.add(
                    SignatureOpen(
                        signature_id=signature.id,
                        opened_at=datetime.now(timezone.utc),
                        user_agent=ua,
                    )
                )
                db.session.commit()
                logger.debug(
                    "Open recorded — signature_id=%s total_opens=%s",
                    signature.id,
                    signature.total_opens,
                )
            except SQLAlchemyError:
                db.session.rollback()
                logger.exception(
                    "Failed to record open for tracking_code=%s", tracking_code
                )

    response = make_response(_TRANSPARENT_GIF)
    response.headers["Content-Type"] = "image/gif"
    # Tell every cache layer never to cache this image.
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    return response


@tracking_bp.route("/click/<string:tracking_code>/<string:platform>")
def click(tracking_code: str, platform: str) -> Union[Response, tuple[str, int]]:
    """
    Increment the click counter and redirect to the real destination URL.

    A10 (SSRF): The destination is always read from our database — never
    from the request itself.  The <platform> segment is validated against
    a fixed allow-list before any DB lookup is performed.

    No authentication required: called by the recipient clicking a link.
    """
    # Validate platform against the allow-list before touching the DB.
    if platform not in _PLATFORM_FIELD:
        logger.warning(
            "Click ignored — unknown platform=%s tracking_code=%s",
            platform,
            tracking_code,
        )
        return redirect(url_for("index"))

    signature: Signature | None = Signature.query.filter_by(
        tracking_code=tracking_code
    ).first()

    if signature is None:
        logger.warning(
            "Click ignored — unknown tracking_code=%s platform=%s",
            tracking_code,
            platform,
        )
        return redirect(url_for("index"))

    # Resolve the destination URL from the model (never from the request).
    destination: str | None = getattr(signature, _PLATFORM_FIELD[platform], None)

    if not destination:
        # The platform field exists but the user left it blank — just go home.
        logger.debug(
            "Click ignored — no URL set for platform=%s signature_id=%s",
            platform,
            signature.id,
        )
        return redirect(url_for("index"))

    try:
        ua: str = request.headers.get("User-Agent", "")
        if not _is_scanner_request(ua):
            signature.increment_clicks()
            db.session.add(
                SignatureClick(
                    signature_id=signature.id,
                    platform=platform,
                    clicked_at=datetime.now(timezone.utc),
                    user_agent=ua,
                )
            )
            db.session.commit()
            logger.debug(
                "Click recorded — signature_id=%s platform=%s total_clicks=%s",
                signature.id,
                platform,
                signature.total_clicks,
            )
    except SQLAlchemyError:
        db.session.rollback()
        logger.exception(
            "Failed to record click for tracking_code=%s platform=%s",
            tracking_code,
            platform,
        )
        # Still redirect the user even if the counter update failed.

    return redirect(destination)
