# app/services/signature_service.py
"""
Signature service - Business logic for signature operations
"""

import re
import html
from urllib.parse import urlparse

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
        accent_color = SignatureService._sanitize_accent_color(
            accent_color, current_user
        )
        font_family = SignatureService._sanitize_font_family(font_family, current_user)
        layout = SignatureService._sanitize_layout(layout, current_user)
        tracking_code = secrets.token_urlsafe(16)

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
            is_active=True,
        )
        signature.html_content = SignatureService._build_html_content(signature)

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
            "font_family",
        ]

        for field, value in kwargs.items():
            if field in allowed_fields:
                if field == "accent_color":
                    value = SignatureService._sanitize_accent_color(value, current_user)
                elif field == "font_family":
                    value = SignatureService._sanitize_font_family(value, current_user)
                elif field == "layout":
                    value = SignatureService._sanitize_layout(value, current_user)
                setattr(signature, field, value)

        signature.updated_at = datetime.now(timezone.utc)

        signature.html_content = SignatureService._build_html_content(signature)

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
    def _escape(value: str | None) -> str:
        """
        HTML-escape user-supplied text before it is embedded in stored
        signature HTML.

        Security: A03 - This is what actually prevents stored XSS. Every
        free-text field (name, title, company, department, phone display
        text) must pass through this before landing in an f-string, since
        html_content is later rendered with Jinja's `| safe` filter on the
        preview page and pasted verbatim into real email clients.
        """
        return html.escape(value, quote=True) if value else ""

    @staticmethod
    def _sanitize_href(
        url: str | None,
        allowed_schemes: tuple[str, ...] = ("http", "https"),
    ) -> Optional[str]:
        """
        Validate a URL before it is embedded in an href/src attribute.

        Security: A03 - Rejects anything without an allowed scheme (blocks
        javascript:, data:, vbscript:, and malformed values that could
        break out of the surrounding double-quoted attribute) and
        HTML-escapes whatever is left. Returns None for anything invalid
        so callers can simply omit that link/image rather than render a
        broken or dangerous attribute.
        """
        if not url:
            return None
        try:
            parsed = urlparse(url)
        except ValueError:
            return None
        if parsed.scheme not in allowed_schemes or not parsed.netloc:
            return None
        return html.escape(url, quote=True)

    DEFAULT_ACCENT_COLOR: str = "#0c2788"
    _HEX_COLOR_PATTERN = re.compile(r"^#[0-9a-fA-F]{6}$")

    @staticmethod
    def _is_pro(user: object) -> bool:
        """
        Security: fails closed. Any missing or unexpected subscription_tier
        value is treated as free tier, never as pro.
        """
        return getattr(user, "subscription_tier", "free") == "pro"

    @staticmethod
    def _sanitize_accent_color(accent_color: str | None, user: object) -> str:
        """
        Validate a user-supplied accent color before it is embedded in
        inline style="" attributes across every layout.

        Security: A03 - accent_color was previously interpolated directly
        into style attributes with no escaping or format check, so a value
        containing a double-quote character could break out of the
        attribute and inject arbitrary HTML (stored XSS). Requiring a
        strict #RRGGBB match closes that gap entirely, since a valid match
        cannot contain a quote character.

        Also enforces that only Pro-tier accounts may override the default
        accent color at all — free-tier submissions are silently ignored
        rather than rejected, consistent with how the free-tier watermark
        fails closed elsewhere in this file.
        """
        if (
            SignatureService._is_pro(user)
            and accent_color
            and SignatureService._HEX_COLOR_PATTERN.fullmatch(accent_color)
        ):
            return accent_color
        return SignatureService.DEFAULT_ACCENT_COLOR

    DEFAULT_FONT_FAMILY: str = "Arial, Helvetica, sans-serif"

    # Free tier: a small, safe set of universally-available fonts.
    FREE_FONT_FAMILIES: frozenset[str] = frozenset(
        {
            "Arial, Helvetica, sans-serif",
            "Calibri, Candara, sans-serif",
            "'Times New Roman', Times, serif",
        }
    )

    # Pro tier: the full set offered in the UI's <select>. Deliberately a
    # superset of FREE_FONT_FAMILIES rather than a separate list, so a
    # free font is always valid for a Pro account too.
    PRO_FONT_FAMILIES: frozenset[str] = FREE_FONT_FAMILIES | frozenset(
        {
            "'Century Gothic', CenturyGothic, sans-serif",
            "'Courier New', Courier, monospace",
            "Garamond, 'EB Garamond', serif",
            "Georgia, 'Times New Roman', serif",
            "Palatino, 'Palatino Linotype', serif",
            "Tahoma, Geneva, sans-serif",
            "'Trebuchet MS', Tahoma, sans-serif",
            "Verdana, Geneva, sans-serif",
        }
    )

    DEFAULT_LAYOUT: str = "classic"

    # Free tier: the original single layout. Kept as its own frozenset
    # (rather than a bare string) so it matches the same type and calling
    # convention as FREE_FONT_FAMILIES, and so a future free-tier layout
    # addition is a one-line change here rather than a signature change.
    FREE_LAYOUTS: frozenset[str] = frozenset({"classic"})

    # Pro tier: every layout _generate_html_content knows how to render.
    # Deliberately a superset of FREE_LAYOUTS rather than a separate list,
    # so a free layout is always valid for a Pro account too.
    PRO_LAYOUTS: frozenset[str] = FREE_LAYOUTS | frozenset(
        {
            "modern",
            "minimal",
            "ruled",
            "avatar",
            "compact",
            "banner",
            "solid",
            "split",
        }
    )

    @staticmethod
    def _sanitize_layout(layout: str | None, user: object) -> str:
        """
        Validate a user-supplied layout name before it is used to select a
        rendering branch in _generate_html_content.

        Security/Business logic: layout was previously passed straight
        through from the form to storage and rendering with no tier check
        at all — unlike accent_color and font_family, a free-tier account
        could select any of the six Pro-only layouts (modern, minimal,
        ruled, avatar, compact, banner) directly in the UI, no crafted
        request required, and it would save and render normally. This
        closes that gap using the same fail-closed allow-list pattern as
        _sanitize_accent_color and _sanitize_font_family: anything not in
        the caller's tier-appropriate set silently falls back to the
        default rather than being rejected outright.

        Note: unlike accent_color/font_family, layout is never interpolated
        into HTML output directly — it only selects an if/elif branch in
        _generate_html_content, so this function's job is tier enforcement,
        not XSS prevention. That's already handled by the escaping applied
        to every field used within each branch.
        """
        allowed: frozenset[str] = (
            SignatureService.PRO_LAYOUTS
            if SignatureService._is_pro(user)
            else SignatureService.FREE_LAYOUTS
        )
        if layout in allowed:
            return layout
        return SignatureService.DEFAULT_LAYOUT

    @staticmethod
    def _sanitize_font_family(font_family: str | None, user: object) -> str:
        """
        Validate a user-supplied font family before it is embedded in
        inline style="" attributes across every layout.

        Security: A03 - font_family was previously interpolated directly
        into style attributes with no escaping or validation. The UI only
        ever offers a fixed <select> of values, but that's a client-side
        constraint only; a request built outside the form (curl, dev
        tools) could submit anything, including a value containing a
        double-quote character that breaks out of the attribute. A
        positive allow-list match closes this completely, since every
        permitted value is a literal string this file defines itself, none
        of which contain a double quote.

        Free-tier accounts are restricted to FREE_FONT_FAMILIES; Pro-tier
        accounts may pick from the larger PRO_FONT_FAMILIES set. Anything
        that doesn't match the caller's allowed set falls back to the
        default, the same fail-closed pattern as accent color and the
        free-tier watermark.
        """
        allowed: frozenset[str] = (
            SignatureService.PRO_FONT_FAMILIES
            if SignatureService._is_pro(user)
            else SignatureService.FREE_FONT_FAMILIES
        )
        if font_family in allowed:
            return font_family
        return SignatureService.DEFAULT_FONT_FAMILY

    @staticmethod
    def _get_initials(full_name: str | None) -> str:
        """
        Derive up to two initials from a full name, HTML-escaped, falling
        back to "YN" when no name is available.

        Shared by the avatar and split layouts, which both render initials
        in place of a logo when the user hasn't uploaded one.
        """
        words: list[str] = full_name.strip().split() if full_name else []
        return SignatureService._escape(
            "".join(w[0] for w in words[:2]).upper() if words else "YN"
        )

    @staticmethod
    def _wrap_table(safe_font_family: str, *cells: str) -> str:
        """
        Shared outer <table> used by every layout: same cellpadding/
        cellspacing/border/font-family/max-width wrapper, with the given
        cell HTML strings placed side by side in a single <tr>.

        Does not include the tracking pixel — callers append pixel_html
        after this, since the classic layout wraps this table in an
        additional outer <div> before adding the pixel.
        """
        return (
            f'<table cellpadding="0" cellspacing="0" border="0" '
            f'style="font-family:{safe_font_family};max-width:520px;">'
            "<tr>" + "".join(cells) + "</tr>"
            "</table>"
        )

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
        Supports nine layouts: classic, modern, minimal, ruled, avatar,
        compact, banner, solid, split.

        Free-tier accounts get a small "Sent with Signature" watermark
        appended after the signature body; Pro accounts do not. This is
        re-evaluated every time html_content is generated (on create and
        on edit), so a signature's watermark will reflect the user's
        current subscription_tier the next time it's saved.
        """

        # --- Escape/validate every user-supplied value up front (A03) ---
        safe_full_name: str = SignatureService._escape(full_name)
        safe_job_title: str = SignatureService._escape(job_title)
        safe_company: str = SignatureService._escape(company)
        safe_department: str = SignatureService._escape(department)
        safe_accent_color: str = (
            accent_color
            if accent_color
            and SignatureService._HEX_COLOR_PATTERN.fullmatch(accent_color)
            else SignatureService.DEFAULT_ACCENT_COLOR
        )
        safe_font_family: str = (
            font_family
            if font_family in SignatureService.PRO_FONT_FAMILIES
            else SignatureService.DEFAULT_FONT_FAMILY
        )
        safe_website: Optional[str] = SignatureService._sanitize_href(website)
        safe_logo_url: Optional[str] = SignatureService._sanitize_href(logo_url)
        safe_linkedin_url: Optional[str] = SignatureService._sanitize_href(linkedin_url)
        safe_twitter_url: Optional[str] = SignatureService._sanitize_href(twitter_url)
        safe_facebook_url: Optional[str] = SignatureService._sanitize_href(facebook_url)
        safe_instagram_url: Optional[str] = SignatureService._sanitize_href(
            instagram_url
        )

        # --- Name ---
        name_html: str = (
            f'<div style="font-size:17px;font-weight:bold;color:#111111;margin-bottom:3px;">'
            f"{safe_full_name}</div>"
        )

        # --- Title / Company ---
        title_parts: list[str] = [p for p in [safe_job_title, safe_company] if p]
        title_html: str = ""
        if title_parts:
            title_html = (
                f'<div style="font-size:13px;color:{safe_accent_color};margin-bottom:2px;">'
                + " &middot; ".join(title_parts)
                + "</div>"
            )

        # --- Department ---
        dept_html: str = ""
        if safe_department:
            dept_html = (
                f'<div style="font-size:12px;color:#777777;margin-bottom:2px;">'
                f"{safe_department}</div>"
            )

        # --- Divider ---
        divider_html: str = (
            '<div style="border-top:1px solid #e0e0e0;margin:8px 0;"></div>'
        )

        # --- Contact ---
        contact_parts: list[str] = []
        formatted_phone: str | None = SignatureService._format_phone(phone)
        safe_formatted_phone: str = SignatureService._escape(formatted_phone)
        if safe_formatted_phone:
            contact_parts.append(
                f'<a href="tel:{safe_formatted_phone}" style="color:#555555;text-decoration:none;font-size:12px;">'
                f"{safe_formatted_phone}</a>"
            )
        if safe_website:
            display: str = SignatureService._escape(
                website.replace("https://", "").replace("http://", "").rstrip("/")
                if website
                else ""
            )
            tracked_website: str = (
                f"{request.host_url.rstrip('/')}/track/click/{tracking_code}/website"
            )
            contact_parts.append(
                f'<a href="{tracked_website}" style="color:{safe_accent_color};text-decoration:none;font-size:12px;">'
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
            (safe_linkedin_url, "LinkedIn", "in", "linkedin"),
            (safe_twitter_url, "Twitter/X", "𝕏", "twitter"),
            (safe_facebook_url, "Facebook", "f", "facebook"),
            (safe_instagram_url, "Instagram", "IG", "instagram"),
        ]
        for url, label, badge, platform in social_map:
            if url:
                tracked: str = (
                    f"{request.host_url.rstrip('/')}/track/click/{tracking_code}/{platform}"
                )
                social_parts.append(
                    f'<a href="{tracked}" title="{label}" '
                    f'style="display:inline-block;background:{safe_accent_color};color:#ffffff;'
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
        if safe_logo_url:
            logo_html = (
                f'<td style="padding-right:16px;vertical-align:top;">'
                f'<img src="{safe_logo_url}" alt="Logo" width="64" height="64" '
                f'style="border-radius:6px;display:block;" /></td>'
            )

        # --- Tracking pixel ---
        pixel_html: str = (
            f'<img src="{request.host_url.rstrip("/")}/track/pixel/{tracking_code}.gif" '
            f'width="1" height="1" alt="" style="border:0;outline:none;" />'
        )

        # --- Free-tier watermark ---
        # This is static, developer-authored text, not user input, so it does
        # not go through _escape(). Defaults to showing the watermark
        # ("free") if subscription_tier is ever missing, rather than
        # defaulting to "pro" — since this is a retention/monetization
        # feature, failing closed (watermark shown) is the safe default.
        watermark_html: str = ""
        if getattr(current_user, "subscription_tier", "free") != "pro":
            watermark_html = (
                '<div style="margin-top:8px;font-size:10px;color:#aaaaaa;'
                'font-family:Arial, Helvetica, sans-serif;">'
                'Sent with <a href="' + request.host_url.rstrip("/") + '" '
                'style="color:#aaaaaa;text-decoration:underline;">Signature</a>'
                "</div>"
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
                f'<div style="background:{safe_accent_color};padding:10px 14px;border-radius:6px 6px 0 0;">'
                f'<div style="font-size:17px;font-weight:bold;color:#ffffff;margin-bottom:3px;">{safe_full_name}</div>'
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
                SignatureService._wrap_table(safe_font_family, logo_html, content_td)
                + pixel_html
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
                SignatureService._wrap_table(safe_font_family, logo_html, content_td)
                + pixel_html
            )

        elif layout == "ruled":
            # Top accent rule instead of left border
            content_td = (
                f'<td style="vertical-align:top;border-top:3px solid {safe_accent_color};padding-top:8px;">'
                + name_html
                + title_html
                + dept_html
                + contact_html
                + social_html
                + "</td>"
            )
            html = (
                SignatureService._wrap_table(safe_font_family, logo_html, content_td)
                + pixel_html
            )

        elif layout == "avatar":
            # Circular avatar (initials or logo) left of content
            initials: str = SignatureService._get_initials(full_name)
            if safe_logo_url:
                avatar_td = (
                    f'<td style="padding-right:16px;vertical-align:middle;">'
                    f'<img src="{safe_logo_url}" alt="{initials}" width="52" height="52" '
                    f'style="width:52px;height:52px;border-radius:50%;object-fit:cover;display:block;" /></td>'
                )
            else:
                avatar_td = (
                    f'<td style="padding-right:16px;vertical-align:middle;">'
                    f'<div style="width:52px;height:52px;border-radius:50%;background:{safe_accent_color};'
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
                SignatureService._wrap_table(safe_font_family, avatar_td, content_td)
                + pixel_html
            )

        elif layout == "compact":
            # Single-line contact row: Job · Company | phone | website
            job_span: str = (
                f'<span style="color:{safe_accent_color};font-weight:500;font-size:12px;">{safe_job_title}</span>'
                if safe_job_title
                else ""
            )
            comp_span: str = (
                f'<span style="color:#555555;font-size:12px;">{safe_company}</span>'
                if safe_company
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
                SignatureService._wrap_table(safe_font_family, logo_html, content_td)
                + pixel_html
            )

        elif layout == "banner":
            # Left-bordered name block; department as uppercase secondary label
            name_block: str = (
                f'<div style="border-left:4px solid {safe_accent_color};padding-left:12px;margin-bottom:8px;">'
                + name_html
                + title_html
                + "</div>"
            )
            dept_label: str = (
                f'<div style="font-size:11px;color:#888888;letter-spacing:0.05em;'
                f'text-transform:uppercase;margin-bottom:4px;">{safe_department}</div>'
                if safe_department
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
                SignatureService._wrap_table(safe_font_family, logo_html, content_td)
                + pixel_html
            )

        elif layout == "solid":
            # Full solid-color card, white text throughout. Built as its own
            # self-contained block rather than reusing name_html/title_html/
            # dept_html/contact_html/social_html, since those bake in dark,
            # on-white colors (e.g. color:#111111, accent-colored links)
            # that would be unreadable, or invisible, against a solid
            # accent-colored background.
            solid_logo_html: str = ""
            if safe_logo_url:
                solid_logo_html = (
                    f'<img src="{safe_logo_url}" alt="Logo" width="48" height="48" '
                    f'style="border-radius:6px;display:block;margin-bottom:10px;" />'
                )
            solid_name_html: str = (
                f'<div style="font-size:18px;font-weight:bold;color:#ffffff;margin-bottom:3px;">'
                f"{safe_full_name}</div>"
            )
            solid_title_html: str = ""
            if title_parts:
                solid_title_html = (
                    '<div style="font-size:13px;color:rgba(255,255,255,0.85);margin-bottom:2px;">'
                    + " &middot; ".join(title_parts)
                    + "</div>"
                )
            solid_dept_html: str = ""
            if safe_department:
                solid_dept_html = (
                    '<div style="font-size:12px;color:rgba(255,255,255,0.7);margin-bottom:2px;">'
                    f"{safe_department}</div>"
                )
            solid_divider_html: str = (
                '<div style="border-top:1px solid rgba(255,255,255,0.3);margin:8px 0;"></div>'
            )
            solid_contact_parts: list[str] = []
            if safe_formatted_phone:
                solid_contact_parts.append(
                    f'<a href="tel:{safe_formatted_phone}" style="color:#ffffff;text-decoration:none;font-size:12px;">'
                    f"{safe_formatted_phone}</a>"
                )
            if safe_website:
                solid_display: str = SignatureService._escape(
                    website.replace("https://", "").replace("http://", "").rstrip("/")
                    if website
                    else ""
                )
                solid_tracked_website: str = (
                    f"{request.host_url.rstrip('/')}/track/click/{tracking_code}/website"
                )
                solid_contact_parts.append(
                    f'<a href="{solid_tracked_website}" style="color:#ffffff;text-decoration:underline;font-size:12px;">'
                    f"{solid_display}</a>"
                )
            solid_contact_html: str = ""
            if solid_contact_parts:
                solid_contact_html = (
                    '<div style="margin-bottom:6px;">'
                    + ' <span style="color:rgba(255,255,255,0.5);">|</span> '.join(
                        solid_contact_parts
                    )
                    + "</div>"
                )
            solid_social_parts: list[str] = []
            for url, label, badge, platform in social_map:
                if url:
                    tracked = f"{request.host_url.rstrip('/')}/track/click/{tracking_code}/{platform}"
                    solid_social_parts.append(
                        f'<a href="{tracked}" title="{label}" '
                        f'style="display:inline-block;background:#ffffff;color:{safe_accent_color};'
                        f"font-size:11px;font-weight:bold;text-decoration:none;"
                        f'padding:3px 7px;border-radius:4px;margin-right:4px;">'
                        f"{badge}</a>"
                    )
            solid_social_html: str = ""
            if solid_social_parts:
                solid_social_html = (
                    '<div style="margin-top:4px;">'
                    + "".join(solid_social_parts)
                    + "</div>"
                )
            content_td = (
                f'<td style="background:{safe_accent_color};padding:18px 20px;'
                f'border-radius:8px;vertical-align:top;">'
                + solid_logo_html
                + solid_name_html
                + solid_title_html
                + solid_dept_html
                + solid_divider_html
                + solid_contact_html
                + solid_social_html
                + "</td>"
            )
            html = (
                SignatureService._wrap_table(safe_font_family, content_td) + pixel_html
            )

        elif layout == "split":
            # Two-column card: solid-color left rail with avatar/initials,
            # white right column with standard on-white text. The right
            # column reuses name_html/title_html/dept_html/divider_html/
            # contact_html/social_html as-is, since that side has the same
            # white background as the classic layout.
            split_initials: str = SignatureService._get_initials(full_name)
            if safe_logo_url:
                avatar_block: str = (
                    f'<img src="{safe_logo_url}" alt="{split_initials}" width="56" height="56" '
                    f'style="width:56px;height:56px;border-radius:50%;object-fit:cover;'
                    f'display:block;border:2px solid #ffffff;margin:0 auto;" />'
                )
            else:
                avatar_block = (
                    '<div style="width:56px;height:56px;border-radius:50%;'
                    "background:rgba(255,255,255,0.15);text-align:center;"
                    'line-height:56px;margin:0 auto;">'
                    '<span style="color:#ffffff;font-size:18px;font-weight:bold;line-height:56px;">'
                    f"{split_initials}</span></div>"
                )
            rail_td: str = (
                f'<td style="background:{safe_accent_color};padding:16px;text-align:center;'
                f'border-radius:8px 0 0 8px;vertical-align:middle;width:88px;">'
                + avatar_block
                + "</td>"
            )
            content_td = (
                '<td style="vertical-align:top;background:#ffffff;padding:16px 18px;'
                'border:1px solid #e0e0e0;border-left:none;border-radius:0 8px 8px 0;">'
                + name_html
                + title_html
                + dept_html
                + divider_html
                + contact_html
                + social_html
                + "</td>"
            )
            html = (
                SignatureService._wrap_table(safe_font_family, rail_td, content_td)
                + pixel_html
            )

        else:
            # Classic (default) — outer div carries the border so it always
            # sits on the far-left edge even when a logo column is present.
            content_td = '<td style="vertical-align:top;">' + body_html + "</td>"
            inner_table: str = SignatureService._wrap_table(
                safe_font_family, logo_html, content_td
            )
            html = (
                f'<div style="border-left:3px solid {safe_accent_color};padding-left:14px;">'
                + inner_table
                + "</div>"
                + pixel_html
            )

        if watermark_html:
            html += watermark_html

        return html

    @staticmethod
    def _build_html_content(signature: Signature) -> str:
        """
        Regenerate html_content from a Signature's current field values.

        Single source of truth for which fields feed HTML generation, so
        create_signature() and update_signature() can't drift out of sync
        with each other as fields are added.
        """
        return SignatureService._generate_html_content(
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
