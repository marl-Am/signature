# app/routes/dashboard.py
"""
Dashboard blueprint.
All routes require an authenticated session.
"""

from flask import Blueprint, render_template
from flask_login import login_required
from werkzeug.wrappers import Response
from typing import Union

from app.services.signature_service import SignatureService

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")


@dashboard_bp.route("/")
@login_required
def index() -> Union[str, Response]:
    """Main dashboard — signatures list and quick stats."""
    signatures = SignatureService.get_user_signatures()
    total_opens: int = sum(s.total_opens for s in signatures)
    total_clicks: int = sum(s.total_clicks for s in signatures)

    return render_template(
        "dashboard/index.html",
        signatures=signatures,
        total_opens=total_opens,
        total_clicks=total_clicks,
    )
