"""Password hashing and JWT access tokens."""

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from .config import settings

ALGORITHM = "HS256"

# bcrypt only looks at the first 72 bytes, so longer passwords are rejected up front
# (see schemas.py) rather than being silently truncated.
MAX_PASSWORD_BYTES = 72

# Used to keep login timing similar whether or not the email exists.
_DUMMY_HASH = bcrypt.hashpw(b"not-a-real-password", bcrypt.gensalt()).decode()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str | None) -> bool:
    """Check a password. Pass None for an unknown user to burn equivalent time."""
    candidate = password_hash or _DUMMY_HASH
    try:
        ok = bcrypt.checkpw(password.encode("utf-8")[:MAX_PASSWORD_BYTES], candidate.encode("utf-8"))
    except ValueError:
        return False
    return ok and password_hash is not None


def create_access_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> int:
    """Return the user id from a valid token, or raise jwt.PyJWTError / ValueError."""
    payload = jwt.decode(
        token, settings.secret_key, algorithms=[ALGORITHM], options={"require": ["exp", "sub"]}
    )
    return int(payload["sub"])
