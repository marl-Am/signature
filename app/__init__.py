# app/__init__.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()


def create_app():
    """Application factory pattern"""
    app = Flask(__name__)

    # Configuration
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL", "sqlite:///dev.db"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Initialize extensions with app
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    # Register blueprints (I'll do these later)
    # from app.routes.auth import auth_bp
    # app.register_blueprint(auth_bp)

    # Simple test route
    @app.route("/")
    def index():
        return """
        <h1>MySignature - Email Signature Generator</h1>
        <p>Architecture design project - Portfolio demonstration</p>
        <p>Status: Development phase - Hello World working! ✓</p>
        """

    return app
