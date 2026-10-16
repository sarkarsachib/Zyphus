"""
Custom APIs and connectors: the agent's way into the rest of the world.

Two shapes of integration, both configured at runtime by the agent itself:

- a **custom API** is an endpoint registry entry (name, base URL, default
  headers, and the *name* of the env var holding its key) that the agent can
  then call by name instead of repeating a full URL and hand-built headers;
- a **connector** is a named, typed integration with a service - a webhook, a
  Slack channel, GitHub, or generic HTTP - with actions to probe it and to send
  a message through it.

Credentials are never stored: only the env var name is, and the value is read
from the process environment (the platform's env file) at call time. Nothing
here is allow-listed - any host, any method - the same full-access rule the rest
of the tool layer follows.
"""

import json
from typing import Any, Dict, List

from src.agent import config
from src.agent.tools import http_request

GITHUB_API = "https://api.github.com"


def _as_headers(raw: Any) -> Dict[str, str]:
    """Accept headers as a dict or a JSON object string; tolerate neither."""
    if isinstance(raw, dict):
        return {str(k): str(v) for k, v in raw.items()}
    if isinstance(raw, str) and raw.strip():
        try:
            parsed = json.loads(raw)
        except ValueError:
            return {}
        if isinstance(parsed, dict):
            return {str(k): str(v) for k, v in parsed.items()}
    return {}


def _auth_headers(entry: Dict[str, Any], kind: str = "api") -> Dict[str, str]:
    """Bearer / webhook / X-API-Key header for a registry entry, if its key is set."""
    name = entry.get("auth_env") or ""
    value = config.env_value(name)
    if not value:
        return {}
    if kind == "connector" and entry.get("kind") in ("webhook", "slack"):
        return {}  # the webhook URL itself is the credential
    return {"Authorization": f"Bearer {value}", "X-API-Key": value}


def _join(base: str, path: str) -> str:
    if not base:
        return path
    if not path:
        return base
    if path.startswith("http://") or path.startswith("https://"):
        return path
    return f"{base.rstrip('/')}/{path.lstrip('/')}"


# --- custom APIs -------------------------------------------------------------


def api_names() -> List[Dict[str, Any]]:
    return [
        {**entry, "key_env": entry.get("auth_env", ""),
         "key_present": config.env_present(entry.get("auth_env", ""))}
        for entry in sorted(config.apis().values(), key=lambda e: e.get("name", ""))
    ]


def api(action: str = "list", name: str = "", base_url: str = "", path: str = "",
        method: str = "GET", body: str = "", headers: Any = None,
        auth_env: str = "", description: str = "") -> Dict[str, Any]:
    """List, register, remove or call a custom API endpoint."""
    action = (action or "list").strip().lower()

    if action in ("list", "ls"):
        return {"apis": api_names(), "registry": config.CONFIG_PATH}

    if action in ("register", "add", "set"):
        if not name:
            return {"error": "register requires a name"}
        entry = config.upsert_api(name, base_url=base_url, description=description,
                                  auth_env=auth_env, headers=_as_headers(headers))
        return {"registered": entry, "key_present": config.env_present(entry.get("auth_env", "")),
                "registry": config.CONFIG_PATH}

    if action in ("remove", "delete", "forget"):
        return {"removed": config.remove_api(name)} if name else {"error": "remove requires a name"}

    if action in ("call", "request", "invoke"):
        entry = config.api_entry(name)
        if entry is None:
            return {"error": f"no registered API named {name!r} - register it first",
                    "known": [e["name"] for e in api_names()]}
        if not path and not entry.get("base_url"):
            return {"error": "call requires a path (or a base_url on the registered API)"}
        url = _join(entry.get("base_url", ""), path)
        merged = {**entry.get("headers", {}), **_as_headers(headers)}
        for key, value in _auth_headers(entry).items():
            merged.setdefault(key, value)
        result = http_request(url, method=method, headers=merged, body=body or None)
        return {"ok": result.ok, "status": result.meta.get("status"),
                "output": result.output, "error": result.error,
                "auth_used": bool(config.env_present(entry.get("auth_env", ""))), "url": url}

    return {"error": f"unknown action {action!r}; use list, register, remove or call"}


# --- connectors --------------------------------------------------------------


def connector_names() -> List[Dict[str, Any]]:
    return [
        {**entry, "key_env": entry.get("auth_env", ""),
         "key_present": config.env_present(entry.get("auth_env", "")),
         "ready": bool(entry.get("url")) or config.env_present(entry.get("auth_env", ""))}
        for entry in sorted(config.connectors().values(), key=lambda e: e.get("name", ""))
    ]


def connector(action: str = "list", name: str = "", kind: str = "", url: str = "",
              auth_env: str = "", description: str = "", message: str = "",
              payload: str = "", path: str = "") -> Dict[str, Any]:
    """List, add, remove, probe or send through a connector."""
    action = (action or "list").strip().lower()

    if action in ("list", "ls"):
        return {"connectors": connector_names(), "registry": config.CONFIG_PATH}

    if action in ("add", "register", "set"):
        if not name:
            return {"error": "add requires a name"}
        try:
            entry = config.upsert_connector(name, kind=kind or "webhook", url=url,
                                            description=description, auth_env=auth_env,
                                            headers=None)
        except ValueError as exc:
            return {"error": str(exc), "kinds": list(config.CONNECTOR_KINDS)}
        return {"added": entry, "key_present": config.env_present(entry.get("auth_env", "")),
                "registry": config.CONFIG_PATH}

    if action in ("remove", "delete", "forget"):
        return {"removed": config.remove_connector(name)} if name else {"error": "remove requires a name"}

    entry = config.connector_entry(name) if name else None
    if entry is None:
        return {"error": f"no connector named {name!r} - add it first",
                "known": [e["name"] for e in connector_names()]}

    if action in ("test", "probe", "check"):
        return _connector_test(entry, path)

    if action in ("send", "post", "notify"):
        return _connector_send(entry, message, payload, path)

    return {"error": f"unknown action {action!r}; use list, add, remove, test or send"}


def _connector_url(entry: Dict[str, Any]) -> str:
    url = entry.get("url") or ""
    if not url and entry.get("kind") in ("webhook", "slack"):
        url = config.env_value(entry.get("auth_env", ""))
    if not url and entry.get("kind") == "github":
        url = GITHUB_API
    return url


def _connector_test(entry: Dict[str, Any], path: str = "") -> Dict[str, Any]:
    """Probe a connector without sending anything it would act on."""
    kind = entry.get("kind")
    url = _connector_url(entry)
    if kind == "github":
        probe = _join(url or GITHUB_API, path or ("/user" if config.env_present(entry.get("auth_env", ""))
                                                  else "/rate_limit"))
    else:
        probe = _join(url, path)
    if not probe:
        return {"ok": False, "error": f"connector {entry.get('name')!r} has no url and no "
                                      f"{entry.get('auth_env') or 'key'} set"}

    headers = dict(entry.get("headers", {}))
    key = config.env_value(entry.get("auth_env", ""))
    if kind == "github" and key:
        headers.setdefault("Authorization", f"Bearer {key}")
        headers.setdefault("Accept", "application/vnd.github+json")
    headers.setdefault("User-Agent", "zyphus-agent")

    result = http_request(probe, method="GET", headers=headers)
    reachable = result.meta.get("status") is not None
    return {"ok": reachable, "kind": kind, "url": probe,
            "status": result.meta.get("status"),
            "note": "reachable" if reachable else (result.error or "unreachable"),
            "sample": (result.output or "")[:400]}


def _connector_send(entry: Dict[str, Any], message: str, payload: str = "",
                    path: str = "") -> Dict[str, Any]:
    kind = entry.get("kind")
    url = _connector_url(entry)
    key = config.env_value(entry.get("auth_env", ""))
    headers = dict(entry.get("headers", {}))

    if kind == "github":
        if not key:
            return {"ok": False, "error": f"github connector needs {entry.get('auth_env')} set"}
        headers.setdefault("Authorization", f"Bearer {key}")
        headers.setdefault("Accept", "application/vnd.github+json")
        headers.setdefault("User-Agent", "zyphus-agent")
        result = http_request(_join(url or GITHUB_API, path or "/user"), method="GET", headers=headers)
        return {"ok": result.ok, "url": result.meta.get("url"), "status": result.meta.get("status"),
                "output": result.output, "error": result.error}

    if not url:
        return {"ok": False, "error": f"connector {entry.get('name')!r} has no url and no "
                                      f"{entry.get('auth_env') or 'key'} set"}

    if payload:
        body = payload
    elif kind in ("slack", "webhook"):
        body = json.dumps({"text": message or "(zyphus has nothing to say)"})
    else:
        body = json.dumps({"message": message, "source": "zyphus"})

    headers.setdefault("Content-Type", "application/json")
    headers.setdefault("User-Agent", "zyphus-agent")
    result = http_request(url, method="POST", headers=headers, body=body)
    return {"ok": result.ok, "kind": kind, "url": url, "status": result.meta.get("status"),
            "output": result.output, "error": result.error}


# --- models ------------------------------------------------------------------


def models() -> List[Dict[str, Any]]:
    active = config.load().get("active_model") or ""
    entries = []
    for entry in config.models():
        entries.append({**entry, "active": entry.get("name") == active,
                        "key_env": entry.get("api_key_env", ""),
                        "key_present": config.env_present(entry.get("api_key_env", ""))})
    return entries


def model(action: str = "list", name: str = "", base_url: str = "", model: str = "",
          api_key_env: str = config.DEFAULT_API_KEY_ENV, provider: str = "openai") -> Dict[str, Any]:
    """Configure and probe the model endpoints the brain may plan with."""
    action = (action or "list").strip().lower()

    if action in ("list", "ls", "status"):
        return {"models": models(), "active": config.load().get("active_model") or None,
                "registry": config.CONFIG_PATH,
                "env_defaults": {"OPENAI_API_KEY": config.env_present("OPENAI_API_KEY"),
                                 "ZYPHUS_MODEL": config.env_value("ZYPHUS_MODEL") or None,
                                 "ZYPHUS_MODEL_BASE_URL": config.env_value("ZYPHUS_MODEL_BASE_URL") or None}}

    if action in ("add", "set", "register", "configure"):
        if not name:
            return {"error": "add requires a name"}
        entry = config.upsert_model(name, base_url=base_url, model=model,
                                    api_key_env=api_key_env, provider=provider, set_active=True)
        return {"configured": entry, "key_present": config.env_present(entry["api_key_env"]),
                "active": entry["name"], "registry": config.CONFIG_PATH}

    if action in ("use", "activate", "switch"):
        if not config.set_active_model(name):
            return {"error": f"no configured model named {name!r}"}
        return {"active": name}

    if action in ("remove", "delete"):
        return {"removed": config.remove_model(name)} if name else {"error": "remove requires a name"}

    if action in ("test", "probe", "check"):
        from src.agent.model_brain import ModelBrain

        entry = config.model_entry(name) if name else config.active_model()
        if entry is None:
            return {"error": f"no configured model named {name!r}", "models": [m["name"] for m in models()]}
        brain = ModelBrain(fallback=None, base_url=entry.get("base_url"), model=entry.get("model"),
                           api_key_env=entry.get("api_key_env") or config.DEFAULT_API_KEY_ENV)
        if not brain.available():
            return {"ok": False, "model": entry, "error": f"{brain.api_key_env} is not set"}
        try:
            reply = brain._chat([{"role": "user", "content": "Reply with the single word: ready"}])
        except Exception as exc:
            return {"ok": False, "model": entry, "error": f"{type(exc).__name__}: {exc}"}
        return {"ok": True, "model": entry, "reply": (reply or "").strip()[:200]}

    return {"error": f"unknown action {action!r}; use list, add, use, remove or test"}
