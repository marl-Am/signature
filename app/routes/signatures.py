# app/routes/signatures.py
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from werkzeug.wrappers import Response
from typing import Union

from app.services.signature_service import SignatureService

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
        job_title: str | None = request.form.get("job_title", "").strip() or None
        company: str | None = request.form.get("company", "").strip() or None
        department: str | None = request.form.get("department", "").strip() or None
        phone: str | None = request.form.get("phone", "").strip() or None

        website: str | None = _normalize_url(request.form.get("website", ""))
        linkedin_url: str | None = _normalize_url(request.form.get("linkedin_url", ""))
        twitter_url: str | None = _normalize_url(request.form.get("twitter_url", ""))
        facebook_url: str | None = _normalize_url(request.form.get("facebook_url", ""))
        instagram_url: str | None = _normalize_url(
            request.form.get("instagram_url", "")
        )
        logo_url: str | None = _normalize_url(request.form.get("logo_url", ""))

        if not name or not full_name:
            flash("Signature label and full name are required.", "danger")
            return render_template("signatures/create.html", form_data=request.form)

        try:
            signature = SignatureService.create_signature(
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
                accent_color=request.form.get("accent_color", "#0c2788").strip()
                or "#0c2788",
                layout=request.form.get("layout", "classic").strip() or "classic",
                font_family=request.form.get(
                    "font_family", "Arial, Helvetica, sans-serif"
                ).strip()
                or "Arial, Helvetica, sans-serif",
            )
            flash(f'Signature "{signature.name}" created successfully!', "success")
            return redirect(url_for("dashboard.index"))
        except Exception:
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

        job_title: str | None = request.form.get("job_title", "").strip() or None
        company: str | None = request.form.get("company", "").strip() or None
        department: str | None = request.form.get("department", "").strip() or None
        phone: str | None = request.form.get("phone", "").strip() or None

        website: str | None = _normalize_url(request.form.get("website", ""))
        linkedin_url: str | None = _normalize_url(request.form.get("linkedin_url", ""))
        twitter_url: str | None = _normalize_url(request.form.get("twitter_url", ""))
        facebook_url: str | None = _normalize_url(request.form.get("facebook_url", ""))
        instagram_url: str | None = _normalize_url(
            request.form.get("instagram_url", "")
        )
        logo_url: str | None = _normalize_url(request.form.get("logo_url", ""))

        try:
            updated = SignatureService.update_signature(
                signature_id,
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
                accent_color=request.form.get("accent_color", "#0c2788").strip()
                or "#0c2788",
                layout=request.form.get("layout", "classic").strip() or "classic",
                font_family=request.form.get(
                    "font_family", "Arial, Helvetica, sans-serif"
                ).strip()
                or "Arial, Helvetica, sans-serif",
            )
            flash(f'Signature "{updated.name}" updated successfully!', "success")
            return redirect(url_for("dashboard.index"))
        except Exception:
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
    """Render the saved signature HTML in isolation."""
    signature = SignatureService.get_signature_by_id(signature_id)
    return render_template("signatures/preview.html", signature=signature)


@signatures_bp.route("/<int:signature_id>/delete", methods=["POST"])
@login_required
def delete(signature_id: int) -> Response:
    """Delete a signature — ownership enforced inside the service (A01)."""
    SignatureService.delete_signature(signature_id)
    flash("Signature deleted.", "success")
    return redirect(url_for("dashboard.index"))
