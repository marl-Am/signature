# app/services/signature_service.py
"""
Signature service - Business logic for signature operations

Security: A01 - All queries filtered by user_id to prevent unauthorized access
"""

from app import db
from app.models.signature import Signature
from flask_login import current_user
from typing import List, Optional
import secrets
from datetime import datetime


class SignatureService:
    """
    Service layer for signature operations

    All methods enforce A01: Access Control by filtering queries with user_id
    """

    @staticmethod
    def get_user_signatures() -> List[Signature]:
        """
        Get ALL signatures for current user ONLY

        Security: A01 - Always filter by user_id

        Returns:
            List of user's signatures
        """
        return Signature.query.filter_by(user_id=current_user.id).all()

    @staticmethod
    def get_signature_by_id(signature_id: int) -> Signature:
        """
        Get ONE signature - verify ownership

        Security: A01 - User can only access their own signatures

        Args:
            signature_id: ID of signature to retrieve

        Returns:
            Signature object if found and owned by user

        Raises:
            404 error if signature not found or not owned by user
        """
        signature = Signature.query.filter_by(
            id=signature_id, user_id=current_user.id
        ).first_or_404()

        return signature

    @staticmethod
    def create_signature(
        name: str,
        full_name: str,
        job_title: Optional[str] = None,
        company: Optional[str] = None,
        department: Optional[str] = None,
        phone: Optional[str] = None,
        website: Optional[str] = None,
        linkedin_url: Optional[str] = None,
        twitter_url: Optional[str] = None,
        facebook_url: Optional[str] = None,
        instagram_url: Optional[str] = None,
        logo_url: Optional[str] = None,
    ) -> Signature:
        """
        Create a new signature for current user

        Security: A01 - Automatically sets user_id to current_user

        Args:
            name: User-friendly name for signature
            full_name: Full name to display
            job_title: Job title (optional)
            company: Company name (optional)
            department: Department (optional)
            phone: Phone number (optional)
            website: Website URL (optional)
            linkedin_url: LinkedIn profile URL (optional)
            twitter_url: Twitter profile URL (optional)
            facebook_url: Facebook profile URL (optional)
            instagram_url: Instagram profile URL (optional)
            logo_url: Logo image URL (optional)

        Returns:
            Newly created Signature object
        """
        # Generate unique tracking code
        tracking_code = secrets.token_urlsafe(16)

        # TODO: Generate actual HTML content with tracking injected
        # For now, placeholder HTML
        html_content = f"<p>Signature for {full_name}</p>"

        signature = Signature(
            user_id=current_user.id,  # A01: Always set user_id
            name=name,
            full_name=full_name,
            job_title=job_title,
            company=company,
            department=department,
            phone=phone,
            website=website,
            linkedin_url=linkedin_url,
            twitter_url=twitter_url,
            facebook_url=facebook_url,
            instagram_url=instagram_url,
            logo_url=logo_url,
            tracking_code=tracking_code,
            html_content=html_content,
            is_active=True,
        )

        db.session.add(signature)
        db.session.commit()

        return signature

    @staticmethod
    def update_signature(signature_id: int, **kwargs) -> Signature:
        """
        Update an existing signature

        Security: A01 - Ownership verified before update

        Args:
            signature_id: ID of signature to update
            **kwargs: Fields to update

        Returns:
            Updated Signature object

        Raises:
            404 error if signature not found or not owned by user
        """
        # Get signature with ownership check
        signature = SignatureService.get_signature_by_id(signature_id)

        # Update allowed fields
        allowed_fields = [
            "name",
            "full_name",
            "job_title",
            "company",
            "department",
            "phone",
            "website",
            "linkedin_url",
            "twitter_url",
            "facebook_url",
            "instagram_url",
            "logo_url",
            "is_active",
        ]

        for field, value in kwargs.items():
            if field in allowed_fields:
                setattr(signature, field, value)

        signature.updated_at = datetime.utcnow()

        # TODO: Regenerate HTML content with new data

        db.session.commit()

        return signature

    @staticmethod
    def delete_signature(signature_id: int) -> bool:
        """
        Delete signature - with ownership check

        Security: A01 - Can only delete own signatures

        Args:
            signature_id: ID of signature to delete

        Returns:
            True if deletion successful

        Raises:
            404 error if signature not found or not owned by user
        """
        # Get signature with ownership check
        signature = SignatureService.get_signature_by_id(signature_id)

        db.session.delete(signature)
        db.session.commit()

        return True

    @staticmethod
    def toggle_signature_status(signature_id: int) -> Signature:
        """
        Toggle signature active/inactive status

        Security: A01 - Ownership verified before toggle

        Args:
            signature_id: ID of signature to toggle

        Returns:
            Updated Signature object
        """
        signature = SignatureService.get_signature_by_id(signature_id)
        signature.is_active = not signature.is_active
        db.session.commit()

        return signature

    @staticmethod
    def get_active_signature() -> Optional[Signature]:
        """
        Get user's currently active signature

        Returns:
            Active Signature object or None if no active signature
        """
        return Signature.query.filter_by(
            user_id=current_user.id, is_active=True
        ).first()

    @staticmethod
    def can_create_signature() -> bool:
        """
        Check if user can create a new signature based on subscription

        Free tier: 1 signature
        Pro tier: Unlimited

        Returns:
            True if user can create signature, False otherwise
        """
        return current_user.can_create_signature()

    @staticmethod
    def get_signature_stats(signature_id: int) -> dict:
        """
        Get analytics stats for a signature

        Security: A01 - Ownership verified before returning stats

        Args:
            signature_id: ID of signature

        Returns:
            Dictionary with signature statistics
        """
        signature = SignatureService.get_signature_by_id(signature_id)

        return {
            "signature_id": signature.id,
            "name": signature.name,
            "total_opens": signature.total_opens,
            "total_clicks": signature.total_clicks,
            "last_opened_at": signature.last_opened_at,
            "created_at": signature.created_at,
        }
