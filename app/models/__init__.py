# app/models/__init__.py
"""
Models package - Database models for MySignature

Import all models here for easy access and to ensure they're registered with SQLAlchemy
"""

from app.models.user import User
from app.models.signature import Signature

# Export models for easier imports elsewhere
__all__ = ["User", "Signature"]

# This allows you to do:
# from app.models import User, Signature
# Instead of:
# from app.models.user import User
# from app.models.signature import Signature
