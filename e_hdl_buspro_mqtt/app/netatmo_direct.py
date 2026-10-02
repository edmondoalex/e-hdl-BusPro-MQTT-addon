from __future__ import annotations

import json
import os
import secrets
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


AUTHORIZE_URL = "https://api.netatmo.com/oauth2/authorize"
TOKEN_URL = "https://api.netatmo.com/oauth2/token"
SCOPES = " ".join((
    "read_bfi", "write_bfi", "read_bubendorff", "write_bubendorff",
    "read_mhs1", "write_mhs1", "read_mx", "write_mx",
    "read_smarther", "write_smarther", "read_thermostat", "write_thermostat",
    "read_station", "read_homecoach",
))


class NetatmoDirect:
    def __init__(self, path: str = "/data/netatmo_direct.json") -> None:
        self.path = Path(path)

    def _load(self) -> dict[str, Any]:
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {}
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return {}

    def _save(self, value: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
        try:
            os.chmod(temp, 0o600)
        except OSError:
            pass
        os.replace(temp, self.path)

    def status(self) -> dict[str, Any]:
        data = self._load()
        return {
            "credentials_configured": bool(data.get("client_id") and data.get("client_secret")),
            "connected": bool(data.get("refresh_token")),
            "authorized_at": data.get("authorized_at"),
            "error": data.get("error"),
        }

    def save_credentials(self, client_id: str, client_secret: str) -> None:
        data = self._load()
        data.update({"client_id": client_id, "client_secret": client_secret})
        for key in ("access_token", "refresh_token", "expires_at", "oauth_state", "oauth_state_expires", "error"):
            data.pop(key, None)
        self._save(data)

    def begin(self, redirect_uri: str) -> str:
        data = self._load()
        if not data.get("client_id") or not data.get("client_secret"):
            raise ValueError("Credenziali Netatmo non configurate")
        state = secrets.token_urlsafe(32)
        data.update({"oauth_state": state, "oauth_state_expires": time.time() + 900, "redirect_uri": redirect_uri})
        self._save(data)
        query = urllib.parse.urlencode({
            "client_id": data["client_id"], "redirect_uri": redirect_uri,
            "response_type": "code", "scope": SCOPES, "state": state,
        })
        return f"{AUTHORIZE_URL}?{query}"

    def complete(self, *, code: str, state: str) -> None:
        data = self._load()
        if not state or not secrets.compare_digest(state, str(data.get("oauth_state") or "")):
            raise ValueError("Stato autorizzazione non valido")
        if float(data.get("oauth_state_expires") or 0) < time.time():
            raise ValueError("Autorizzazione scaduta: ripetere il collegamento")
        body = urllib.parse.urlencode({
            "grant_type": "authorization_code", "client_id": data["client_id"],
            "client_secret": data["client_secret"], "code": code,
            "redirect_uri": data["redirect_uri"], "scope": SCOPES,
        }).encode()
        request = urllib.request.Request(TOKEN_URL, data=body, headers={"Content-Type": "application/x-www-form-urlencoded"})
        with urllib.request.urlopen(request, timeout=30) as response:
            tokens = json.loads(response.read().decode("utf-8"))
        if not tokens.get("access_token") or not tokens.get("refresh_token"):
            raise ValueError("Netatmo non ha restituito token validi")
        data.update({
            "access_token": tokens["access_token"], "refresh_token": tokens["refresh_token"],
            "expires_at": time.time() + int(tokens.get("expires_in") or 10800) - 60,
            "authorized_at": int(time.time()), "error": None,
        })
        data.pop("oauth_state", None)
        data.pop("oauth_state_expires", None)
        self._save(data)

    def disconnect(self) -> None:
        data = self._load()
        for key in ("access_token", "refresh_token", "expires_at", "authorized_at", "oauth_state", "oauth_state_expires"):
            data.pop(key, None)
        self._save(data)
