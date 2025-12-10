# app/models/signature.py
"""
Signature model - Email signature storage

Security Features Implemented:
- A01: Broken Access Control - Every signature belongs to a user
- A05: Injection - SQLAlchemy ORM prevents SQL injection
- A08: Data Integrity - Validate HTML content before storage
"""

from app import db
from datetime import datetime
from typing import Optional


class Signature(db.Model):
    """
    Email signature model

    Each signature belongs to exactly one user (user_id foreign key)
    This enforces A01: Access Control - users can only access their own signatures
    """

    __tablename__ = "signatures"

    # ========================================
    # PRIMARY FIELDS
    # ========================================
    id = db.Column(db.Integer, primary_key=True)

    # A01: CRITICAL - Every signature must belong to a user
    user_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "users.id", ondelete="CASCADE"
        ),  # Delete signatures when user deleted
        nullable=False,
        index=True,  # Index for fast queries by user_id
    )

    # Signature metadata
    name = db.Column(
        db.String(100), nullable=False
    )  # User-friendly name like "Work Signature"
    is_active = db.Column(
        db.Boolean, default=True, nullable=False
    )  # Can be disabled without deletion

    # ========================================
    # SIGNATURE CONTENT
    # ========================================
    # Personal information
    full_name = db.Column(db.String(100), nullable=False)
    job_title = db.Column(db.String(100), nullable=True)
    company = db.Column(db.String(100), nullable=True)
    department = db.Column(db.String(100), nullable=True)

    # Contact information
    phone = db.Column(db.String(50), nullable=True)
    website = db.Column(db.String(255), nullable=True)

    # Social media links
    linkedin_url = db.Column(db.String(255), nullable=True)
    twitter_url = db.Column(db.String(255), nullable=True)
    facebook_url = db.Column(db.String(255), nullable=True)
    instagram_url = db.Column(db.String(255), nullable=True)

    # Logo/Image
    logo_url = db.Column(db.String(500), nullable=True)  # S3 URL to uploaded logo

    # Generated HTML (the actual signature code)
    html_content = db.Column(
        db.Text, nullable=False
    )  # Final HTML with tracking injected

    # ========================================
    # TRACKING & ANALYTICS (The Business Model)
    # ========================================
    # Unique tracking code for this signature (used in pixel/redirect URLs)
    tracking_code = db.Column(db.String(32), unique=True, nullable=False, index=True)

    # Analytics counters (updated by tracking endpoints)
    total_opens = db.Column(db.Integer, default=0, nullable=False)
    total_clicks = db.Column(db.Integer, default=0, nullable=False)
    last_opened_at = db.Column(db.DateTime, nullable=True)

    # ========================================
    # TIMESTAMPS
    # ========================================
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # ========================================
    # RELATIONSHIPS
    # ========================================
    # Back reference to User (A01: Access Control)
    user = db.relationship("User", back_populates="signatures")

    # TODO: Add when analytics model is created
    # analytics = db.relationship('Analytics', back_populates='signature', lazy='dynamic')

    # ========================================
    # UTILITY METHODS
    # ========================================

    def __repr__(self) -> str:
        """String representation for debugging"""
        return f"<Signature {self.name} (User: {self.user_id})>"

    def to_dict(self) -> dict:
        """
        Convert signature to dictionary (for API responses)

        Returns:
            Dictionary of signature data
        """
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "is_active": self.is_active,
            "full_name": self.full_name,
            "job_title": self.job_title,
            "company": self.company,
            "phone": self.phone,
            "website": self.website,
            "logo_url": self.logo_url,
            "total_opens": self.total_opens,
            "total_clicks": self.total_clicks,
            "last_opened_at": (
                self.last_opened_at.isoformat() if self.last_opened_at else None
            ),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def get_tracking_pixel_url(self) -> str:
        """
        Generate tracking pixel URL for this signature

        Returns:
            Full URL to tracking pixel endpoint
        """
        # TODO: Replace with actual domain in production
        base_url = "https://yourdomain.com"
        return f"{base_url}/track/pixel/{self.tracking_code}.png"

    def get_redirect_url(self, social_platform: str) -> str:
        """
        Generate click tracking redirect URL for social media links

        Args:
            social_platform: Platform name (linkedin, twitter, etc.)

        Returns:
            Full URL to redirect endpoint
        """
        # TODO: Replace with actual domain in production
        base_url = "https://yourdomain.com"
        return f"{base_url}/track/click/{self.tracking_code}/{social_platform}"

    def increment_opens(self) -> None:
        """
        Increment open counter (called by tracking pixel endpoint)

        A09: Logging - This action should also be logged
        """
        self.total_opens += 1
        self.last_opened_at = datetime.utcnow()
        db.session.commit()

    def increment_clicks(self) -> None:
        """
        Increment click counter (called by redirect endpoint)

        A09: Logging - This action should also be logged
        """
        self.total_clicks += 1
        db.session.commit()


# ========================================
# DATABASE INDEXES (Already defined above)
# ========================================
# - user_id (indexed for fast "get all user signatures" queries)
# - tracking_code (unique + indexed for fast tracking lookups)
