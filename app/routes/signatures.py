# app/routes/signatures.py
from flask import Blueprint, render_template, abort
from flask_login import login_required, current_user
from app.models.signature import Signature

signatures_bp = Blueprint("signatures", __name__, url_prefix="/signatures")

@signatures_bp.route("/<int:signature_id>/edit")
@login_required  # ← STEP 1: User must be logged in
def edit_signature(signature_id):
    # ← STEP 2: Fetch signature
    signature = Signature.query.get_or_404(signature_id)

    # ← STEP 3: Check if current user owns this signature
    if signature.user_id != current_user.id:
        abort(403)  # Forbidden - user doesn't own this resource

    return render_template("signatures/edit.html", signature=signature)
