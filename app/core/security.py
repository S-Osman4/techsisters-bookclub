# app/core/security.py
import logging
from itsdangerous import TimestampSigner, SignatureExpired, BadSignature
import bcrypt

from app.core.config import settings

logger = logging.getLogger(__name__)


# ── Password hashing ─────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    """
    Hash a plain-text password using bcrypt.
    Returns the hash as a UTF-8 string suitable for DB storage.
    """
    return bcrypt.hashpw(
        plain.encode("utf-8"),
        bcrypt.gensalt(),
    ).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """
    Verify a plain-text password against a stored bcrypt hash.
    Returns False on any error rather than raising.
    """
    try:
        return bcrypt.checkpw(
            plain.encode("utf-8"),
            hashed.encode("utf-8"),
        )
    except Exception:
        logger.warning("Password verification error — malformed hash or input")
        return False


# ── CSRF tokens ───────────────────────────────────────────────────────────────

def _get_signer() -> TimestampSigner:
    return TimestampSigner(settings.SECRET_KEY, salt="csrf")


def generate_csrf_token(session_id: str) -> str:
    """
    Generate a signed CSRF token bound to the given session ID.
    The token is signed with a timestamp so it expires after
    settings.CSRF_TOKEN_MAX_AGE seconds.

    The session_id is included as the value so the token cannot
    be reused across sessions.
    """
    signer = _get_signer()
    return signer.sign(session_id).decode("utf-8")


def verify_csrf_token(token: str, session_id: str) -> bool:
    """
    Verify a CSRF token against the current session ID.

    Returns True only if:
    - The signature is valid
    - The token has not expired
    - The embedded value matches the current session_id
    """
    if not token or not session_id:
        return False

    signer = _get_signer()
    try:
        value = signer.unsign(
            token,
            max_age=settings.CSRF_TOKEN_MAX_AGE,
        ).decode("utf-8")
        return value == session_id
    except SignatureExpired:
        logger.warning("CSRF token expired")
        return False
    except BadSignature:
        logger.warning("CSRF token bad signature")
        return False
    except Exception:
        logger.warning("CSRF token verification error")
        return False