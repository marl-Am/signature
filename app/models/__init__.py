# app/models/__init__.py
"""
Import all models here for easy access and to ensure they're registered with SQLAlchemy
"""

from app.models.user import User
from app.models.signature import Signature
from app.models.analytics import SignatureOpen, SignatureClick

# Export models for easier imports elsewhere
__all__ = ["User", "Signature", "SignatureOpen", "SignatureClick"]

# This allows me to do:
# from app.models import User, Signature
