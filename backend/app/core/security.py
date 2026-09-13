import hashlib
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config.settings import settings

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

PASSWORD_RESET_EXPIRATION_SECONDS = 30 * 60


def hash_password(password: str) -> str:
    return _pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _pwd_context.verify(password, password_hash)


def _password_fingerprint(password_hash: str) -> str:
    return hashlib.sha256(password_hash.encode()).hexdigest()[:16]


def verify_password_reset_fingerprint(fingerprint: str, password_hash: str) -> bool:
    return fingerprint == _password_fingerprint(password_hash)


def _create_token(
    subject: str, scope: str, expiration_seconds: int, extra_claims: dict | None = None
) -> str:
    expire = datetime.now(timezone.utc) + timedelta(seconds=expiration_seconds)
    payload = {"sub": subject, "scope": scope, "exp": expire, **(extra_claims or {})}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def _decode_token(token: str, expected_scope: str) -> dict | None:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        return None

    if payload.get("scope") != expected_scope:
        return None

    return payload


def create_access_token(subject: str) -> str:
    return _create_token(subject, scope="access", expiration_seconds=settings.JWT_EXPIRATION)


def decode_access_token(token: str) -> str | None:
    payload = _decode_token(token, expected_scope="access")
    return payload.get("sub") if payload else None


def create_password_reset_token(subject: str, password_hash: str) -> str:
    return _create_token(
        subject,
        scope="password_reset",
        expiration_seconds=PASSWORD_RESET_EXPIRATION_SECONDS,
        extra_claims={"pwf": _password_fingerprint(password_hash)},
    )


def decode_password_reset_token(token: str) -> dict | None:
    return _decode_token(token, expected_scope="password_reset")
