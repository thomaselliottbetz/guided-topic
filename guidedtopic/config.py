import os
import secrets
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DB_PATH = BASE_DIR.parent / "instance" / "guidedtopic.db"
DEFAULT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def _env_bool(name: str, default: Union[str, bool] = "True") -> bool:
    value = os.getenv(name, default)
    if isinstance(value, bool):
        return value
    return str(value).lower() in {"1", "true", "yes", "on"}


class Config:
    """Base configuration driven by environment variables."""

    SECRET_KEY = (
        os.getenv("GUIDEDTOPIC_SECRET_KEY")
        or os.getenv("SECRET_KEY")
        or secrets.token_urlsafe(32)
    )

    SQLALCHEMY_DATABASE_URI = (
        os.getenv("GUIDEDTOPIC_DATABASE_URI")
        or os.getenv("DATABASE_URL")
        or f"sqlite:///{DEFAULT_DB_PATH}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    MAIL_SERVER = os.getenv("GUIDEDTOPIC_MAIL_SERVER", os.getenv("MAIL_SERVER", "smtp.googlemail.com"))
    MAIL_PORT = int(os.getenv("GUIDEDTOPIC_MAIL_PORT", os.getenv("MAIL_PORT", 587)))
    MAIL_USE_TLS = _env_bool("GUIDEDTOPIC_MAIL_USE_TLS", os.getenv("MAIL_USE_TLS", "True"))
    MAIL_USERNAME = os.getenv("GUIDEDTOPIC_MAIL_USERNAME", os.getenv("MAIL_USERNAME"))
    MAIL_PASSWORD = os.getenv("GUIDEDTOPIC_MAIL_PASSWORD", os.getenv("MAIL_PASSWORD"))
    MAIL_DEFAULT_SENDER = os.getenv("GUIDEDTOPIC_MAIL_DEFAULT_SENDER", MAIL_USERNAME)

    AWS_REGION = os.getenv("GUIDEDTOPIC_AWS_REGION", os.getenv("AWS_REGION"))
    AWS_S3_BUCKET = (
        os.getenv("GUIDEDTOPIC_S3_BUCKET")
        or os.getenv("GUIDEDTOPIC_AWS_S3_BUCKET")
        or os.getenv("AWS_S3_BUCKET")
    )

    STREAMING_TEMPLATE = os.getenv("GUIDEDTOPIC_STREAMING_TEMPLATE")

    SUPPORT_RECIPIENTS = [
        addr.strip()
        for addr in os.getenv("GUIDEDTOPIC_SUPPORT_RECIPIENTS", "").split(",")
        if addr.strip()
    ]

    WELCOME_VIDEO_URL = os.getenv("GUIDEDTOPIC_WELCOME_VIDEO_URL")

    MAX_CONTENT_LENGTH = int(
        os.getenv("GUIDEDTOPIC_MAX_CONTENT_LENGTH", str(500 * 1024 * 1024))
    )
    UPLOAD_ALLOWED_EXTENSIONS = {
        ext.strip().lower()
        for ext in os.getenv("GUIDEDTOPIC_ALLOWED_EXTENSIONS", "mp4,m4v,mov").split(",")
        if ext.strip()
    }


def configure_logging() -> Dict[str, Any]:
    """Return a dictConfig structure based on environment log-level overrides."""

    level = os.getenv("GUIDEDTOPIC_LOG_LEVEL", os.getenv("LOG_LEVEL", "INFO")).upper()
    return {
        "version": 1,
        "formatters": {
            "default": {
                "format": "[%(asctime)s] %(levelname)s in %(module)s: %(message)s",
            }
        },
        "handlers": {
            "wsgi": {
                "class": "logging.StreamHandler",
                "stream": "ext://flask.logging.wsgi_errors_stream",
                "formatter": "default",
            }
        },
        "root": {
            "level": level,
            "handlers": ["wsgi"],
        },
    }
