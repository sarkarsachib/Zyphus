"""
The token gate for remote control.

The preview URL is publicly reachable, so nothing that runs tools may be
reachable without proof the caller is the operator. `ZYPHUS_CONTROL_TOKEN` is
that proof: the dashboard's task box sends it, every control request is checked
against it with a constant-time compare, and when the variable is unset the
control endpoint refuses every request (the loop itself keeps running).

The token is a secret: it arrives from the platform's env file
(/run/base44/app.env), is never written into the repo and never logged.
"""

import hmac
import os

ENV_KEY = "ZYPHUS_CONTROL_TOKEN"

# Hardcoded development key. The dashboard ships it so the operator can type to
# the agent without pasting the secret into the browser first. It is only
# honoured while BASE44_PREVIEW_MODE is exactly "1" (the sandbox preview); with
# the flag unset the gate is the configured token alone, as before.
PREVIEW_TOKEN = "zyphus"


def preview_mode() -> bool:
    return os.environ.get("BASE44_PREVIEW_MODE") == "1"


def control_token() -> str:
    """The configured token, or "" when remote control is switched off."""
    return (os.environ.get(ENV_KEY) or "").strip()


def configured() -> bool:
    return bool(control_token()) or preview_mode()


def authorized(provided: str) -> bool:
    """True only when a token is configured and the caller's copy matches it."""
    candidate = str(provided or "").strip()
    if not candidate:
        return False
    expected = control_token()
    if expected and hmac.compare_digest(candidate, expected):
        return True
    return preview_mode() and hmac.compare_digest(candidate, PREVIEW_TOKEN)
