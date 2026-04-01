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
        tracking_code = secrets.token_urlsafe(16)

        html_content: str = SignatureService._generate_html_content(
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
        )

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
        signature = SignatureService.get_signature_by_id(signature_id)

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

        signature.html_content = SignatureService._generate_html_content(
            full_name=signature.full_name,
            job_title=signature.job_title,
            company=signature.company,
            department=signature.department,
            phone=signature.phone,
            website=signature.website,
            linkedin_url=signature.linkedin_url,
            twitter_url=signature.twitter_url,
            facebook_url=signature.facebook_url,
            instagram_url=signature.instagram_url,
            logo_url=signature.logo_url,
            tracking_code=signature.tracking_code,
        )

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

    @staticmethod
    def _generate_html_content(
        full_name: str,
        job_title: str | None,
        company: str | None,
        department: str | None,
        phone: str | None,
        website: str | None,
        linkedin_url: str | None,
        twitter_url: str | None,
        facebook_url: str | None,
        instagram_url: str | None,
        logo_url: str | None,
        tracking_code: str,
    ) -> str:
        """
        Generate email-client-compatible HTML for the signature.

        Click tracking: social and website links go through
        /track/click/<tracking_code>/<platform> so every click increments
        the counter before the recipient reaches the real destination.

        A10 (SSRF): the redirect endpoint reads the destination from the
        database, so the tracking URL itself never carries the real URL.
        """
        brand: str = "rgb(12, 39, 136)"

        # --- Name row ---
        name_html: str = (
            f'<div style="font-size:17px;font-weight:bold;color:#111111;margin-bottom:3px;">'
            f"{full_name}"
            f"</div>"
        )

        # --- Title / Company row ---
        title_parts: list[str] = [p for p in [job_title, company] if p]
        title_html: str = ""
        if title_parts:
            title_html = (
                f'<div style="font-size:13px;color:{brand};margin-bottom:2px;">'
                + " &middot; ".join(title_parts)
                + "</div>"
            )

        # --- Department row ---
        dept_html: str = ""
        if department:
            dept_html = (
                f'<div style="font-size:12px;color:#777777;margin-bottom:2px;">'
                f"{department}"
                f"</div>"
            )

        # --- Divider ---
        divider_html: str = (
            '<div style="border-top:1px solid #e0e0e0;margin:8px 0;"></div>'
        )

        # --- Contact row ---
        # Phone: no tracking needed (tel: links do not load images or hit servers)
        # Website: routed through click tracker so the open is counted
        contact_parts: list[str] = []
        formatted_phone: str | None = SignatureService._format_phone(phone)
        if formatted_phone:
            contact_parts.append(
                f'<a href="tel:{formatted_phone}" style="color:#555555;text-decoration:none;font-size:12px;">'
                f"{formatted_phone}</a>"
            )
        if website:
            display: str = (
                website.replace("https://", "").replace("http://", "").rstrip("/")
            )
            tracked_website: str = f"/track/click/{tracking_code}/website"
            contact_parts.append(
                f'<a href="{tracked_website}" style="color:{brand};text-decoration:none;font-size:12px;">'
                f"{display}</a>"
            )
        contact_html: str = ""
        if contact_parts:
            contact_html = (
                '<div style="margin-bottom:6px;">'
                + ' <span style="color:#cccccc;">|</span> '.join(contact_parts)
                + "</div>"
            )

        # --- Social links row ---
        # href points to the click-tracking redirect, not the raw URL.
        # The platform segment matches the keys in tracking._PLATFORM_FIELD.
        social_parts: list[str] = []
        social_map: list[tuple[str | None, str, str, str]] = [
            (linkedin_url, "LinkedIn", "in", "linkedin"),
            (twitter_url, "Twitter/X", "𝕏", "twitter"),
            (facebook_url, "Facebook", "f", "facebook"),
            (instagram_url, "Instagram", "IG", "instagram"),
        ]
        for url, label, badge, platform in social_map:
            if url:
                tracked: str = f"/track/click/{tracking_code}/{platform}"
                social_parts.append(
                    f'<a href="{tracked}" title="{label}" '
                    f'style="display:inline-block;background:{brand};color:#ffffff;'
                    f"font-size:11px;font-weight:bold;text-decoration:none;"
                    f'padding:3px 7px;border-radius:4px;margin-right:4px;">'
                    f"{badge}</a>"
                )
        social_html: str = ""
        if social_parts:
            social_html = (
                '<div style="margin-top:4px;">' + "".join(social_parts) + "</div>"
            )

        # --- Logo column ---
        logo_html: str = ""
        if logo_url:
            logo_html = (
                f'<td style="padding-right:16px;vertical-align:top;">'
                f'<img src="{logo_url}" alt="Logo" width="64" height="64" '
                f'style="border-radius:6px;display:block;" />'
                f"</td>"
            )

        # --- Left border accent (only when no logo) ---
        border_style: str = (
            f"border-left:3px solid {brand};padding-left:14px;" if not logo_url else ""
        )

        # --- Tracking pixel ---
        pixel_html: str = (
            f'<img src="/track/pixel/{tracking_code}.gif" '
            f'width="1" height="1" alt="" style="display:none;" />'
        )

        # --- Assemble ---
        content_td: str = (
            f'<td style="vertical-align:top;{border_style}">'
            + name_html
            + title_html
            + dept_html
            + divider_html
            + contact_html
            + social_html
            + "</td>"
        )

        html: str = (
            '<table cellpadding="0" cellspacing="0" border="0" '
            'style="font-family:Arial,Helvetica,sans-serif;max-width:520px;">'
            "<tr>" + logo_html + content_td + "</tr>"
            "</table>" + pixel_html
        )

        return html

    @staticmethod
    def _format_phone(phone: str | None) -> str | None:
        """
        Normalize a phone number to +1 XXX XXX XXXX format.
        Handles 10-digit (US) and 11-digit (1 + US) inputs.
        Falls back to the raw string for anything else.
        """
        if not phone:
            return None
        digits: str = "".join(ch for ch in phone if ch.isdigit())
        if len(digits) == 11 and digits[0] == "1":
            return f"+1 {digits[1:4]} {digits[4:7]} {digits[7:]}"
        if len(digits) == 10:
            return f"+1 {digits[0:3]} {digits[3:6]} {digits[6:]}"
        return phone
