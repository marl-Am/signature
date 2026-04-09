"""add email_verification_expires

Revision ID: add_email_verif_expires
Revises: <replace with your current head revision ID>
Create Date: 2026-04-09

IMPORTANT (SQLite rule): nullable=True columns can be added without a
server_default, so no manual edit is required before running db upgrade.
"""

from alembic import op
import sqlalchemy as sa


# ---------------------------------------------------------------------------
# Replace the placeholder below with the output of:
#   flask --app wsgi:app db heads
# ---------------------------------------------------------------------------
revision = "b9e3f1a72c04"
down_revision = "3367ea2db3da"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("email_verification_expires", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "email_verification_expires")
