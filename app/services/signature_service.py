# app/services/signature_service.py
"""
Signature service - Business logic for signature operations

Security: A01 - All queries filtered by user_id to prevent unauthorized access
"""

import re

from flask import request
from app import db
from app.models.signature import Signature
from flask_login import current_user
from typing import List, Optional
import secrets
from datetime import datetime, timezone


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
        accent_color: str = "#0c2788",
        layout: str = "classic",
        font_family: str = "Arial, Helvetica, sans-serif",
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
            accent_color=accent_color,
            layout=layout,
            font_family=font_family,
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
            accent_color=accent_color,
            layout=layout,
            font_family=font_family,
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
            "accent_color",
            "layout",
            "font_family",  # ← add these
        ]

        for field, value in kwargs.items():
            if field in allowed_fields:
                setattr(signature, field, value)

        signature.updated_at = datetime.now(timezone.utc)

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
            accent_color=signature.accent_color,
            layout=signature.layout,
            font_family=signature.font_family,
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
        accent_color: str = "#0c2788",
        layout: str = "classic",
        font_family: str = "Arial, Helvetica, sans-serif",
    ) -> str:
        """
        Generate email-client-compatible HTML for the signature.
        Supports three layouts: classic, modern, minimal.
        """

        # --- Name ---
        name_html: str = (
            f'<div style="font-size:17px;font-weight:bold;color:#111111;margin-bottom:3px;">'
            f"{full_name}</div>"
        )

        # --- Title / Company ---
        title_parts: list[str] = [p for p in [job_title, company] if p]
        title_html: str = ""
        if title_parts:
            title_html = (
                f'<div style="font-size:13px;color:{accent_color};margin-bottom:2px;">'
                + " &middot; ".join(title_parts)
                + "</div>"
            )

        # --- Department ---
        dept_html: str = ""
        if department:
            dept_html = (
                f'<div style="font-size:12px;color:#777777;margin-bottom:2px;">'
                f"{department}</div>"
            )

        # --- Divider ---
        divider_html: str = (
            '<div style="border-top:1px solid #e0e0e0;margin:8px 0;"></div>'
        )

        # --- Contact ---
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
            tracked_website: str = (
                f"{request.host_url.rstrip('/')}/track/click/{tracking_code}/website"
            )
            contact_parts.append(
                f'<a href="{tracked_website}" style="color:{accent_color};text-decoration:none;font-size:12px;">'
                f"{display}</a>"
            )
        contact_html: str = ""
        if contact_parts:
            contact_html = (
                '<div style="margin-bottom:6px;">'
                + ' <span style="color:#cccccc;">|</span> '.join(contact_parts)
                + "</div>"
            )

        # --- Social links ---
        social_parts: list[str] = []
        social_map: list[tuple[str | None, str, str, str]] = [
            (linkedin_url, "LinkedIn", "in", "linkedin"),
            (twitter_url, "Twitter/X", "𝕏", "twitter"),
            (facebook_url, "Facebook", "f", "facebook"),
            (instagram_url, "Instagram", "IG", "instagram"),
        ]
        for url, label, badge, platform in social_map:
            if url:
                tracked: str = (
                    f"{request.host_url.rstrip('/')}/track/click/{tracking_code}/{platform}"
                )
                social_parts.append(
                    f'<a href="{tracked}" title="{label}" '
                    f'style="display:inline-block;background:{accent_color};color:#ffffff;'
                    f"font-size:11px;font-weight:bold;text-decoration:none;"
                    f'padding:3px 7px;border-radius:4px;margin-right:4px;">'
                    f"{badge}</a>"
                )
        social_html: str = ""
        if social_parts:
            social_html = (
                '<div style="margin-top:4px;">' + "".join(social_parts) + "</div>"
            )

        # --- Logo ---
        logo_html: str = ""
        if logo_url:
            logo_html = (
                f'<td style="padding-right:16px;vertical-align:top;">'
                f'<img src="{logo_url}" alt="Logo" width="64" height="64" '
                f'style="border-radius:6px;display:block;" /></td>'
            )

        # --- Tracking pixel ---
        pixel_html: str = (
            f'<img src="{request.host_url.rstrip("/")}/track/pixel/{tracking_code}.gif" '
            f'width="1" height="1" alt="" style="display:none;" />'
        )

        # --- Layout: build content_td differently per layout ---
        body_html: str = (
            name_html
            + title_html
            + dept_html
            + divider_html
            + contact_html
            + social_html
        )

        if layout == "modern":
            # Colored header band containing name + title, white body below
            header_html: str = (
                f'<div style="background:{accent_color};padding:10px 14px;border-radius:6px 6px 0 0;">'
                f'<div style="font-size:17px;font-weight:bold;color:#ffffff;margin-bottom:3px;">{full_name}</div>'
            )
            if title_parts:
                header_html += (
                    '<div style="font-size:13px;color:rgba(255,255,255,0.8);">'
                    + " &middot; ".join(title_parts)
                    + "</div>"
                )
            header_html += "</div>"
            sub_html: str = (
                '<div style="background:#f9f9f9;padding:10px 14px;border-radius:0 0 6px 6px;'
                'border:1px solid #e0e0e0;border-top:none;">'
                + (dept_html if department else "")
                + contact_html
                + social_html
                + "</div>"
            )
            content_td = (
                '<td style="vertical-align:top;">' + header_html + sub_html + "</td>"
            )
            html = (
                f'<table cellpadding="0" cellspacing="0" border="0" '
                f'style="font-family:{font_family};max-width:520px;">'
                "<tr>" + logo_html + content_td + "</tr>"
                "</table>" + pixel_html
            )

        elif layout == "minimal":
            # Clean, no border, no divider
            content_td = (
                '<td style="vertical-align:top;padding:4px 0;">'
                + name_html
                + title_html
                + dept_html
                + contact_html
                + social_html
                + "</td>"
            )
            html = (
                f'<table cellpadding="0" cellspacing="0" border="0" '
                f'style="font-family:{font_family};max-width:520px;">'
                "<tr>" + logo_html + content_td + "</tr>"
                "</table>" + pixel_html
            )

        elif layout == "ruled":
            # Top accent rule instead of left border
            content_td = (
                f'<td style="vertical-align:top;border-top:3px solid {accent_color};padding-top:8px;">'
                + name_html
                + title_html
                + dept_html
                + contact_html
                + social_html
                + "</td>"
            )
            html = (
                f'<table cellpadding="0" cellspacing="0" border="0" '
                f'style="font-family:{font_family};max-width:520px;">'
                "<tr>" + logo_html + content_td + "</tr>"
                "</table>" + pixel_html
            )

        elif layout == "avatar":
            # Circular avatar (initials or logo) left of content
            words: list[str] = full_name.strip().split() if full_name else []
            initials: str = "".join(w[0] for w in words[:2]).upper() if words else "YN"
            if logo_url:
                avatar_td = (
                    f'<td style="padding-right:16px;vertical-align:middle;">'
                    f'<img src="{logo_url}" alt="{initials}" width="52" height="52" '
                    f'style="width:52px;height:52px;border-radius:50%;object-fit:cover;display:block;" /></td>'
                )
            else:
                avatar_td = (
                    f'<td style="padding-right:16px;vertical-align:middle;">'
                    f'<div style="width:52px;height:52px;border-radius:50%;background:{accent_color};'
                    f'text-align:center;line-height:52px;display:inline-block;">'
                    f'<span style="color:#ffffff;font-size:16px;font-weight:bold;line-height:52px;">'
                    f"{initials}</span></div></td>"
                )
            content_td = (
                '<td style="vertical-align:middle;">'
                + name_html
                + title_html
                + dept_html
                + divider_html
                + contact_html
                + social_html
                + "</td>"
            )
            html = (
                f'<table cellpadding="0" cellspacing="0" border="0" '
                f'style="font-family:{font_family};max-width:520px;">'
                "<tr>" + avatar_td + content_td + "</tr>"
                "</table>" + pixel_html
            )

        elif layout == "compact":
            # Single-line contact row: Job · Company | phone | website
            job_span: str = (
                f'<span style="color:{accent_color};font-weight:500;font-size:12px;">{job_title}</span>'
                if job_title
                else ""
            )
            comp_span: str = (
                f'<span style="color:#555555;font-size:12px;">{company}</span>'
                if company
                else ""
            )
            sep1: str = (
                '<span style="color:#cccccc;margin:0 5px;">&middot;</span>'
                if job_span and comp_span
                else ""
            )
            sep2: str = (
                '<span style="color:#cccccc;margin:0 8px;">|</span>'
                if (job_span or comp_span) and contact_parts
                else ""
            )
            inline_contact: str = (
                '<span style="color:#cccccc;margin:0 5px;">|</span>'.join(contact_parts)
            )
            compact_row: str = (
                '<div style="font-size:12px;margin-bottom:5px;">'
                + job_span
                + sep1
                + comp_span
                + sep2
                + inline_contact
                + "</div>"
            )
            content_td = (
                '<td style="vertical-align:top;padding:4px 0;">'
                + name_html
                + dept_html
                + compact_row
                + social_html
                + "</td>"
            )
            html = (
                f'<table cellpadding="0" cellspacing="0" border="0" '
                f'style="font-family:{font_family};max-width:520px;">'
                "<tr>" + logo_html + content_td + "</tr>"
                "</table>" + pixel_html
            )

        elif layout == "banner":
            # Left-bordered name block; department as uppercase secondary label
            name_block: str = (
                f'<div style="border-left:4px solid {accent_color};padding-left:12px;margin-bottom:8px;">'
                + name_html
                + title_html
                + "</div>"
            )
            dept_label: str = (
                f'<div style="font-size:11px;color:#888888;letter-spacing:0.05em;'
                f'text-transform:uppercase;margin-bottom:4px;">{department}</div>'
                if department
                else ""
            )
            content_td = (
                '<td style="vertical-align:top;">'
                + name_block
                + dept_label
                + contact_html
                + social_html
                + "</td>"
            )
            html = (
                f'<table cellpadding="0" cellspacing="0" border="0" '
                f'style="font-family:{font_family};max-width:520px;">'
                "<tr>" + logo_html + content_td + "</tr>"
                "</table>" + pixel_html
            )

        else:
            # Classic (default) — outer div carries the border so it always
            # sits on the far-left edge even when a logo column is present.
            content_td = '<td style="vertical-align:top;">' + body_html + "</td>"
            inner_table: str = (
                f'<table cellpadding="0" cellspacing="0" border="0" '
                f'style="font-family:{font_family};max-width:520px;">'
                "<tr>" + logo_html + content_td + "</tr>"
                "</table>"
            )
            html = (
                f'<div style="border-left:3px solid {accent_color};padding-left:14px;">'
                + inner_table
                + "</div>"
                + pixel_html
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

    # Matches the exact tracking pixel <img> tag produced in
    # _generate_html_content — targeted narrowly by the /track/pixel/ path
    # segment so it can never accidentally strip a user's own logo <img>.
    _PIXEL_IMG_PATTERN = re.compile(r'<img[^>]*?/track/pixel/[^"]*\.gif[^>]*/?>')

    @staticmethod
    def strip_tracking_pixel(html_content: str) -> str:
        """
        Return signature HTML with the tracking pixel <img> tag removed.

        Used ONLY for the in-app visual preview. Loading the preview page
        in a browser fetches every <img> on it just like a real email
        client would, which would otherwise increment total_opens every
        time the owner previews their own signature. The stored
        html_content used for the Copy Signature/Copy HTML buttons and for
        real outgoing emails is never modified — only what's rendered
        on-screen here.
        """
        return SignatureService._PIXEL_IMG_PATTERN.sub("", html_content)
