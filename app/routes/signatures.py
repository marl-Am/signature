# app/routes/signatures.py
import logging
from dataclasses import asdict, dataclass
from typing import Union

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.datastructures import ImmutableMultiDict
from werkzeug.wrappers import Response

from app.services.signature_service import SignatureService

logger = logging.getLogger(__name__)

signatures_bp = Blueprint("signatures", __name__, url_prefix="/signatures")


def _normalize_url(url: str | None) -> str | None:
    """
    Prepend https:// if no scheme is present.
    Allows users to type 'google.com' instead of requiring 'https://google.com'.
    """
    if not url:
        return None
    url = url.strip()
    if not url:
        return None
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


@dataclass(frozen=True)
class SignatureFormFields:
    """
    Typed result of reading the signature builder's optional fields from
    submitted form data. Each attribute keeps the same type
    SignatureService.create_signature/update_signature expects — the
    contact/social fields may be None, while accent_color/layout/
    font_family always fall back to a default and are never None.
    """

    job_title: str | None
    company: str | None
    department: str | None
    phone: str | None
    website: str | None
    linkedin_url: str | None
    twitter_url: str | None
    facebook_url: str | None
    instagram_url: str | None
    logo_url: str | None
    accent_color: str
    layout: str
    font_family: str


def _read_signature_form_fields(form: ImmutableMultiDict) -> SignatureFormFields:
    """
    Extract the signature builder's optional fields from submitted form
    data, applying the same trim/default/URL-normalization rules used by
    both create() and edit().
    """
    return SignatureFormFields(
        job_title=form.get("job_title", "").strip() or None,
        company=form.get("company", "").strip() or None,
        department=form.get("department", "").strip() or None,
        phone=form.get("phone", "").strip() or None,
        website=_normalize_url(form.get("website", "")),
        linkedin_url=_normalize_url(form.get("linkedin_url", "")),
        twitter_url=_normalize_url(form.get("twitter_url", "")),
        facebook_url=_normalize_url(form.get("facebook_url", "")),
        instagram_url=_normalize_url(form.get("instagram_url", "")),
        logo_url=_normalize_url(form.get("logo_url", "")),
        accent_color=form.get("accent_color", "#0c2788").strip() or "#0c2788",
        layout=form.get("layout", "classic").strip() or "classic",
        font_family=(
            form.get("font_family", "Arial, Helvetica, sans-serif").strip()
            or "Arial, Helvetica, sans-serif"
        ),
    )


@signatures_bp.route("/create", methods=["GET", "POST"])
@login_required
def create() -> Union[str, Response]:
    """Signature builder — form + live preview."""

    if not SignatureService.can_create_signature():
        flash(
            "You have reached the signature limit for your plan. "
            "Upgrade to Pro for unlimited signatures.",
            "warning",
        )
        return redirect(url_for("pricing"))

    if request.method == "POST":
        name: str = request.form.get("name", "").strip()
        full_name: str = request.form.get("full_name", "").strip()

        if not name or not full_name:
            flash("Signature label and full name are required.", "danger")
            return render_template("signatures/create.html", form_data=request.form)

        fields = _read_signature_form_fields(request.form)

        _, logo_error = SignatureService.validate_logo_url(fields.logo_url)
        if logo_error:
            flash(logo_error, "danger")
            return render_template("signatures/create.html", form_data=request.form)

        try:
            signature = SignatureService.create_signature(
                name=name, full_name=full_name, **asdict(fields)
            )
            flash(f'Signature "{signature.name}" created successfully!', "success")
            return redirect(url_for("dashboard.index"))
        except SQLAlchemyError:
            logger.exception(
                "Unexpected error creating signature for user %s", current_user.id
            )
            flash("An error occurred while saving. Please try again.", "danger")
            return render_template("signatures/create.html", form_data=request.form)

    return render_template("signatures/create.html")


@signatures_bp.route("/<int:signature_id>/edit", methods=["GET", "POST"])
@login_required
def edit(signature_id: int) -> Union[str, Response]:
    """Edit an existing signature — ownership enforced by the service (A01)."""

    # Ownership check happens inside get_signature_by_id → 404 if not owner
    signature = SignatureService.get_signature_by_id(signature_id)

    if request.method == "POST":
        name: str = request.form.get("name", "").strip()
        full_name: str = request.form.get("full_name", "").strip()

        if not name or not full_name:
            flash("Signature label and full name are required.", "danger")
            return render_template(
                "signatures/edit.html",
                signature=signature,
                form_data=request.form,
            )

        fields = _read_signature_form_fields(request.form)

        _, logo_error = SignatureService.validate_logo_url(fields.logo_url)
        if logo_error:
            flash(logo_error, "danger")
            return render_template(
                "signatures/edit.html",
                signature=signature,
                form_data=request.form,
            )

        try:
            updated = SignatureService.update_signature(
                signature_id, name=name, full_name=full_name, **asdict(fields)
            )
            flash(f'Signature "{updated.name}" updated successfully!', "success")
            return redirect(url_for("dashboard.index"))
        except SQLAlchemyError:
            logger.exception(
                "Unexpected error updating signature %s for user %s",
                signature_id,
                current_user.id,
            )
            flash("An error occurred while saving. Please try again.", "danger")
            return render_template(
                "signatures/edit.html",
                signature=signature,
                form_data=request.form,
            )

    return render_template("signatures/edit.html", signature=signature)


@signatures_bp.route("/<int:signature_id>/preview")
@login_required
def preview(signature_id: int) -> Union[str, Response]:
    """
    Render the saved signature HTML in isolation.

    The on-screen render uses a pixel-stripped copy so viewing your own
    signature does not inflate total_opens. The Copy Signature / Copy HTML
    buttons on this page still use signature.html_content directly (with
    the real pixel intact), since that's the exact HTML the user pastes
    into their actual email client.
    """
    signature = SignatureService.get_signature_by_id(signature_id)
    preview_html: str = SignatureService.strip_tracking_pixel(signature.html_content)
    return render_template(
        "signatures/preview.html", signature=signature, preview_html=preview_html
    )


@signatures_bp.route("/<int:signature_id>/delete", methods=["POST"])
@login_required
def delete(signature_id: int) -> Response:
    """Delete a signature — ownership enforced inside the service (A01)."""
    SignatureService.delete_signature(signature_id)
    flash("Signature deleted.", "success")
    return redirect(url_for("dashboard.index"))
