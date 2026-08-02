# app/models/signature.py
"""
Signature model - Email signature storage
"""

from datetime import datetime, timezone

from app import db


class Signature(db.Model):
    """
    Email signature model

    Each signature belongs to exactly one user (user_id foreign key)
    """

    __tablename__ = "signatures"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "users.id", ondelete="CASCADE"
        ),  # Delete signatures when user deleted
        nullable=False,
        index=True,  # Index for fast queries by user_id
    )

    # Signature metadata
    name = db.Column(db.String(100), nullable=False)

    is_active = db.Column(db.Boolean, default=True, nullable=False)

    locked = db.Column(db.Boolean, default=False, nullable=False)

    full_name = db.Column(db.String(100), nullable=False)
    job_title = db.Column(db.String(100), nullable=True)
    company = db.Column(db.String(100), nullable=True)
    department = db.Column(db.String(100), nullable=True)

    phone = db.Column(db.String(50), nullable=True)
    website = db.Column(db.String(255), nullable=True)

    linkedin_url = db.Column(db.String(255), nullable=True)
    twitter_url = db.Column(db.String(255), nullable=True)
    facebook_url = db.Column(db.String(255), nullable=True)
    instagram_url = db.Column(db.String(255), nullable=True)

    logo_url = db.Column(db.String(500), nullable=True)

    accent_color = db.Column(db.String(7), nullable=False, default="#0c2788")
    layout = db.Column(db.String(20), nullable=False, default="classic")
    font_family = db.Column(
        db.String(50), nullable=False, default="Arial, Helvetica, sans-serif"
    )

    # Generated HTML (the actual signature code)
    html_content = db.Column(
        db.Text, nullable=False
    )  # Final HTML with tracking injected

    # Unique tracking code for this signature (used in pixel/redirect URLs)
    tracking_code = db.Column(db.String(32), unique=True, nullable=False, index=True)

    # Analytics counters (updated by tracking endpoints)
    total_opens = db.Column(db.Integer, default=0, nullable=False)
    total_clicks = db.Column(db.Integer, default=0, nullable=False)
    last_opened_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user = db.relationship("User", back_populates="signatures")
    opens = db.relationship(
        "SignatureOpen", back_populates="signature", cascade="all, delete-orphan"
    )
    clicks = db.relationship(
        "SignatureClick", back_populates="signature", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        """String representation for debugging"""
        return f"<Signature {self.name} (User: {self.user_id})>"

    def increment_opens(self) -> None:
        """
        Increment open counter (called by tracking pixel endpoint)

        A09: Logging - This action should also be logged
        """
        self.total_opens += 1
        self.last_opened_at = datetime.now(timezone.utc)

    def increment_clicks(self) -> None:
        """
        Increment click counter (called by redirect endpoint)

        A09: Logging - This action should also be logged
        """
        self.total_clicks += 1
