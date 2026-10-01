"""Server-issued, HMAC-signed session tokens.

Clients never choose their own session ids: the API issues a random id together with an
HMAC signature, and only ids carrying a valid signature are accepted. This prevents clients
from addressing arbitrary cache keys or guessing/forging other users' sessions.
"""
import hashlib
import hmac
import re
import uuid

_TOKEN_PATTERN = re.compile(r"^([0-9a-f]{32})\.([0-9a-f]{64})$")


def _sign(session_id: str, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), session_id.encode("utf-8"), hashlib.sha256).hexdigest()


def issue_session_token(secret: str) -> str:
    """Create a new random session id and return it as a signed token."""
    if not secret:
        raise ValueError("A session secret is required")
    session_id: str = uuid.uuid4().hex
    return f"{session_id}.{_sign(session_id, secret)}"


def verify_session_token(token: object, secret: str) -> str | None:
    """Return the session id if the token is well formed and correctly signed, otherwise None."""
    if not secret or not isinstance(token, str):
        return None
    match = _TOKEN_PATTERN.match(token)
    if match is None:
        return None
    session_id, signature = match.groups()
    if not hmac.compare_digest(signature, _sign(session_id, secret)):
        return None
    return session_id
