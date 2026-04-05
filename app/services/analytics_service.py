# app/services/analytics_service.py
"""
Analytics service — queries open/click history for the current user.

Security:
- A01: All queries are scoped to current_user.id via a JOIN on signatures.
  A user can never retrieve data belonging to another user's signatures.
- A05: SQLAlchemy ORM only, no raw SQL.
"""

from datetime import datetime, timezone, timedelta
from typing import TypedDict

from sqlalchemy import func
from flask_login import current_user

from app import db
from app.models.signature import Signature
from app.models.analytics import SignatureOpen, SignatureClick


class SignatureStat(TypedDict):
    id: int
    name: str
    full_name: str
    total_opens: int
    total_clicks: int
    ctr: float
    last_opened_at: datetime | None
    created_at: datetime | None


class DailyPoint(TypedDict):
    date: str  # "YYYY-MM-DD"
    opens: int
    clicks: int


class AnalyticsSummary(TypedDict):
    total_opens: int
    total_clicks: int
    overall_ctr: float
    signature_count: int
    per_signature: list[SignatureStat]
    daily_last_30: list[DailyPoint]
    top_platform: str | None


class AnalyticsService:

    @staticmethod
    def get_summary() -> AnalyticsSummary:
        """
        Return all analytics data scoped to the current logged-in user.
        A01: Every query joins through signatures.user_id = current_user.id.
        """
        user_id: int = current_user.id

        # ── All signatures owned by this user ──────────────────────────────
        signatures: list[Signature] = (
            Signature.query.filter_by(user_id=user_id)
            .order_by(Signature.created_at.desc())
            .all()
        )
        sig_ids: list[int] = [s.id for s in signatures]

        if not sig_ids:
            return AnalyticsSummary(
                total_opens=0,
                total_clicks=0,
                overall_ctr=0.0,
                signature_count=0,
                per_signature=[],
                daily_last_30=[],
                top_platform=None,
            )

        # ── Totals ─────────────────────────────────────────────────────────
        total_opens: int = sum(s.total_opens for s in signatures)
        total_clicks: int = sum(s.total_clicks for s in signatures)
        overall_ctr: float = (
            round((total_clicks / total_opens) * 100, 1) if total_opens > 0 else 0.0
        )

        # ── Per-signature stats ────────────────────────────────────────────
        per_signature: list[SignatureStat] = []
        for sig in signatures:
            ctr = (
                round((sig.total_clicks / sig.total_opens) * 100, 1)
                if sig.total_opens > 0
                else 0.0
            )
            per_signature.append(
                SignatureStat(
                    id=sig.id,
                    name=sig.name,
                    full_name=sig.full_name,
                    total_opens=sig.total_opens,
                    total_clicks=sig.total_clicks,
                    ctr=ctr,
                    last_opened_at=sig.last_opened_at,
                    created_at=sig.created_at,
                )
            )

        # ── Daily breakdown — last 30 days ─────────────────────────────────
        cutoff: datetime = datetime.now(timezone.utc) - timedelta(days=29)

        opens_by_day: list[tuple[str, int]] = (
            db.session.query(
                func.strftime("%Y-%m-%d", SignatureOpen.opened_at).label("day"),
                func.count(SignatureOpen.id).label("cnt"),
            )
            .filter(
                SignatureOpen.signature_id.in_(sig_ids),
                SignatureOpen.opened_at >= cutoff,
            )
            .group_by("day")
            .all()
        )

        clicks_by_day: list[tuple[str, int]] = (
            db.session.query(
                func.strftime("%Y-%m-%d", SignatureClick.clicked_at).label("day"),
                func.count(SignatureClick.id).label("cnt"),
            )
            .filter(
                SignatureClick.signature_id.in_(sig_ids),
                SignatureClick.clicked_at >= cutoff,
            )
            .group_by("day")
            .all()
        )

        opens_map: dict[str, int] = {row.day: row.cnt for row in opens_by_day}
        clicks_map: dict[str, int] = {row.day: row.cnt for row in clicks_by_day}

        daily_last_30: list[DailyPoint] = []
        for i in range(30):
            day_dt = datetime.now(timezone.utc) - timedelta(days=29 - i)
            day_str = day_dt.strftime("%Y-%m-%d")
            daily_last_30.append(
                DailyPoint(
                    date=day_str,
                    opens=opens_map.get(day_str, 0),
                    clicks=clicks_map.get(day_str, 0),
                )
            )

        # ── Top clicked platform ───────────────────────────────────────────
        top_row = (
            db.session.query(
                SignatureClick.platform,
                func.count(SignatureClick.id).label("cnt"),
            )
            .filter(SignatureClick.signature_id.in_(sig_ids))
            .group_by(SignatureClick.platform)
            .order_by(func.count(SignatureClick.id).desc())
            .first()
        )
        top_platform: str | None = top_row.platform if top_row else None

        return AnalyticsSummary(
            total_opens=total_opens,
            total_clicks=total_clicks,
            overall_ctr=overall_ctr,
            signature_count=len(signatures),
            per_signature=per_signature,
            daily_last_30=daily_last_30,
            top_platform=top_platform,
        )
