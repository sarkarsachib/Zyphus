"""
Where the agent's outward-facing capabilities are configured.

One JSON file (`devmind/agent/config.json`) describes what the agent can talk
to: model endpoints, custom APIs and connectors. It never holds a secret value -
only the *name* of the environment variable that carries one - so the file is
safe to keep in the repository while the credentials themselves stay in the
platform's env file (`/run/base44/app.env`).

Stdlib only, and every write is a plain JSON dump, so a human can edit the file
by hand just as well as the agent can edit it with a tool.
"""

import json
import os
from typing import Any, Dict, List, Optional

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIG_PATH = os.path.join(REPO_ROOT, "devmind", "agent", "config.json")

DEFAULT_API_KEY_ENV = "OPENAI_API_KEY"

# Env var each connector kind reads when the caller does not name one.
DEFAULT_CONNECTOR_ENVS = {
    "github": "GITHUB_TOKEN",
    "slack": "SLACK_WEBHOOK_URL",
    "webhook": "",
    "http": "",
}

CONNECTOR_KINDS = ("webhook", "slack", "github", "http")


def _blank() -> Dict[str, Any]:
    return {"models": [], "active_model": "", "apis": {}, "connectors": {}}


def load() -> Dict[str, Any]:
    """The stored configuration, with missing sections filled in."""
    data = _blank()
    if not os.path.isfile(CONFIG_PATH):
        return data
    try:
        with open(CONFIG_PATH, encoding="utf-8") as handle:
            stored = json.load(handle)
    except (OSError, ValueError):
        return data
    if isinstance(stored, dict):
        for key, default in data.items():
            value = stored.get(key)
            if isinstance(value, type(default)):
                data[key] = value
    return data


def save(data: Dict[str, Any]) -> str:
    """Write the configuration back to disk and return its path."""
    parent = os.path.dirname(CONFIG_PATH)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return CONFIG_PATH


def env_value(name: str) -> str:
    """The value of an environment variable, or "" when it is not set."""
    return (os.environ.get(name or "") or "").strip()


def env_present(name: str) -> bool:
    return bool(env_value(name))


# --- model endpoints ---------------------------------------------------------


def models() -> List[Dict[str, Any]]:
    return load()["models"]


def model_entry(name: str) -> Optional[Dict[str, Any]]:
    for entry in models():
        if entry.get("name") == name:
            return entry
    return None


def active_model() -> Optional[Dict[str, Any]]:
    """The model endpoint the brain should use, if one is configured."""
    return model_entry(load().get("active_model") or "")


def upsert_model(name: str, base_url: str = "", model: str = "",
                 api_key_env: str = DEFAULT_API_KEY_ENV, provider: str = "openai",
                 set_active: bool = True) -> Dict[str, Any]:
    """Add or update a model endpoint; the newest one becomes active by default."""
    data = load()
    entry = {
        "name": name,
        "provider": provider or "openai",
        "base_url": base_url.rstrip("/"),
        "model": model,
        "api_key_env": api_key_env or DEFAULT_API_KEY_ENV,
    }
    data["models"] = [existing for existing in data["models"] if existing.get("name") != name]
    data["models"].append(entry)
    if set_active or not data.get("active_model"):
        data["active_model"] = name
    save(data)
    return entry


def set_active_model(name: str) -> bool:
    data = load()
    if not any(entry.get("name") == name for entry in data["models"]):
        return False
    data["active_model"] = name
    save(data)
    return True


def remove_model(name: str) -> bool:
    data = load()
    remaining = [entry for entry in data["models"] if entry.get("name") != name]
    if len(remaining) == len(data["models"]):
        return False
    data["models"] = remaining
    if data.get("active_model") == name:
        data["active_model"] = remaining[0]["name"] if remaining else ""
    save(data)
    return True


# --- custom APIs -------------------------------------------------------------


def apis() -> Dict[str, Dict[str, Any]]:
    return load()["apis"]


def api_entry(name: str) -> Optional[Dict[str, Any]]:
    return apis().get(name)


def upsert_api(name: str, base_url: str = "", description: str = "",
               auth_env: str = "", headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    data = load()
    entry = {
        "name": name,
        "base_url": (base_url or "").rstrip("/"),
        "description": description,
        "auth_env": auth_env,
        "headers": headers or {},
    }
    data["apis"][name] = entry
    save(data)
    return entry


def remove_api(name: str) -> bool:
    data = load()
    if name not in data["apis"]:
        return False
    del data["apis"][name]
    save(data)
    return True


# --- connectors --------------------------------------------------------------


def connectors() -> Dict[str, Dict[str, Any]]:
    return load()["connectors"]


def connector_entry(name: str) -> Optional[Dict[str, Any]]:
    return connectors().get(name)


def upsert_connector(name: str, kind: str = "webhook", url: str = "", description: str = "",
                     auth_env: str = "", headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    kind = (kind or "webhook").strip().lower()
    if kind not in CONNECTOR_KINDS:
        raise ValueError(f"unknown connector kind {kind!r}; use one of {', '.join(CONNECTOR_KINDS)}")
    data = load()
    entry = {
        "name": name,
        "kind": kind,
        "url": url,
        "description": description,
        "auth_env": auth_env if auth_env else DEFAULT_CONNECTOR_ENVS.get(kind, ""),
        "headers": headers or {},
    }
    data["connectors"][name] = entry
    save(data)
    return entry


def remove_connector(name: str) -> bool:
    data = load()
    if name not in data["connectors"]:
        return False
    del data["connectors"][name]
    save(data)
    return True
