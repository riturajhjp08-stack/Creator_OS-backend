import logging
import uuid
from flask import Flask, request, g, has_request_context
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from backend.config import config, validate_production_config
from backend.extensions import limiter
from models import db
from sqlalchemy import inspect, text
import os
from dotenv import load_dotenv
from werkzeug.middleware.proxy_fix import ProxyFix
from utils.auth_security import extract_access_token_from_request, is_session_active
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration

# Load backend/.env before reading config values.
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))


class RequestIdFilter(logging.Filter):
    def filter(self, record):
        if has_request_context():
            record.request_id = getattr(g, "request_id", "-")
        else:
            record.request_id = "-"
        return True


def _configure_logging(app):
    level_name = str(app.config.get("LOG_LEVEL", "INFO")).upper()
    level = getattr(logging, level_name, logging.INFO)
    log_format = str(app.config.get("LOG_FORMAT", "text")).lower()

    handler = logging.StreamHandler()
    handler.addFilter(RequestIdFilter())

    if log_format == "json":
        try:
            from pythonjsonlogger import jsonlogger
            formatter = jsonlogger.JsonFormatter(
                "%(asctime)s %(levelname)s %(name)s %(message)s %(request_id)s"
            )
        except Exception:
            formatter = logging.Formatter(
                "%(asctime)s %(levelname)s %(name)s %(message)s [%(request_id)s]"
            )
    else:
        formatter = logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s [%(request_id)s]"
        )

    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)


def _run_sqlite_compat_migrations():
    """
    Lightweight compatibility migration for local SQLite DB.
    Avoids breaking local dev when columns are added.
    """
    engine = db.engine
    if engine.dialect.name != "sqlite":
        return

    table_name = "scheduled_posts"
    inspector = inspect(engine)
    if table_name not in inspector.get_table_names():
        return

    existing_post_cols = {col["name"] for col in inspector.get_columns(table_name)}
    expected_posts = {
        "schedule_type": "TEXT DEFAULT 'now'",
        "scheduled_for": "DATETIME",
        "caption": "TEXT",
        "hashtags": "TEXT",
        "media_items": "JSON",
        "virality_score": "INTEGER",
        "external_post_id": "TEXT",
        "publish_response": "JSON",
        "error_message": "TEXT",
        "credits_spent": "INTEGER DEFAULT 0",
        "credits_earned": "INTEGER DEFAULT 0",
        "reward_granted": "BOOLEAN DEFAULT 0",
        "published_at": "DATETIME",
    }

    with engine.begin() as conn:
        for col, col_type in expected_posts.items():
            if col in existing_post_cols:
                continue
            conn.execute(text(f"ALTER TABLE scheduled_posts ADD COLUMN {col} {col_type}"))
            
    # Also migrate feedback table
    if "feedback" in inspector.get_table_names():
        existing_fb_cols = {col["name"] for col in inspector.get_columns("feedback")}
        expected_fb = {
            "reply": "TEXT",
            "replied_at": "DATETIME"
        }
        with engine.begin() as conn:
            for col, col_type in expected_fb.items():
                if col in existing_fb_cols:
                    continue
                conn.execute(text(f"ALTER TABLE feedback ADD COLUMN {col} {col_type}"))

    # Migrate users table
    if "users" in inspector.get_table_names():
        existing_user_cols = {col["name"] for col in inspector.get_columns("users")}
        if "status" not in existing_user_cols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE users ADD COLUMN status VARCHAR(50) DEFAULT 'active'"))

def create_app(config_name=None):
    """Application factory"""
    if config_name is None:
        config_name = os.getenv("FLASK_ENV", "development")
    
    app = Flask(__name__)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    
    # Load config
    app.config.from_object(config[config_name])
    validate_production_config(app)

    _configure_logging(app)

    # SQLAlchemy engine options for non-SQLite only.
    db_uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
    if db_uri.startswith("sqlite"):
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {}
    
    # Initialize extensions
    db.init_app(app)
    limiter.init_app(app)
    CORS(
        app,
        resources={r"/api/*": {"origins": app.config.get("CORS_ALLOWED_ORIGINS") or []}},
        allow_headers=["Content-Type", "Authorization", "X-CSRF-TOKEN"],
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        supports_credentials=True,
    )
    JWTManager(app)

    # Observability
    if app.config.get("SENTRY_DSN"):
        sentry_sdk.init(
            dsn=app.config["SENTRY_DSN"],
            integrations=[FlaskIntegration()],
            traces_sample_rate=0.1,
        )

    logging.getLogger("werkzeug").setLevel(logging.getLogger().level)
    
    # Create database tables
    with app.app_context():
        if app.config.get("ENV_NAME") != "production" and app.config.get("DB_AUTO_CREATE", True):
            db.create_all()
            _run_sqlite_compat_migrations()
    
    # Register blueprints
    from routes.auth import auth_bp
    from routes.platforms import platforms_bp
    from routes.analytics import analytics_bp
    from routes.ai import ai_bp
    from routes.posts import posts_bp
    from routes.user import user_bp
    from routes.feedback import feedback_bp
    from routes.admin import admin_bp
    from routes.admin_advanced import admin_advanced_bp
    from routes.notifications import notifications_bp
    
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(platforms_bp, url_prefix='/api/platforms')
    app.register_blueprint(analytics_bp, url_prefix='/api/analytics')
    app.register_blueprint(ai_bp, url_prefix='/api/ai')
    app.register_blueprint(posts_bp, url_prefix='/api/posts')
    app.register_blueprint(user_bp, url_prefix='/api/user')
    app.register_blueprint(feedback_bp, url_prefix='/api/feedback')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    app.register_blueprint(admin_advanced_bp, url_prefix='/api/admin_advanced')
    app.register_blueprint(notifications_bp, url_prefix='/api/notifications')

    public_paths = {
        "/health",
        "/api/auth/register",
        "/api/auth/login",
        "/api/auth/google/login",
        "/api/auth/google/callback",
        "/api/auth/tiktok/login",
        "/api/auth/tiktok/callback",
        "/api/auth/verify-token",
        "/api/platforms/youtube/callback",
        "/api/platforms/instagram/callback",
        "/api/platforms/instagram/test-callback",
        "/api/platforms/tiktok/callback",
        "/api/platforms/twitter/callback",
        "/api/platforms/linkedin/callback",
    }

    @app.before_request
    def enforce_session_revocation():
        if request.method == "OPTIONS":
            return None
        path = request.path
        if not path.startswith("/api/"):
            return None
        if path in public_paths:
            return None
        # Admin endpoints use short-lived tokens but do not create sessions.
        if path.startswith("/api/admin"):
            return None
        if path.startswith("/api/admin_advanced"):
            return None

        raw_token = extract_access_token_from_request()
        if not raw_token:
            return {"error": "Missing authorization token"}, 401
        if not is_session_active(raw_token):
            return {"error": "Session expired or revoked"}, 401
        return None

    @app.before_request
    def assign_request_id():
        g.request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex

    @app.after_request
    def set_request_id(response):
        response.headers.setdefault("X-Request-ID", getattr(g, "request_id", ""))
        return response

    @app.after_request
    def set_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Permissions-Policy", "geolocation=()")
        if app.config.get("ENV_NAME") == "production":
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response

    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return {"error": "Not found"}, 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return {"error": "Internal server error"}, 500
    
    # Health check
    @app.route('/health', methods=['GET'])
    def health():
        return {"status": "healthy"}, 200

    @app.route('/ready', methods=['GET'])
    def ready():
        try:
            db.session.execute(text("SELECT 1"))
            return {"status": "ready"}, 200
        except Exception:
            return {"status": "not_ready"}, 503
    
    return app

if __name__ == '__main__':
    env_name = os.getenv("FLASK_ENV", "development")
    app = create_app(env_name)
    app.run(
        host='0.0.0.0',
        port=int(os.getenv("PORT", "5004")),
        threaded=True
    )
