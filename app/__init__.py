# app/__init__.py
from typing import Any, Type, cast

from dotenv import load_dotenv
from flask import Flask, render_template
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from werkzeug.middleware.proxy_fix import ProxyFix

from app.config import Config, DevelopmentConfig

load_dotenv()


db = SQLAlchemy(session_options={"expire_on_commit": False})
login_manager = LoginManager()
migrate = Migrate()
csrf = CSRFProtect()


def create_app(config_class: Type[Config] = DevelopmentConfig) -> Flask:
    """
    Application factory pattern.

    Args:
        config_class: Config class to load (DevelopmentConfig, ProductionConfig,
            or TestingConfig from app.config). Defaults to DevelopmentConfig so
            every existing call site (wsgi.py) keeps working unchanged.
    """
    app = Flask(__name__, static_folder="static")

    # Render's load balancer is the only proxy hop in front of this app
    # (no Cloudflare — this runs on the plain .onrender.com subdomain).
    # x_for=1, x_proto=1 trusts exactly that one hop when reading the real
    # client IP from X-Forwarded-For. Do NOT raise this without also adding
    # a real second hop (e.g. a custom domain routed through Cloudflare) —
    # trusting more hops than actually exist lets a client fake its own IP.
    #
    # cast() here is deliberate: ProxyFix wraps wsgi_app in a new callable
    # that satisfies the same (environ, start_response) -> Iterable[bytes]
    # contract at runtime, but Werkzeug's stubs type wsgi_app as a bound
    # method specifically, so static analysis can't verify the match.

    # app.wsgi_app = cast(  # type: ignore[method-assign]
    #     "WSGIApplication", ProxyFix(app.wsgi_app, x_for=1, x_proto=1)
    # )
    app.wsgi_app = cast(Any, ProxyFix(app.wsgi_app, x_for=1, x_proto=1))

    # Load config object — caller decides which environment this is.
    app.config.from_object(config_class)
    config_class.init_app(app)

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
