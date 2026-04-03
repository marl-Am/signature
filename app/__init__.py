# app/__init__.py
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from dotenv import load_dotenv
from app.config import DevelopmentConfig
import os

load_dotenv()

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()


def create_app() -> Flask:
    """Application factory pattern"""
    app = Flask(__name__)

    # Load config object (swap to ProductionConfig for prod)
    app.config.from_object(DevelopmentConfig)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    # A07: Redirect unauthenticated users to login; show a warning flash
    login_manager.login_view = "auth.login"  # type: ignore[assignment]
    login_manager.login_message = "Please log in to access that page."
    login_manager.login_message_category = "warning"

    @login_manager.user_loader
    def load_user(user_id: str):
        from app.models.user import User

        return User.query.get(int(user_id))

    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.signatures import signatures_bp
    from app.routes.tracking import tracking_bp
    from app.routes.billing import billing_bp
    from app.routes.subscription import subscription_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(signatures_bp)
    app.register_blueprint(tracking_bp)
    app.register_blueprint(billing_bp)
    app.register_blueprint(subscription_bp)

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/pricing")
    def pricing():
        return render_template("pricing.html")

    # Custom error pages
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template("errors/404.html"), 404

    return app
