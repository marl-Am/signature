# app/routes/analytics.py
from flask import Blueprint, render_template
from flask_login import login_required

from app.services.analytics_service import (
    AnalyticsService,
    AnalyticsSummary,
    SignatureDetail,
)

analytics_bp = Blueprint("analytics", __name__, url_prefix="/analytics")


@analytics_bp.route("/")
@login_required
def index():
    summary: AnalyticsSummary = AnalyticsService.get_summary()
    return render_template("analytics/index.html", summary=summary)


@analytics_bp.route("/signature/<int:signature_id>")
@login_required
def detail(signature_id: int):
    detail: SignatureDetail = AnalyticsService.get_signature_detail(signature_id)
    return render_template("analytics/detail.html", detail=detail)
