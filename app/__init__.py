# app/__init__.py
from typing import Type

from dotenv import load_dotenv
from flask import Flask, render_template
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect

from app.config import DevelopmentConfig

load_dotenv()


db = SQLAlchemy(session_options={"expire_on_commit": False})
login_manager = LoginManager()
migrate = Migrate()
csrf = CSRFProtect()


def create_app(config_class: Type[object] = DevelopmentConfig) -> Flask:
    """
    Application factory pattern.

    Args:
        config_class: Config class to load (DevelopmentConfig, ProductionConfig,
            or TestingConfig from app.config). Defaults to DevelopmentConfig so
            every existing call site (wsgi.py) keeps working unchanged.
    """
    app = Flask(__name__, static_folder="static")

    # Load config object — caller decides which environment this is.
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access that page."
    login_manager.login_message_category = "warning"

    @login_manager.user_loader
    def load_user(user_id: str):
        from app.models.user import User

        return db.session.get(User, int(user_id))

    from app.routes.analytics import analytics_bp
    from app.routes.auth import auth_bp
    from app.routes.billing import billing_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.profile import profile_bp
    from app.routes.signatures import signatures_bp
    from app.routes.subscription import subscription_bp
    from app.routes.tracking import tracking_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(signatures_bp)
    app.register_blueprint(tracking_bp)
    app.register_blueprint(billing_bp)
    app.register_blueprint(subscription_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(profile_bp)

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/pricing")
    def pricing():
        return render_template("pricing.html")

    @app.route("/privacy")
    def privacy():
        return render_template("privacy.html")

    @app.route("/terms")
    def terms():
        return render_template("terms.html")

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_error(e):
        # Roll back any failed transaction before rendering the error page.
        # Without this, a broken session from the request that triggered
        # this handler causes the error page itself to fail with
        # sqlalchemy.exc.PendingRollbackError.
        db.session.rollback()
        return render_template("errors/500.html"), 500

    # Ensure every request ends with a clean session, success or failure —
    # this is what actually returns the connection to the pool correctly
    # rather than leaving it in a broken transaction state for the next
    # request to trip over.
    @app.teardown_appcontext
    def shutdown_session(exception=None):
        db.session.remove()

    return app
