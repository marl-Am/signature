# app/routes/analytics.py
from flask import Blueprint, render_template
from flask_login import login_required

from app.services.analytics_service import AnalyticsService, AnalyticsSummary

analytics_bp = Blueprint("analytics", __name__, url_prefix="/analytics")


@analytics_bp.route("/")
@login_required
def index():
    summary: AnalyticsSummary = AnalyticsService.get_summary()
    return render_template("analytics/index.html", summary=summary)
