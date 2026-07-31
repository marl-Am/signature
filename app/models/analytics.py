# app/models/analytics.py

from datetime import datetime, timezone
from app import db


class SignatureOpen(db.Model):
    """One row per tracking pixel hit (one email open)."""

    __tablename__ = "signature_opens"

    id = db.Column(db.Integer, primary_key=True)
    signature_id = db.Column(
        db.Integer,
        db.ForeignKey("signatures.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    opened_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
    user_agent = db.Column(db.String(500), nullable=True)

    signature = db.relationship("Signature", back_populates="opens")


class SignatureClick(db.Model):
    """One row per tracked link click."""

    __tablename__ = "signature_clicks"

    id = db.Column(db.Integer, primary_key=True)
    signature_id = db.Column(
        db.Integer,
        db.ForeignKey("signatures.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    platform = db.Column(db.String(50), nullable=False)
    clicked_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
    user_agent = db.Column(db.String(500), nullable=True)

    signature = db.relationship("Signature", back_populates="clicks")
