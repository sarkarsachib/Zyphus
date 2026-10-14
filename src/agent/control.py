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


def control_token() -> str:
    """The configured token, or "" when remote control is switched off."""
    return (os.environ.get(ENV_KEY) or "").strip()


def configured() -> bool:
    return bool(control_token())


def authorized(provided: str) -> bool:
    """True only when a token is configured and the caller's copy matches it."""
    expected = control_token()
    if not expected:
        return False
    return hmac.compare_digest(str(provided or "").strip(), expected)
