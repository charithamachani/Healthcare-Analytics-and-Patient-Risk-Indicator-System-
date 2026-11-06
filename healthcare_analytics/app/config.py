"""Configuration loaded from environment variables (see .env.example)."""
import os

from dotenv import load_dotenv

load_dotenv()

VALID_ROLES = {"analyst", "admin"}


def parse_api_keys(raw: str) -> dict:
    """'analyst=abc,admin=xyz' -> {'abc': 'analyst', 'xyz': 'admin'} (key -> role)."""
    keys = {}
    for part in (raw or "").split(","):
        if "=" not in part:
            continue
        role, key = part.split("=", 1)
        role, key = role.strip(), key.strip()
        if role in VALID_ROLES and key:
            keys[key] = role
    return keys


def default_database_url() -> str:
    return os.environ.get(
        "DATABASE_URL",
        "mysql+pymysql://health_user:CHANGE_ME@localhost:3306/health_analytics",
    )
