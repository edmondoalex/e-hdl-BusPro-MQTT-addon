from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Literal

AUTH_NONE = "none"
AUTH_TOKEN = "token"
AUTH_BASIC = "basic"

AuthMode = Literal["none", "token", "basic"]


@dataclass(frozen=True)
class AuthConfig:
    mode: AuthMode
    token: str
    username: str
    password: str


@dataclass(frozen=True)
class MqttConfig:
    host: str
    port: int
    username: str
    password: str
    base_topic: str
    discovery_prefix: str
    client_id: str


@dataclass(frozen=True)
class GatewayConfig:
    host: str
    port: int
    local_ip: str


@dataclass(frozen=True)
class Settings:
    gateway: GatewayConfig
    mqtt: MqttConfig
    auth: AuthConfig
    user_auth: AuthConfig
    poll_interval_s: float
    poll_pace_s: float
    ha_poll_interval_s: float
    light_cmd_interval_s: float
    udp_send_interval_s: float
    debug: bool
    debug_telegram: bool


def read_options() -> dict[str, Any]:
    path = os.environ.get("BUSPRO_OPTIONS", "/data/options.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def load_settings(options: dict[str, Any]) -> Settings:
    gw = options.get("gateway_host") or "127.0.0.1"
    gw_port = int(options.get("gateway_port") or 6000)
    gw_local_ip = str(options.get("gateway_local_ip") or "").strip()

    def _read_float(key: str, default: float) -> float:
        try:
            v = options.get(key)
            if v is None:
                return float(default)
            return float(v)
        except Exception:
            return float(default)

    auth_raw = options.get("auth") or {}
    mode = (auth_raw.get("mode") or AUTH_TOKEN).strip().lower()
    if mode not in (AUTH_NONE, AUTH_TOKEN, AUTH_BASIC):
        mode = AUTH_TOKEN

    # fallback to none if credentials missing
    if mode == AUTH_TOKEN and not str(auth_raw.get("token") or ""):
        mode = AUTH_NONE
    if mode == AUTH_BASIC and (not str(auth_raw.get("username") or "") or not str(auth_raw.get("password") or "")):
        mode = AUTH_NONE
    auth = AuthConfig(
        mode=mode,  # type: ignore[arg-type]
        token=str(auth_raw.get("token") or ""),
        username=str(auth_raw.get("username") or ""),
        password=str(auth_raw.get("password") or ""),
    )

    user_auth_raw = options.get("user_auth") or {}
    user_mode = (user_auth_raw.get("mode") or AUTH_NONE).strip().lower()
    if user_mode not in (AUTH_NONE, AUTH_TOKEN, AUTH_BASIC):
        user_mode = AUTH_NONE
    if user_mode == AUTH_TOKEN and not str(user_auth_raw.get("token") or ""):
        user_mode = AUTH_NONE
    if user_mode == AUTH_BASIC and (
        not str(user_auth_raw.get("username") or "") or not str(user_auth_raw.get("password") or "")
    ):
        user_mode = AUTH_NONE
    user_auth = AuthConfig(
        mode=user_mode,  # type: ignore[arg-type]
        token=str(user_auth_raw.get("token") or ""),
        username=str(user_auth_raw.get("username") or ""),
        password=str(user_auth_raw.get("password") or ""),
    )

    mqtt_raw = options.get("mqtt") or {}
    mqtt = MqttConfig(
        host=str(mqtt_raw.get("host") or "core-mosquitto"),
        port=int(mqtt_raw.get("port") or 1883),
        username=str(mqtt_raw.get("username") or ""),
        password=str(mqtt_raw.get("password") or ""),
        base_topic=str(mqtt_raw.get("base_topic") or "buspro").rstrip("/"),
        discovery_prefix=str(mqtt_raw.get("discovery_prefix") or "homeassistant").rstrip("/"),
        client_id=str(mqtt_raw.get("client_id") or "buspro-addon"),
    )

    poll_interval_s = max(0.0, _read_float("poll_interval_s", 180.0))
    poll_pace_s = max(0.0, _read_float("poll_pace_s", 0.15))
    ha_poll_interval_s = max(0.5, _read_float("ha_poll_interval_s", 2.0))
    light_cmd_interval_s = max(0.0, _read_float("light_cmd_interval_s", 0.12))
    udp_send_interval_s = max(0.0, _read_float("udp_send_interval_s", 0.0))

    return Settings(
        gateway=GatewayConfig(host=str(gw), port=gw_port, local_ip=gw_local_ip),
        mqtt=mqtt,
        auth=auth,
        user_auth=user_auth,
        poll_interval_s=poll_interval_s,
        poll_pace_s=poll_pace_s,
        ha_poll_interval_s=ha_poll_interval_s,
        light_cmd_interval_s=light_cmd_interval_s,
        udp_send_interval_s=udp_send_interval_s,
        debug=bool(options.get("debug") or False),
        debug_telegram=bool(options.get("debug_telegram") or False),
    )
