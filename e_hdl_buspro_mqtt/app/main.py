from __future__ import annotations

import asyncio 
import base64
import json
import logging
import os 
import struct
import time
import threading
import urllib.parse
import urllib.request
from typing import Any
import re

from fastapi import FastAPI, HTTPException, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .buspro_gateway import BusproGateway, CoverKey, CoverState, LightKey, LightState
from .discovery import (
    cover_discovery,
    cover_group_discovery,
    cover_group_no_pct_discovery,
    cover_no_pct_discovery,
    dry_contact_discovery,
    pir_discovery,
    ultrasonic_discovery,
    humidity_discovery,
    illuminance_discovery,
    air_quality_discovery,
    gas_percent_discovery,
    light_discovery,
    light_scenario_button_discovery,
    slugify,
    temperature_discovery,
)
from .icons import ensure_mdi_icons, parse_mdi_icon, placeholder_svg
from .mqtt_client import MqttClient
from .realtime import RealtimeHub
from .settings import AUTH_BASIC, AUTH_NONE, AUTH_TOKEN, AuthConfig, load_settings, read_options
from .sniffer import TelegramSniffer
from .store import StateStore

_LOGGER = logging.getLogger("buspro_addon")
logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO").upper())

ADDON_VERSION = "0.1.252"

USER_PORT = 8124
ADMIN_PORT = 8125


def _configure_logging(debug: bool, debug_telegram: bool) -> None:
    level = logging.DEBUG if debug else logging.INFO

    root = logging.getLogger()
    root.setLevel(level)

    for name in (
        "buspro_addon",
        "buspro_gateway",
        "paho",
        "uvicorn",
        "uvicorn.error",
        "uvicorn.access",
    ):
        logging.getLogger(name).setLevel(level)

    # Telegram/log dump e' molto rumoroso: abilitalo solo se richiesto esplicitamente.
    tl = logging.DEBUG if debug_telegram else (logging.INFO if debug else logging.WARNING)
    logging.getLogger("buspro.telegram").setLevel(tl)
    logging.getLogger("buspro.log").setLevel(tl)


def _normalize_ingress_base(base: str) -> str:
    base = (base or "").strip()
    if not base:
        return ""
    if not base.startswith("/"):
        base = "/" + base
    base = base.rstrip("/")
    if base.endswith("/ingress"):
        base = base[: -len("/ingress")]
    return base


def _is_ingress_headers(headers: dict[str, str]) -> bool:
    return bool(
        headers.get("x-ingress-path")
        or headers.get("x-hassio-ingress")
        or headers.get("x-hassio-key")
        or headers.get("x-forwarded-prefix")
    )


def _unauthorized(mode: str) -> Response:
    headers: dict[str, str] = {}
    if mode == AUTH_BASIC:
        headers["WWW-Authenticate"] = 'Basic realm="buspro"'
    return Response(status_code=401, headers=headers)


def _clean_backup_text(text: str) -> str:
    # Make restore more tolerant to BOM/accidental prefixes/suffixes when pasting.
    t = (text or "").strip()
    if t.startswith("\ufeff"):
        t = t.lstrip("\ufeff").strip()
    if not t:
        return ""
    if not t.lstrip().startswith("{"):
        a = t.find("{")
        b = t.rfind("}")
        if a != -1 and b != -1 and b > a:
            t = t[a : b + 1].strip()
    return t


def _check_auth_headers(headers: dict[str, str], query: dict[str, str], auth: AuthConfig) -> bool:
    if auth.mode == AUTH_NONE:
        return True

    header = headers.get("authorization")

    if auth.mode == AUTH_TOKEN:
        if not auth.token:
            return False
        if header and header.lower().startswith("bearer "):
            return header[7:].strip() == auth.token
        token_q = query.get("token")
        return bool(token_q) and token_q == auth.token

    if auth.mode == AUTH_BASIC:
        if not auth.username or not auth.password:
            return False
        if not header or not header.lower().startswith("basic "):
            return False
        try:
            raw = base64.b64decode(header[6:].strip()).decode("utf-8")
            user, pw = raw.split(":", 1)
            return user == auth.username and pw == auth.password
        except Exception:
            return False

    return False


def _parse_light_cmd(payload: str) -> tuple[bool, int | None]:
    # Returns (on, brightness255)
    s = payload.strip()
    if not s:
        raise ValueError("empty payload")

    if s[0] == "{":
        obj = json.loads(s)
        state = str(obj.get("state") or "").upper()
        on = state != "OFF"
        br = obj.get("brightness")
        if br is None:
            return on, None
        return on, int(br)

    up = s.upper()
    if up in ("ON", "OFF"):
        return up == "ON", None

    raise ValueError("unsupported payload")


def create_app() -> FastAPI: 
    api = FastAPI() 

    static_dir = os.path.join(os.path.dirname(__file__), "static")
    api.mount("/static", StaticFiles(directory=static_dir), name="static")

    def _resolve_www_dir() -> str | None:
        candidates: list[str] = []
        env = str(os.environ.get("BUSPRO_WWW") or "").strip()
        if env:
            candidates.append(env)

        here = os.path.dirname(__file__)
        candidates.extend(
            [
                os.path.abspath(os.path.join(here, "..", "www")),
                os.path.abspath(os.path.join(here, "..", "..", "www")),
                os.path.abspath(os.path.join(os.getcwd(), "www")),
                "/www",
                "/app/www",
                "/data/www",
                "/config/www",
            ]
        )

        for c in candidates:
            try:
                if c and os.path.isdir(c):
                    return c
            except Exception:
                continue
        return None

    api.state.www_dir = _resolve_www_dir()

    store = StateStore(os.environ.get("BUSPRO_STATE", "/data/state.json"))
    api.state.store = store

    icons_dir = os.environ.get("BUSPRO_ICONS", "/data/icons")
    api.state.icons_dir = icons_dir
    api.state.icon_lock = asyncio.Lock()

    hub = RealtimeHub()
    api.state.hub = hub

    options = read_options()
    settings = load_settings(options)
    api.state.settings = settings
    _configure_logging(settings.debug, settings.debug_telegram)
    # Optional: force the source IPv4 embedded in telegrams (BUSPRO_LOCAL_IP).
    try:
        if str(getattr(settings.gateway, "local_ip", "") or "").strip():
            os.environ["BUSPRO_LOCAL_IP"] = str(getattr(settings.gateway, "local_ip")).strip()
    except Exception:
        pass

    mqtt = MqttClient(
        host=settings.mqtt.host,
        port=settings.mqtt.port,
        username=settings.mqtt.username,
        password=settings.mqtt.password,
        client_id=settings.mqtt.client_id,
    )
    api.state.mqtt = mqtt

    # Home Assistant (Core) integration via Supervisor token (no user token required)
    def _ha_enabled() -> bool:
        try:
            tok = str(os.environ.get("SUPERVISOR_TOKEN") or "").strip()
            return bool(tok)
        except Exception:
            return False

    def _ha_base_url() -> str:
        # Supervisor Core proxy (works inside add-on containers)
        return "http://supervisor/core"

    def _ha_headers() -> dict[str, str]:
        tok = str(os.environ.get("SUPERVISOR_TOKEN") or "").strip()
        if not tok:
            return {}
        return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}

    def _ha_request(method: str, path: str, *, payload: dict[str, Any] | None = None, timeout_s: int = 8) -> Any:
        base = _ha_base_url().rstrip("/")
        url = base + "/" + path.lstrip("/")
        headers = _ha_headers()
        data: bytes | None = None
        if payload is not None:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(url=url, method=method.upper(), data=data)
        for k, v in headers.items():
            req.add_header(k, v)
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            raw = resp.read()
            try:
                return json.loads(raw.decode("utf-8", errors="replace"))
            except Exception:
                return raw.decode("utf-8", errors="replace")

    def _ha_state_str(v: Any) -> str:
        return str(v or "").strip().lower()

    def _ha_friendly_name(st: dict[str, Any]) -> str:
        try:
            attrs = st.get("attributes") or {}
            if isinstance(attrs, dict):
                return str(attrs.get("friendly_name") or "").strip()
        except Exception:
            return ""
        return ""

    def _ha_light_is_dimmable(st: dict[str, Any]) -> bool:
        try:
            attrs = st.get("attributes") or {}
            if not isinstance(attrs, dict):
                return False
            if attrs.get("brightness") is not None:
                return True
            scm = attrs.get("supported_color_modes")
            if isinstance(scm, list):
                modes = [str(x or "").strip().lower() for x in scm if str(x or "").strip()]
                return any(m and m != "onoff" for m in modes)
            if isinstance(scm, str):
                return scm.strip().lower() != "onoff"
        except Exception:
            return False
        return False

    def _map_ha_state_to_light(st: dict[str, Any]) -> dict[str, Any]:
        eid = str(st.get("entity_id") or "").strip().lower()
        s = _ha_state_str(st.get("state"))
        if s in ("unavailable", "unknown", ""):
            state = "?"
        else:
            state = "ON" if s == "on" else "OFF"
        attrs = st.get("attributes") or {}
        br_i: int | None = None
        if isinstance(attrs, dict) and attrs.get("brightness") is not None:
            try:
                br_i = int(attrs.get("brightness"))
            except Exception:
                br_i = None
        brightness = 0
        if state == "ON":
            brightness = max(0, min(255, br_i)) if br_i is not None else 255
        return {"entity_id": eid, "state": state, "brightness": brightness}

    def _map_ha_state_to_switch(st: dict[str, Any]) -> dict[str, Any]:
        eid = str(st.get("entity_id") or "").strip().lower()
        s = _ha_state_str(st.get("state"))
        if s in ("unavailable", "unknown", ""):
            state = "?"
        else:
            state = "ON" if s == "on" else "OFF"
        return {"entity_id": eid, "state": state}

    def _map_ha_state_to_cover(st: dict[str, Any]) -> dict[str, Any]:
        eid = str(st.get("entity_id") or "").strip().lower()
        s = _ha_state_str(st.get("state"))
        if s in ("unavailable", "unknown", ""):
            state = "?"
        elif s == "open":
            state = "OPEN"
        elif s == "closed":
            state = "CLOSED"
        elif s == "opening":
            state = "OPENING"
        elif s == "closing":
            state = "CLOSING"
        else:
            state = "STOP"
        attrs = st.get("attributes") or {}
        pos: int | None = None
        if isinstance(attrs, dict) and attrs.get("current_position") is not None:
            try:
                pos = int(attrs.get("current_position"))
                pos = max(0, min(100, pos))
            except Exception:
                pos = None
        return {"entity_id": eid, "state": state, "position": pos}

    def _list_user_devices() -> list[dict[str, Any]]:
        devices = list(store.list_devices())
        caps: dict[str, Any] = getattr(api.state, "ha_caps", {}) or {}
        ha = store.list_ha_devices()
        for it in ha:
            try:
                eid = str(it.get("entity_id") or "").strip().lower()
                if not eid or "." not in eid:
                    continue
                domain = str(it.get("domain") or eid.split(".", 1)[0]).strip().lower()
                page = str(it.get("page") or "").strip().lower() or ("covers" if domain == "cover" else "lights")
                name_override = str(it.get("name") or "").strip()
                group = str(it.get("group") or "").strip()
                icon = str(it.get("icon") or "").strip()
                cap = caps.get(eid) if isinstance(caps, dict) else None
                cap_name = str((cap or {}).get("name") or "").strip() if isinstance(cap, dict) else ""
                name = name_override or cap_name or eid

                if domain == "cover":
                    devices.append(
                        {
                            "type": "cover",
                            "origin": "ha",
                            "entity_id": eid,
                            "page": page,
                            "name": name,
                            "group": group,
                            "icon": icon,
                        }
                    )
                else:
                    is_dimmable = False
                    if domain == "light":
                        if isinstance(cap, dict) and cap.get("dimmable") is not None:
                            is_dimmable = bool(cap.get("dimmable"))
                        else:
                            is_dimmable = True
                    devices.append(
                        {
                            "type": "light",
                            "origin": "ha",
                            "entity_id": eid,
                            "domain": domain,
                            "page": page,
                            "name": name,
                            "group": group,
                            "dimmable": is_dimmable if domain == "light" else False,
                            "icon": icon,
                            "category": "switch" if domain == "switch" else "Luci",
                        }
                    )
            except Exception:
                continue
        return devices

    api.state.loop = None
    api.state.gateway = None
    api.state.sniffer = TelegramSniffer(share_dir="/share", maxlen=5000)

    @api.middleware("http")
    async def ingress_path_middleware(request: Request, call_next):
        base = request.headers.get("x-forwarded-prefix") or request.headers.get("x-ingress-path") or ""
        base = _normalize_ingress_base(base)

        if not base:
            path = request.scope.get("path") or ""
            if path.startswith("/local_"):
                seg = path.split("/", 3)
                if len(seg) > 1:
                    base = "/" + seg[1]

        if base:
            path = request.scope.get("path") or ""
            if path == base:
                request.scope["root_path"] = base
                request.scope["path"] = "/"
            elif path.startswith(base + "/"):
                request.scope["root_path"] = base
                request.scope["path"] = path[len(base):] or "/"

        # Some ingress URLs can end up with a double slash (e.g. .../hassio_ingress/<token>//).
        # Normalize repeated slashes so our routing matches "/" etc.
        try:
            p = str(request.scope.get("path") or "")
            while "//" in p:
                p = p.replace("//", "/")
            if not p.startswith("/"):
                p = "/" + p
            request.scope["path"] = p
        except Exception:
            pass

        return await call_next(request)

    @api.middleware("http")
    async def auth_middleware(request: Request, call_next):
        if request.url.path in ("/health",):
            return await call_next(request)

        options_ = read_options()
        settings_ = load_settings(options_)
        headers = {k.lower(): v for k, v in request.headers.items()}
        query = dict(request.query_params)
        port = None
        try:
            port = int((request.scope.get("server") or ("", 0))[1])
        except Exception:
            port = None

        # User port: allow ingress bypass and use user_auth
        if port == USER_PORT:
            if _is_ingress_headers(headers):
                return await call_next(request)
            if not _check_auth_headers(headers, query, settings_.user_auth):
                return _unauthorized(settings_.user_auth.mode)
            return await call_next(request)

        # Admin port: always enforce auth (no ingress bypass)
        if not _check_auth_headers(headers, query, settings_.auth):
            return _unauthorized(settings_.auth.mode)

        return await call_next(request)

    @api.middleware("http")
    async def port_gate_middleware(request: Request, call_next):
        # Block admin-only endpoints on USER_PORT.
        try:
            port = int((request.scope.get("server") or ("", 0))[1])
        except Exception:
            port = None
        if port != USER_PORT:
            return await call_next(request)

        # When opened via Home Assistant Ingress, allow full UI/API access on USER_PORT.
        try:
            headers = {k.lower(): v for k, v in request.headers.items()}
            if _is_ingress_headers(headers):
                return await call_next(request)
        except Exception:
            pass
        try:
            if str(request.cookies.get("buspro_ingress") or "") == "1":
                return await call_next(request)
        except Exception:
            pass

        path = request.url.path or "/"
        if path in ("/health", "/ws", "/favicon.ico") or path.startswith("/static/"):
            return await call_next(request)
        if path in ("/manifest.webmanifest", "/sw.js"):
            return await call_next(request)
        if path.startswith("/www/"):
            return await call_next(request)
        if path.startswith("/ext/"):
            return await call_next(request)
        if path.startswith("/extws/"):
            return await call_next(request)

        # User pages
        if path in ("/", "/home", "/home2", "/lights", "/covers", "/extra", "/scenarios"): 
            return await call_next(request) 

        # User allowed APIs (read-only + control)
        if path.startswith("/api/control/"):
            return await call_next(request)
        if path.startswith("/api/user/light_scenarios"):
            return await call_next(request)
        if path == "/api/user/devices" and request.method.upper() == "GET":
            return await call_next(request)
        if path.startswith("/api/icons/mdi/"):
            return await call_next(request)
        if path == "/api/devices" and request.method.upper() == "GET":
            return await call_next(request)
        if path == "/api/cover_groups" and request.method.upper() == "GET":
            return await call_next(request)
        if path in ("/api/meta", "/api/buspro/status", "/api/mqtt/status"):
            return await call_next(request)
        if path == "/api/stream":
            return await call_next(request)
        if path.startswith("/assets/"):
            return await call_next(request)

        # If a proxy target is active (cookie set by /ext), allow unknown non-/api paths
        # so the SPA fallback can proxy routes like /security/functions instead of 404.
        try:
            px = str(request.cookies.get("buspro_px") or "").strip()
            if px and store.find_proxy_target(name=px):
                if not path.startswith("/api/"):
                    return await call_next(request)
        except Exception:
            pass

        # Everything else is admin-only
        return JSONResponse({"detail": "Not Found"}, status_code=404)

    @api.get("/favicon.ico")
    async def favicon_ico():
        return Response(status_code=204)

    @api.get("/manifest.webmanifest", include_in_schema=False)
    async def webmanifest():
        cfg = store.get_pwa_config()
        icon_url = str(cfg.get("icon_url") or "/static/e-face-nobg.png")
        start_url = str(cfg.get("start_url") or "/home2")
        if not start_url.startswith("/"):
            start_url = "/" + start_url
        data = {
            "name": cfg.get("name") or "Ekonex",
            "short_name": cfg.get("short_name") or (cfg.get("name") or "Ekonex"),
            "start_url": start_url,
            "scope": "/",
            "display": "standalone",
            "background_color": cfg.get("background_color") or "#05070b",
            "theme_color": cfg.get("theme_color") or "#05070b",
            "icons": [
                {"src": icon_url, "sizes": "192x192", "type": "image/png"},
                {"src": icon_url, "sizes": "512x512", "type": "image/png"},
            ],
        }
        return Response(content=json.dumps(data, ensure_ascii=False), media_type="application/manifest+json")

    @api.get("/sw.js", include_in_schema=False)
    async def service_worker():
        # Minimal SW: cache static assets, network-first for navigations.
        sw = f"""
// buspro minimal service worker
const CACHE = 'buspro-pwa-{ADDON_VERSION}';
const PRECACHE = [
  '/home2',
  '/manifest.webmanifest',
  '/static/logo_ekonex.png',
  '/static/e-face-nobg.png',
];

self.addEventListener('install', (event) => {{
  event.waitUntil((async () => {{
    const cache = await caches.open(CACHE);
    await cache.addAll(PRECACHE);
    self.skipWaiting();
  }})());
}});

self.addEventListener('activate', (event) => {{
  event.waitUntil((async () => {{
    const keys = await caches.keys();
    await Promise.all(keys.map((k) => (k !== CACHE ? caches.delete(k) : Promise.resolve())));
    self.clients.claim();
  }})());
}});

self.addEventListener('fetch', (event) => {{
  const req = event.request;
  const url = new URL(req.url);
  if (req.method !== 'GET' || url.origin !== self.location.origin) return;

  // Navigation: network first, fallback to cached /home2
  if (req.mode === 'navigate') {{
    event.respondWith((async () => {{
      try {{
        const res = await fetch(req);
        return res;
      }} catch (e) {{
        const cache = await caches.open(CACHE);
        const cached = await cache.match('/home2');
        return cached || new Response('Offline', {{ status: 503 }});
      }}
    }})());
    return;
  }}

  // Static: cache first
  if (url.pathname.startsWith('/static/')) {{
    event.respondWith((async () => {{
      const cache = await caches.open(CACHE);
      const cached = await cache.match(req);
      if (cached) return cached;
      const res = await fetch(req);
      try {{ cache.put(req, res.clone()); }} catch (e) {{}}
      return res;
    }})());
  }}
}});
""".strip()
        return Response(content=sw, media_type="application/javascript", headers={"Cache-Control": "no-cache"})

    @api.get("/www/{asset_path:path}")
    async def www_asset(asset_path: str):
        base_raw = getattr(api.state, "www_dir", None)
        base = os.path.abspath(str(base_raw or ""))
        if not base_raw or not base or not os.path.isdir(base):
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        rel = str(asset_path or "").lstrip("/").replace("\\", "/")
        if not rel or rel.startswith(".") or "/.." in f"/{rel}":
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        full = os.path.abspath(os.path.join(base, rel))
        if not full.startswith(base):
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        if not os.path.exists(full) or not os.path.isfile(full):
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        try:
            return FileResponse(full)
        except Exception:
            return JSONResponse({"detail": "Not Found"}, status_code=404)

    def _rewrite_location(*, name: str, upstream_base: str, location: str) -> str:
        loc = str(location or "").strip()
        if not loc:
            return loc
        try:
            base = urllib.parse.urlparse(upstream_base)
            if loc.startswith("/"):
                return f"/ext/{name}{loc}"
            u = urllib.parse.urlparse(loc)
            if u.scheme and u.netloc:
                if u.scheme == base.scheme and u.netloc == base.netloc:
                    return f"/ext/{name}{u.path or '/'}" + (("?" + u.query) if u.query else "") + (("#" + u.fragment) if u.fragment else "")
        except Exception:
            pass
        return loc

    def _proxy_name_from_request(request: Request) -> str | None:
        # Prefer referer, fallback to cookie (set by /ext responses).
        ref = str(request.headers.get("referer") or "")
        if ref:
            try:
                p = urllib.parse.urlparse(ref)
                seg = (p.path or "").split("/")
                # /ext/<name>/...
                if len(seg) >= 3 and seg[1] == "ext" and seg[2]:
                    return seg[2]
            except Exception:
                pass
        try:
            c = request.cookies.get("buspro_px")
            if c:
                return str(c).strip() or None
        except Exception:
            pass
        return None

    def _rewrite_set_cookie_path(*, name: str, header_value: str) -> str:
        s = str(header_value or "")
        parts = [p.strip() for p in s.split(";")]
        out: list[str] = []
        for p in parts:
            if p.lower().startswith("path="):
                out.append(f"Path=/ext/{name}/")
                continue
            if p.lower().startswith("domain="):
                # strip Domain to keep cookie host-only under our domain
                continue
            out.append(p)
        return "; ".join([x for x in out if x])

    def _rewrite_body_text(*, name: str, text: str, content_type: str) -> str:
        # Best-effort rewrite of root-absolute references (/foo) to /ext/{name}/foo
        # Works for many simple UIs (NVR/router/HA pages), not guaranteed.
        s = text
        prefix = f"/ext/{name}/"
        try:
            # html attributes
            for attr in ("href", "src", "action", "poster", "data-src", "data-href"):
                s = s.replace(f'{attr}="/', f'{attr}="{prefix}')
                s = s.replace(f"{attr}='/", f"{attr}='{prefix}")
                # unquoted (href=/foo)
                s = re.sub(rf"(?i)(\\b{re.escape(attr)}\\s*=\\s*)/(?!ext/)", rf"\\1{prefix}", s)
            # CSS url(/...)
            s = s.replace("url(/", f"url({prefix}")
            s = s.replace("url('/", f"url('{prefix}")
            s = s.replace('url("/', f'url("{prefix}')
        except Exception:
            return text
        return s

    def _proxy_bootstrap_js(*, name: str, upstream_base: str) -> str:
        # Injected into HTML pages served via /ext to keep fetch/XHR/WebSocket inside the proxy.
        base = urllib.parse.urlparse(upstream_base)
        upstream_host = base.netloc
        return f"""
<script>
// buspro proxy bootstrap (best-effort)
(function() {{
  const PROXY_PREFIX = '/ext/{name}';
  const WS_PREFIX = '/extws/{name}';
  const UPSTREAM_HOST = {json.dumps(upstream_host)};
  // Hidden back gesture: long-press top-left corner (works even on proxied pages).
  (function() {{
    const CORNER = 70;
    const HOLD_MS = 450;
    let timer = null;
    function inCornerXY(x, y) {{ return Number(x) <= CORNER && Number(y) <= CORNER; }}
    function clear() {{ if (timer) {{ clearTimeout(timer); timer = null; }} }}
    function goHome() {{ try {{ window.location.href = new URL('/home2', window.location.href).toString(); }} catch(e) {{}} }}
    function doBack() {{
      try {{
        // In proxied apps, prefer going back to our Home2 (SPA routers often swallow history.back()).
        if (String(window.location.pathname || '').startsWith(PROXY_PREFIX + '/') || String(window.location.pathname || '') === PROXY_PREFIX) {{
          goHome();
          return;
        }}
        if (window.history && window.history.length > 1) {{
          window.history.back();
          return;
        }}
      }} catch(e) {{}}
      goHome();
    }}
    function arm() {{
      if (timer) return;
      timer = setTimeout(() => {{ timer = null; doBack(); }}, HOLD_MS);
    }}
    function onPointerDown(e) {{
      try {{
        if (!inCornerXY(e.clientX, e.clientY)) return;
        arm();
      }} catch(ex) {{}}
    }}
    function onTouchStart(e) {{
      try {{
        const t = (e.touches && e.touches[0]) ? e.touches[0] : null;
        if (!t) return;
        if (!inCornerXY(t.clientX, t.clientY)) return;
        arm();
      }} catch(ex) {{}}
    }}
    document.addEventListener('pointerdown', onPointerDown, {{ passive: true }});
    document.addEventListener('pointerup', clear, {{ passive: true }});
    document.addEventListener('pointercancel', clear, {{ passive: true }});
    document.addEventListener('pointermove', (e) => {{ if (!timer) return; try {{ if (!inCornerXY(e.clientX, e.clientY)) clear(); }} catch(ex) {{ clear(); }} }}, {{ passive: true }});
    document.addEventListener('touchstart', onTouchStart, {{ passive: true }});
    document.addEventListener('touchend', clear, {{ passive: true }});
    document.addEventListener('touchcancel', clear, {{ passive: true }});
    document.addEventListener('mousedown', onPointerDown, {{ passive: true }});
    document.addEventListener('mouseup', clear, {{ passive: true }});
    document.addEventListener('mousemove', (e) => {{ if (!timer) return; try {{ if (!inCornerXY(e.clientX, e.clientY)) clear(); }} catch(ex) {{ clear(); }} }}, {{ passive: true }});
  }})();

  function abs(u) {{ try {{ return new URL(u, window.location.href).toString(); }} catch(e) {{ return String(u||''); }} }}
  function rewriteNav(u) {{
    const s = String(u||'');
    if (!s) return s;
    if (s.startsWith(PROXY_PREFIX) || s.startsWith(WS_PREFIX)) return s;
    if (s.startsWith('ext/{name}')) return '/' + s;
    if (s.startsWith('extws/{name}')) return '/' + s;
    if (s.startsWith('#')) return s;
    if (s.startsWith('/')) return PROXY_PREFIX + s;
    try {{
      const parsed = new URL(s, window.location.href);
      if (parsed && parsed.host && parsed.host === window.location.host) {{
        const p = (parsed.pathname || '/');
        if (p.startsWith(PROXY_PREFIX) || p === PROXY_PREFIX || p.startsWith(WS_PREFIX) || p === WS_PREFIX) {{
          return p + (parsed.search||'') + (parsed.hash||'');
        }}
        return PROXY_PREFIX + p + (parsed.search||'') + (parsed.hash||'');
      }}
      if (parsed && parsed.host && parsed.host === UPSTREAM_HOST) {{
        const p = (parsed.pathname || '/');
        if (p.startsWith(PROXY_PREFIX) || p === PROXY_PREFIX || p.startsWith(WS_PREFIX) || p === WS_PREFIX) {{
          return p + (parsed.search||'') + (parsed.hash||'');
        }}
        return PROXY_PREFIX + p + (parsed.search||'') + (parsed.hash||'');
      }}
    }} catch(e) {{}}
    return s;
  }}
  function rewritePath(u) {{
    const s = String(u||'');
    if (!s) return s;
    if (s.startsWith(PROXY_PREFIX) || s.startsWith(WS_PREFIX)) return s;
    if (s.startsWith('ext/{name}')) return '/' + s;
    if (s.startsWith('extws/{name}')) return '/' + s;
    if (s.startsWith('/')) return PROXY_PREFIX + s;
    // Absolute URL on same origin (our add-on) -> force through proxy
    try {{
      const parsed = new URL(s, window.location.href);
      if (parsed && parsed.host && parsed.host === window.location.host) {{
        const p = (parsed.pathname || '/');
        if (p.startsWith(PROXY_PREFIX) || p === PROXY_PREFIX || p.startsWith(WS_PREFIX) || p === WS_PREFIX) {{
          return p + (parsed.search||'') + (parsed.hash||'');
        }}
        if (p && p.startsWith('/')) return PROXY_PREFIX + p + (parsed.search||'') + (parsed.hash||'');
      }}
      // Absolute URL pointing to upstream host -> force through proxy
      if (parsed && parsed.host && parsed.host === UPSTREAM_HOST) {{
        const p = (parsed.pathname || '/');
        if (p.startsWith(PROXY_PREFIX) || p === PROXY_PREFIX || p.startsWith(WS_PREFIX) || p === WS_PREFIX) {{
          return p + (parsed.search||'') + (parsed.hash||'');
        }}
        return PROXY_PREFIX + p + (parsed.search||'') + (parsed.hash||'');
      }}
    }} catch(e) {{}}
    return s;
  }}

  // Intercept clicks on absolute paths (e.g. /security/functions) and keep them inside /ext/<name>/...
  try {{
    document.addEventListener('click', (e) => {{
      try {{
        const t = e.target;
        if (!t) return;
        const a = (t.closest && t.closest('a')) ? t.closest('a') : null;
        if (!a) return;
        const hrefAttr = a.getAttribute('href') || '';
        if (!hrefAttr) return;
        if (hrefAttr.startsWith('#') || hrefAttr.startsWith('mailto:') || hrefAttr.startsWith('tel:')) return;
        const rewritten = rewriteNav(hrefAttr);
        if (rewritten !== hrefAttr) {{
          e.preventDefault();
          e.stopPropagation();
          window.location.href = abs(rewritten);
        }}
      }} catch(ex) {{}}
    }}, true);
    document.addEventListener('submit', (e) => {{
      try {{
        const f = e.target;
        if (!f || !f.getAttribute) return;
        const action = f.getAttribute('action') || '';
        if (!action) return;
        const rewritten = rewriteNav(action);
        if (rewritten !== action) f.setAttribute('action', rewritten);
      }} catch(ex) {{}}
    }}, true);
  }} catch(e) {{}}

  // Best-effort patch for location.assign/replace and window.open used by some apps
  try {{
    const _open = window.open;
    if (typeof _open === 'function') {{
      window.open = function(url, target, features) {{
        try {{ url = abs(rewriteNav(url)); }} catch(e) {{}}
        return _open.call(window, url, target, features);
      }};
    }}
  }} catch(e) {{}}
  try {{
    const loc = window.location;
    const _assign = loc.assign ? loc.assign.bind(loc) : null;
    const _replace = loc.replace ? loc.replace.bind(loc) : null;
    if (_assign) loc.assign = function(u) {{ return _assign(abs(rewriteNav(u))); }};
    if (_replace) loc.replace = function(u) {{ return _replace(abs(rewriteNav(u))); }};
  }} catch(e) {{}}
  // fetch wrapper
  try {{
    const _fetch = window.fetch;
    if (typeof _fetch === 'function') {{
      window.fetch = function(input, init) {{
        try {{
          if (typeof input === 'string') {{
            return _fetch(rewritePath(input), init);
          }}
          if (input && typeof input.url === 'string') {{
            const u = rewritePath(input.url);
            if (u !== input.url) {{
              const req = new Request(abs(u), input);
              return _fetch(req, init);
            }}
          }}
        }} catch(e) {{}}
        return _fetch(input, init);
      }};
    }}
  }} catch(e) {{}}
  // XHR wrapper
  try {{
    const X = window.XMLHttpRequest;
    if (X && X.prototype && typeof X.prototype.open === 'function') {{
      const _open = X.prototype.open;
      X.prototype.open = function(method, url) {{
        try {{
          const u = rewritePath(url);
          const args = Array.prototype.slice.call(arguments);
          args[1] = abs(u);
          return _open.apply(this, args);
        }} catch(e) {{}}
        return _open.apply(this, arguments);
      }};
    }}
  }} catch(e) {{}}
  // WebSocket wrapper
  try {{
    const _WS = window.WebSocket;
    if (typeof _WS === 'function') {{
      window.WebSocket = function(url, protocols) {{
        try {{
          let u = String(url||'');
          if (u.startsWith('/')) {{
            u = WS_PREFIX + u;
          }} else {{
            const parsed = new URL(u, window.location.href);
            if (parsed && parsed.host && parsed.host === UPSTREAM_HOST) {{
              u = WS_PREFIX + (parsed.pathname || '/');
              if (parsed.search) u += parsed.search;
            }}
          }}
          const absu = abs(u);
          return protocols ? new _WS(absu, protocols) : new _WS(absu);
        }} catch(e) {{
          return protocols ? new _WS(url, protocols) : new _WS(url);
        }}
      }};
      window.WebSocket.prototype = _WS.prototype;
      window.WebSocket.OPEN = _WS.OPEN;
      window.WebSocket.CLOSED = _WS.CLOSED;
      window.WebSocket.CLOSING = _WS.CLOSING;
      window.WebSocket.CONNECTING = _WS.CONNECTING;
    }}
  }} catch(e) {{}}
}})();
</script>
""".strip()

    def _fetch_upstream(method: str, url: str, headers: dict[str, str], body: bytes | None) -> tuple[int, dict[str, list[str]], bytes]:
        req = urllib.request.Request(url=url, method=method.upper())
        for k, v in headers.items():
            req.add_header(k, v)
        data = body if body is not None and method.upper() not in ("GET", "HEAD") else None
        try:
            with urllib.request.urlopen(req, data=data, timeout=12) as resp:
                status = int(getattr(resp, "status", 200))
                raw_headers = resp.headers
                out_headers: dict[str, list[str]] = {}
                for k in raw_headers.keys():
                    vals = raw_headers.get_all(k) or []
                    out_headers[k] = [str(x) for x in vals]
                payload = resp.read()
                return status, out_headers, payload
        except urllib.error.HTTPError as e:
            # Propagate upstream HTTP errors (404/401/500) instead of masking them as 502.
            status = int(getattr(e, "code", 502) or 502)
            raw_headers = getattr(e, "headers", None)
            out_headers: dict[str, list[str]] = {}
            if raw_headers is not None:
                for k in raw_headers.keys():
                    vals = raw_headers.get_all(k) or []
                    out_headers[k] = [str(x) for x in vals]
            try:
                payload = e.read()
            except Exception:
                payload = b""
            return status, out_headers, payload

    def _hop_by_hop_header(name: str) -> bool:
        return name.lower() in {
            "connection",
            "keep-alive",
            "proxy-authenticate",
            "proxy-authorization",
            "te",
            "trailers",
            "transfer-encoding",
            "upgrade",
        }

    @api.api_route("/ext/{name}/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"])
    async def ext_proxy(name: str, path: str, request: Request):
        # User-side reverse proxy for configured local targets.
        target = store.find_proxy_target(name=name)
        if not target:
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        upstream_base = str(target.get("base_url") or "").strip()
        if not upstream_base:
            return JSONResponse({"detail": "Not Found"}, status_code=404)

        # Guard against duplicated proxy prefix (e.g. /ext/core/ext/core/...)
        try:
            dup = f"ext/{name}/"
            p = str(path or "")
            while p.startswith(dup):
                p = p[len(dup) :]
            if p == f"ext/{name}":
                p = ""
            path = p
        except Exception:
            pass

        q = request.url.query or ""
        base = upstream_base.rstrip("/") + "/"
        upstream_url = urllib.parse.urljoin(base, str(path or "").lstrip("/"))
        if q:
            upstream_url = upstream_url + ("&" if "?" in upstream_url else "?") + q

        # Forward headers (subset)
        fwd_headers: dict[str, str] = {}
        for k, v in request.headers.items():
            lk = k.lower()
            if lk in ("host", "content-length"):
                continue
            if lk.startswith("sec-"):
                continue
            if lk == "origin":
                continue
            fwd_headers[k] = v

        body = await request.body()
        try:
            status, upstream_headers, payload = await asyncio.to_thread(
                _fetch_upstream,
                request.method,
                upstream_url,
                fwd_headers,
                body,
            )
        except Exception:
            return JSONResponse({"detail": "Upstream error"}, status_code=502)

        # Build response headers
        out_headers: dict[str, str] = {}
        set_cookie_out: list[str] = []
        content_type = ""
        for k, vals in upstream_headers.items():
            if _hop_by_hop_header(k):
                continue
            lk = k.lower()
            if lk == "content-length":
                continue
            if lk == "location" and vals:
                out_headers["Location"] = _rewrite_location(name=name, upstream_base=upstream_base, location=vals[-1])
                continue
            if lk == "set-cookie":
                for sv in vals:
                    set_cookie_out.append(_rewrite_set_cookie_path(name=name, header_value=sv))
                continue
            if lk == "content-type" and vals:
                content_type = vals[-1]
            # Keep last value for most headers
            if vals:
                out_headers[k] = vals[-1]

        # Rewrite HTML/CSS bodies best-effort
        ct = (content_type or "").lower()
        if payload and ("text/html" in ct or "text/css" in ct):
            try:
                charset = "utf-8"
                if "charset=" in ct:
                    charset = ct.split("charset=", 1)[1].split(";", 1)[0].strip() or "utf-8"
                text = payload.decode(charset, errors="replace")
                text2 = _rewrite_body_text(name=name, text=text, content_type=content_type)
                if "text/html" in ct:
                    inj = _proxy_bootstrap_js(name=name, upstream_base=upstream_base)
                    if "</head>" in text2:
                        text2 = text2.replace("</head>", inj + "\n</head>", 1)
                    elif "</body>" in text2:
                        text2 = text2.replace("</body>", inj + "\n</body>", 1)
                    else:
                        text2 = inj + "\n" + text2
                payload = text2.encode(charset, errors="replace")
            except Exception:
                pass

        resp = Response(content=payload, status_code=int(status), headers=out_headers)
        for sc in set_cookie_out:
            resp.headers.append("Set-Cookie", sc)
        try:
            resp.set_cookie("buspro_px", name, path="/", samesite="lax")
        except Exception:
            pass
        return resp

    @api.api_route("/assets/{asset_path:path}", methods=["GET", "HEAD"])
    async def assets_proxy(asset_path: str, request: Request):
        name = _proxy_name_from_request(request)
        if not name:
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        return await ext_proxy(name=name, path=f"assets/{asset_path}", request=request)

    @api.api_route("/api/stream", methods=["GET"])
    async def api_stream_proxy(request: Request):
        # Some panels use SSE / long-poll endpoints at /api/stream
        name = _proxy_name_from_request(request)
        if not name:
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        target = store.find_proxy_target(name=name)
        if not target:
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        upstream_base = str(target.get("base_url") or "").strip()
        if not upstream_base:
            return JSONResponse({"detail": "Not Found"}, status_code=404)

        q = request.url.query or ""
        base = upstream_base.rstrip("/") + "/"
        upstream_url = urllib.parse.urljoin(base, "api/stream")
        if q:
            upstream_url = upstream_url + ("&" if "?" in upstream_url else "?") + q

        # EventSource expects text/event-stream (some upstreams omit/lie on HEAD).
        media_type = "text/event-stream"

        queue: asyncio.Queue[bytes | None] = asyncio.Queue(maxsize=40)
        stop = threading.Event()

        def _run():
            try:
                req = urllib.request.Request(url=upstream_url, method="GET", headers={"Accept": "text/event-stream"})
                with urllib.request.urlopen(req, timeout=300) as resp:
                    while not stop.is_set():
                        # SSE is line-oriented; read line-by-line to flush quickly.
                        chunk = resp.readline()
                        if not chunk:
                            break
                        try:
                            api.state.loop.call_soon_threadsafe(queue.put_nowait, bytes(chunk))
                        except Exception:
                            break
            except Exception:
                pass
            finally:
                try:
                    api.state.loop.call_soon_threadsafe(queue.put_nowait, None)
                except Exception:
                    pass

        t = threading.Thread(target=_run, daemon=True)
        t.start()

        async def gen():
            try:
                while True:
                    item = await queue.get()
                    if item is None:
                        break
                    yield item
            finally:
                stop.set()

        headers = {"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"}
        return StreamingResponse(gen(), media_type=media_type, headers=headers)

    @api.websocket("/extws/{name}/{path:path}")
    async def ext_ws(websocket: WebSocket, name: str, path: str):
        await websocket.accept()
        target = store.find_proxy_target(name=name)
        if not target:
            await websocket.close(code=1008)
            return
        upstream_base = str(target.get("base_url") or "").strip()
        if not upstream_base:
            await websocket.close(code=1011)
            return

        # Guard against duplicated proxy prefix (e.g. /extws/core/extws/core/...)
        try:
            dup = f"extws/{name}/"
            p = str(path or "")
            while p.startswith(dup):
                p = p[len(dup) :]
            if p == f"extws/{name}":
                p = ""
            path = p
        except Exception:
            pass

        base = urllib.parse.urlparse(upstream_base)
        scheme = "wss" if base.scheme == "https" else "ws"
        upstream_ws = f"{scheme}://{base.netloc}/" + str(path or "").lstrip("/")
        q = websocket.url.query or ""
        if q:
            upstream_ws = upstream_ws + ("&" if "?" in upstream_ws else "?") + q

        try:
            import websockets  # type: ignore
        except Exception:
            await websocket.close(code=1011)
            return

        # Forward cookies/auth headers to upstream.
        extra_headers: list[tuple[str, str]] = []
        try:
            for k, v in websocket.headers.items():
                lk = k.lower()
                if lk in ("cookie", "authorization"):
                    extra_headers.append((k, v))
        except Exception:
            pass

        try:
            async with websockets.connect(upstream_ws, extra_headers=extra_headers, ping_interval=None) as upstream:
                async def c2u():
                    try:
                        while True:
                            msg = await websocket.receive()
                            t = msg.get("type")
                            if t == "websocket.disconnect":
                                break
                            if t != "websocket.receive":
                                continue
                            if "text" in msg and msg["text"] is not None:
                                await upstream.send(msg["text"])
                            elif "bytes" in msg and msg["bytes"] is not None:
                                await upstream.send(msg["bytes"])
                    except Exception:
                        return

                async def u2c():
                    try:
                        async for m in upstream:
                            if isinstance(m, (bytes, bytearray)):
                                await websocket.send_bytes(bytes(m))
                            else:
                                await websocket.send_text(str(m))
                    except Exception:
                        return

                t1 = asyncio.create_task(c2u())
                t2 = asyncio.create_task(u2c())
                done, pending = await asyncio.wait({t1, t2}, return_when=asyncio.FIRST_COMPLETED)
                for p in pending:
                    p.cancel()
        except Exception:
            try:
                await websocket.close(code=1011)
            except Exception:
                pass

    def _publish_light_state(dev: dict[str, Any], st: LightState) -> None:
        subnet = int(dev["subnet_id"])
        did = int(dev["device_id"])
        ch = int(dev["channel"])
        topic = f"{settings.mqtt.base_topic}/state/light/{subnet}/{did}/{ch}"
        payload: dict[str, Any] = {"state": "ON" if st.is_on else "OFF"}
        if bool(dev.get("dimmable", True)):
            payload["brightness"] = int(st.brightness or 0)
        store.set_light_state(subnet_id=subnet, device_id=did, channel=ch, state=payload["state"], brightness=payload.get("brightness"))
        mqtt.publish(topic, payload, retain=True)

    def _publish_cover_state(dev: dict[str, Any], st: CoverState) -> None:
        subnet = int(dev["subnet_id"])
        did = int(dev["device_id"])
        ch = int(dev["channel"])
        state_topic = f"{settings.mqtt.base_topic}/state/cover_state/{subnet}/{did}/{ch}"
        pos_topic = f"{settings.mqtt.base_topic}/state/cover_pos/{subnet}/{did}/{ch}"
        state = str(st.state).upper()
        pos = int(st.position) if st.position is not None else None
        store.set_cover_state(subnet_id=subnet, device_id=did, channel=ch, state=state, position=pos)
        mqtt.publish(state_topic, state, retain=True)
        if pos is not None:
            mqtt.publish(pos_topic, str(pos), retain=True)

    def _publish_temp_value(dev: dict[str, Any], value: float, ts: float | None = None) -> None:
        subnet = int(dev["subnet_id"])
        did = int(dev["device_id"])
        sensor_id = int(dev["channel"])
        topic = f"{settings.mqtt.base_topic}/state/temp/{subnet}/{did}/{sensor_id}"

        decimals = 1
        try:
            decimals = int(dev.get("decimals") if dev.get("decimals") is not None else 1)
        except Exception:
            decimals = 1
        decimals = max(0, min(3, decimals))

        # Reduce chatter: publish only if the rounded value changed
        addr = f"{subnet}.{did}.{sensor_id}"
        last_t: dict[str, float] = getattr(api.state, "_last_temp_value", {}) or {}
        rounded = float(round(float(value), decimals))
        if addr in last_t and float(last_t[addr]) == rounded:
            return
        last_t[addr] = rounded
        api.state._last_temp_value = last_t

        store.set_temp_state(subnet_id=subnet, device_id=did, channel=sensor_id, value=float(value), ts=ts)
        mqtt.publish(topic, f"{rounded:.{decimals}f}", retain=True)

    def _publish_humidity_value(dev: dict[str, Any], value: float, ts: float | None = None) -> None:
        subnet = int(dev["subnet_id"])
        did = int(dev["device_id"])
        sensor_id = int(dev["channel"])
        topic = f"{settings.mqtt.base_topic}/state/humidity/{subnet}/{did}/{sensor_id}"

        decimals = 0
        try:
            decimals = int(dev.get("decimals") if dev.get("decimals") is not None else 0)
        except Exception:
            decimals = 0
        decimals = max(0, min(3, decimals))

        # Reduce chatter: publish only if the rounded value changed
        addr = f"{subnet}.{did}.{sensor_id}"
        last_h: dict[str, float] = getattr(api.state, "_last_humidity_value", {}) or {}
        rounded = float(round(float(value), decimals))
        if addr in last_h and float(last_h[addr]) == rounded:
            return
        last_h[addr] = rounded
        api.state._last_humidity_value = last_h

        store.set_humidity_state(subnet_id=subnet, device_id=did, channel=sensor_id, value=float(value), ts=ts)
        mqtt.publish(topic, f"{rounded:.{decimals}f}", retain=True)

    def _publish_illuminance_value(dev: dict[str, Any], value: float, ts: float | None = None) -> None:
        subnet = int(dev["subnet_id"])
        did = int(dev["device_id"])
        sensor_id = int(dev["channel"])
        topic = f"{settings.mqtt.base_topic}/state/illuminance/{subnet}/{did}/{sensor_id}"

        decimals = 0
        try:
            decimals = int(dev.get("decimals") if dev.get("decimals") is not None else 0)
        except Exception:
            decimals = 0
        decimals = max(0, min(3, decimals))

        scale: float | None = None
        offset: float | None = None
        try:
            scale = float(dev.get("lux_scale")) if dev.get("lux_scale") is not None else None
        except Exception:
            scale = None
        try:
            offset = float(dev.get("lux_offset")) if dev.get("lux_offset") is not None else None
        except Exception:
            offset = None

        v = float(value)
        if scale is not None:
            v = v * float(scale)
        if offset is not None:
            v = v + float(offset)

        # Reduce chatter: publish only if the rounded value changed
        addr = f"{subnet}.{did}.{sensor_id}"
        last_lx: dict[str, float] = getattr(api.state, "_last_illuminance_value", {}) or {}
        rounded = float(round(float(v), decimals))
        if addr in last_lx and float(last_lx[addr]) == rounded:
            return
        last_lx[addr] = rounded
        api.state._last_illuminance_value = last_lx

        store.set_illuminance_state(subnet_id=subnet, device_id=did, channel=sensor_id, value=float(v), ts=ts)
        mqtt.publish(topic, f"{rounded:.{decimals}f}", retain=True)

    def _air_level_to_text(level: int) -> str:
        if int(level) == 0:
            return "clean"
        if int(level) == 1:
            return "mild"
        if int(level) == 2:
            return "moderate"
        if int(level) == 3:
            return "severe"
        return "unknown"

    def _publish_air_quality(dev: dict[str, Any], level: int, ts: float | None = None) -> None:
        subnet = int(dev["subnet_id"])
        did = int(dev["device_id"])
        sensor_id = int(dev["channel"])
        topic = f"{settings.mqtt.base_topic}/state/air_quality/{subnet}/{did}/{sensor_id}"

        addr = f"{subnet}.{did}.{sensor_id}"
        last_a: dict[str, str] = getattr(api.state, "_last_air_quality", {}) or {}
        text = _air_level_to_text(int(level))
        if addr in last_a and str(last_a[addr]) == text:
            return
        last_a[addr] = text
        api.state._last_air_quality = last_a

        store.set_air_quality_state(subnet_id=subnet, device_id=did, channel=sensor_id, state=text, ts=ts)
        mqtt.publish(topic, text, retain=True)

    def _publish_gas_percent(dev: dict[str, Any], value: float, ts: float | None = None) -> None:
        subnet = int(dev["subnet_id"])
        did = int(dev["device_id"])
        sensor_id = int(dev["channel"])
        topic = f"{settings.mqtt.base_topic}/state/gas_percent/{subnet}/{did}/{sensor_id}"

        addr = f"{subnet}.{did}.{sensor_id}"
        last_g: dict[str, float] = getattr(api.state, "_last_gas_percent", {}) or {}
        rounded = float(round(float(value), 0))
        if addr in last_g and float(last_g[addr]) == rounded:
            return
        last_g[addr] = rounded
        api.state._last_gas_percent = last_g

        store.set_gas_percent_state(subnet_id=subnet, device_id=did, channel=sensor_id, value=float(rounded), ts=ts)
        mqtt.publish(topic, f"{rounded:.0f}", retain=True)

    def _publish_pir_state(dev: dict[str, Any], state: str, ts: float | None = None) -> None:
        subnet = int(dev["subnet_id"])
        did = int(dev["device_id"])
        sensor_id = int(dev["channel"])
        topic = f"{settings.mqtt.base_topic}/state/pir/{subnet}/{did}/{sensor_id}"

        state_u = str(state or "").upper()
        if state_u not in ("ON", "OFF"):
            return

        addr = f"{subnet}.{did}.{sensor_id}"
        last_p: dict[str, str] = getattr(api.state, "_last_pir_state", {}) or {}
        if addr in last_p and str(last_p[addr]) == state_u:
            return
        last_p[addr] = state_u
        api.state._last_pir_state = last_p

        store.set_pir_state(subnet_id=subnet, device_id=did, channel=sensor_id, state=state_u, ts=ts)
        mqtt.publish(topic, state_u, retain=True)

    def _publish_ultrasonic_state(dev: dict[str, Any], state: str, ts: float | None = None) -> None:
        subnet = int(dev["subnet_id"])
        did = int(dev["device_id"])
        sensor_id = int(dev["channel"])
        topic = f"{settings.mqtt.base_topic}/state/ultrasonic/{subnet}/{did}/{sensor_id}"

        state_u = str(state or "").upper()
        if state_u not in ("ON", "OFF"):
            return

        addr = f"{subnet}.{did}.{sensor_id}"
        last_u: dict[str, str] = getattr(api.state, "_last_ultrasonic_state", {}) or {}
        if addr in last_u and str(last_u[addr]) == state_u:
            return
        last_u[addr] = state_u
        api.state._last_ultrasonic_state = last_u

        store.set_ultrasonic_state(subnet_id=subnet, device_id=did, channel=sensor_id, state=state_u, ts=ts)
        mqtt.publish(topic, state_u, retain=True)

    def _publish_dry_contact_state(dev: dict[str, Any], state: str, ts: float | None = None, payload_x: int | None = None) -> None:
        subnet = int(dev["subnet_id"])
        did = int(dev["device_id"])
        input_id = int(dev["channel"])
        topic = f"{settings.mqtt.base_topic}/state/dry_contact/{subnet}/{did}/{input_id}"
        attrs_topic = f"{settings.mqtt.base_topic}/state/dry_contact_attr/{subnet}/{did}/{input_id}"

        state_u = str(state or "").upper()
        if state_u not in ("ON", "OFF"):
            return

        store.set_dry_contact_state(subnet_id=subnet, device_id=did, channel=input_id, state=state_u, ts=ts, payload_x=payload_x)
        mqtt.publish(topic, state_u, retain=True)
        mqtt.publish(
            attrs_topic,
            {
                "subnet_id": subnet,
                "device_id": did,
                "input_id": input_id,
                "x": int(payload_x) if payload_x is not None else None,
                "ts": float(ts) if ts is not None else None,
            },
            retain=True,
        )

    def _cover_group_config_topic(*, gid: str) -> str:
        nid = f"buspro_{settings.gateway.host.replace('.', '_')}_{settings.gateway.port}"
        return f"{settings.mqtt.discovery_prefix}/cover/{nid}/group_{gid}/config"

    def _cover_group_no_pct_config_topic(*, gid: str) -> str:
        nid = f"buspro_{settings.gateway.host.replace('.', '_')}_{settings.gateway.port}"
        return f"{settings.mqtt.discovery_prefix}/cover/{nid}/group_{gid}_no_pct/config"

    def _light_scenario_config_topic(*, sid: str) -> str:
        nid = f"buspro_{settings.gateway.host.replace('.', '_')}_{settings.gateway.port}"
        return f"{settings.mqtt.discovery_prefix}/button/{nid}/light_scenario_{sid}/config"

    def _publish_cover_group_state(*, gid: str, state: str, position: int | None) -> None:
        state_u = str(state or "").upper() or "STOP"
        pos_i = int(position) if position is not None else None
        store.set_cover_group_state(group_id=gid, state=state_u, position=pos_i)
        mqtt.publish(f"{settings.mqtt.base_topic}/state/cover_group_state/{gid}", state_u, retain=True)
        if pos_i is not None:
            mqtt.publish(f"{settings.mqtt.base_topic}/state/cover_group_pos/{gid}", str(pos_i), retain=True)

    def _rebuild_cover_group_index() -> None:
        groups = store.list_cover_groups()
        by_gid: dict[str, dict[str, Any]] = {}
        membership: dict[str, set[str]] = {}
        for g in groups:
            name = str(g.get("name") or "").strip()
            gid = str(g.get("id") or "").strip() or slugify(name)
            if not name or not gid:
                continue
            by_gid[gid] = g
            for m in (g.get("members") or []):
                addr = str(m or "").strip()
                if not addr:
                    continue
                membership.setdefault(addr, set()).add(gid)
        api.state.cover_groups_by_gid = by_gid
        api.state.cover_group_membership = membership

    def _rebuild_temp_index() -> None:
        idx: dict[tuple[int, int, int], dict[str, Any]] = {}
        for dev in store.list_devices():
            if str(dev.get("type") or "light").strip().lower() != "temp":
                continue
            try:
                key = (int(dev["subnet_id"]), int(dev["device_id"]), int(dev["channel"]))
            except Exception:
                continue
            idx[key] = dev
        api.state.temp_index = idx

    def _rebuild_humidity_index() -> None:
        # Map (subnet, device) -> list of humidity devices (channels)
        idx: dict[tuple[int, int], list[dict[str, Any]]] = {}
        for dev in store.list_devices():
            if str(dev.get("type") or "").strip().lower() != "humidity":
                continue
            try:
                key = (int(dev["subnet_id"]), int(dev["device_id"]))
            except Exception:
                continue
            idx.setdefault(key, []).append(dev)
        api.state.humidity_index = idx

    def _rebuild_illuminance_index() -> None:
        # Map (subnet, device) -> list of illuminance devices (channels)
        idx: dict[tuple[int, int], list[dict[str, Any]]] = {}
        for dev in store.list_devices():
            if str(dev.get("type") or "").strip().lower() != "illuminance":
                continue
            try:
                key = (int(dev["subnet_id"]), int(dev["device_id"]))
            except Exception:
                continue
            idx.setdefault(key, []).append(dev)
        api.state.illuminance_index = idx

    def _rebuild_dry_contact_index() -> None:
        idx: dict[tuple[int, int, int], dict[str, Any]] = {}
        for dev in store.list_devices():
            if str(dev.get("type") or "").strip().lower() != "dry_contact":
                continue
            try:
                key = (int(dev["subnet_id"]), int(dev["device_id"]), int(dev["channel"]))
            except Exception:
                continue
            idx[key] = dev
        api.state.dry_contact_index = idx

    def _rebuild_air_index() -> None:
        idx: dict[tuple[int, int, int], dict[str, Any]] = {}
        for dev in store.list_devices():
            if str(dev.get("type") or "").strip().lower() != "air":
                continue
            try:
                key = (int(dev["subnet_id"]), int(dev["device_id"]), int(dev["channel"]))
            except Exception:
                continue
            idx[key] = dev
        api.state.air_index = idx

    def _rebuild_pir_index() -> None:
        idx: dict[tuple[int, int, int], dict[str, Any]] = {}
        for dev in store.list_devices():
            if str(dev.get("type") or "").strip().lower() != "pir":
                continue
            try:
                key = (int(dev["subnet_id"]), int(dev["device_id"]), int(dev["channel"]))
            except Exception:
                continue
            idx[key] = dev
        api.state.pir_index = idx

    def _rebuild_ultrasonic_index() -> None:
        idx: dict[tuple[int, int, int], dict[str, Any]] = {}
        for dev in store.list_devices():
            if str(dev.get("type") or "").strip().lower() != "ultrasonic":
                continue
            try:
                key = (int(dev["subnet_id"]), int(dev["device_id"]), int(dev["channel"]))
            except Exception:
                continue
            idx[key] = dev
        api.state.ultrasonic_index = idx

    def _aggregate_cover_group_state(gid: str) -> tuple[str, int | None] | None:
        by_gid: dict[str, dict[str, Any]] = getattr(api.state, "cover_groups_by_gid", {}) or {}
        group = by_gid.get(gid)
        if not group:
            return None
        members = group.get("members") or []
        if not isinstance(members, list) or not members:
            return None

        last: dict[str, tuple[str, int | None]] = getattr(api.state, "_last_cover_state", {}) or {}
        states: list[str] = []
        positions: list[int] = []
        for m in members:
            addr = str(m or "").strip()
            if not addr:
                continue
            st = last.get(addr)
            if st is None:
                continue
            s, p = st
            su = str(s or "").upper() or "STOP"
            states.append(su)
            if p is not None:
                positions.append(int(p))

        if not states:
            return None

        if any(s == "OPENING" for s in states) and not any(s == "CLOSING" for s in states):
            agg_state = "OPENING"
        elif any(s == "CLOSING" for s in states) and not any(s == "OPENING" for s in states):
            agg_state = "CLOSING"
        else:
            if positions and all(p == 0 for p in positions):
                agg_state = "CLOSED"
            elif positions and all(p == 100 for p in positions):
                agg_state = "OPEN"
            else:
                agg_state = "STOP"

        agg_pos: int | None = None
        if positions:
            agg_pos = int(round(sum(positions) / max(1, len(positions))))
            agg_pos = max(0, min(100, agg_pos))
        return agg_state, agg_pos

    def _publish_cover_groups_for_member(addr: str) -> None:
        membership: dict[str, set[str]] = getattr(api.state, "cover_group_membership", {}) or {}
        gids = membership.get(addr)
        if not gids:
            return
        last_g: dict[str, tuple[str, int | None]] = getattr(api.state, "_last_cover_group_state", {}) or {}
        for gid in list(gids):
            agg = _aggregate_cover_group_state(gid)
            if agg is None:
                continue
            state_u, pos_i = agg
            prev = last_g.get(gid)
            cur = (state_u, pos_i)
            if prev == cur:
                continue
            last_g[gid] = cur
            api.state._last_cover_group_state = last_g
            _publish_cover_group_state(gid=gid, state=state_u, position=pos_i)

    def _publish_all_cover_group_states() -> None:
        by_gid: dict[str, dict[str, Any]] = getattr(api.state, "cover_groups_by_gid", {}) or {}
        if not by_gid:
            return
        last_g: dict[str, tuple[str, int | None]] = getattr(api.state, "_last_cover_group_state", {}) or {}
        for gid in list(by_gid.keys()):
            agg = _aggregate_cover_group_state(gid)
            if agg is None:
                continue
            state_u, pos_i = agg
            cur = (state_u, pos_i)
            if last_g.get(gid) == cur:
                continue
            last_g[gid] = cur
            _publish_cover_group_state(gid=gid, state=state_u, position=pos_i)
        api.state._last_cover_group_state = last_g

    def _parse_cover_member_addr(addr: str) -> tuple[int, int, int] | None:
        try:
            a = str(addr or "").strip()
            s, d, c = a.split(".")
            return int(s), int(d), int(c)
        except Exception:
            return None

    def _find_cover_group_by_gid(gid: str) -> dict[str, Any] | None:
        gid_s = str(gid or "").strip()
        if not gid_s:
            return None
        by_gid: dict[str, dict[str, Any]] = getattr(api.state, "cover_groups_by_gid", {}) or {}
        if gid_s in by_gid:
            return by_gid[gid_s]
        for g in store.list_cover_groups():
            name = str(g.get("name") or "").strip()
            if name and slugify(name) == gid_s:
                return g
        return None

    async def _run_cover_group_command(gid: str, cmd: str, pos: int | None = None, *, raw: bool = False) -> None:
        group = _find_cover_group_by_gid(gid)
        if not group:
            return
        members = group.get("members") or []
        if not isinstance(members, list) or not members:
            return

        gw: BusproGateway | None = api.state.gateway
        if gw is None:
            return

        # Importante: inviare in modo "pacciato" (stile Control4) per evitare flood UDP quando un gruppo
        # ha molti membri. BusproGateway ha gia' una coda per cover, ma creare task concorrenti qui
        # aumenta la probabilita' di race/ordine non deterministico sotto carico.
        for m in members:
            parsed = _parse_cover_member_addr(str(m or ""))
            if not parsed:
                continue
            subnet, did, ch = parsed
            if cmd == "OPEN":
                if raw:
                    await gw.cover_open_raw(subnet_id=subnet, device_id=did, channel=ch)
                else:
                    await gw.cover_open(subnet_id=subnet, device_id=did, channel=ch)
            elif cmd == "CLOSE":
                if raw:
                    await gw.cover_close_raw(subnet_id=subnet, device_id=did, channel=ch)
                else:
                    await gw.cover_close(subnet_id=subnet, device_id=did, channel=ch)
            elif cmd == "STOP":
                await gw.cover_stop(subnet_id=subnet, device_id=did, channel=ch)
            elif cmd == "SET_POSITION" and pos is not None:
                await gw.cover_set_position(subnet_id=subnet, device_id=did, channel=ch, position=int(pos))

    async def _broadcast_light_state(dev: dict[str, Any], st: LightState) -> None:
        subnet = int(dev["subnet_id"])
        did = int(dev["device_id"])
        ch = int(dev["channel"])
        await hub.broadcast(
            "light_state",
            {
                "subnet_id": subnet,
                "device_id": did,
                "channel": ch,
                "state": "ON" if st.is_on else "OFF",
                "brightness": int(st.brightness or 0),
            },
        )

    async def _broadcast_cover_state(dev: dict[str, Any], st: CoverState) -> None:
        subnet = int(dev["subnet_id"])
        did = int(dev["device_id"])
        ch = int(dev["channel"])
        await hub.broadcast(
            "cover_state",
            {
                "subnet_id": subnet,
                "device_id": did,
                "channel": ch,
                "state": str(st.state).upper(),
                "position": int(st.position) if st.position is not None else None,
            },
        )

    async def _broadcast_temp_value(dev: dict[str, Any], value: float, ts: float | None) -> None:
        subnet = int(dev["subnet_id"])
        did = int(dev["device_id"])
        sensor_id = int(dev["channel"])
        await hub.broadcast(
            "temp_value",
            {
                "subnet_id": subnet,
                "device_id": did,
                "channel": sensor_id,
                "value": float(value),
                "ts": float(ts) if ts is not None else None,
            },
        )

    async def _broadcast_humidity_value(dev: dict[str, Any], value: float, ts: float | None) -> None:
        subnet = int(dev["subnet_id"])
        did = int(dev["device_id"])
        sensor_id = int(dev["channel"])
        await hub.broadcast(
            "humidity_value",
            {
                "subnet_id": subnet,
                "device_id": did,
                "channel": sensor_id,
                "value": float(value),
                "ts": float(ts) if ts is not None else None,
            },
        )

    async def _broadcast_illuminance_value(dev: dict[str, Any], value: float, ts: float | None) -> None:
        subnet = int(dev["subnet_id"])
        did = int(dev["device_id"])
        sensor_id = int(dev["channel"])
        await hub.broadcast(
            "illuminance_value",
            {
                "subnet_id": subnet,
                "device_id": did,
                "channel": sensor_id,
                "value": float(value),
                "ts": float(ts) if ts is not None else None,
            },
        )

    async def _broadcast_air_quality(dev: dict[str, Any], state: str, ts: float | None) -> None:
        subnet = int(dev["subnet_id"])
        did = int(dev["device_id"])
        sensor_id = int(dev["channel"])
        await hub.broadcast(
            "air_quality",
            {
                "subnet_id": subnet,
                "device_id": did,
                "channel": sensor_id,
                "state": str(state),
                "ts": float(ts) if ts is not None else None,
            },
        )

    async def _broadcast_gas_percent(dev: dict[str, Any], value: float, ts: float | None) -> None:
        subnet = int(dev["subnet_id"])
        did = int(dev["device_id"])
        sensor_id = int(dev["channel"])
        await hub.broadcast(
            "gas_percent",
            {
                "subnet_id": subnet,
                "device_id": did,
                "channel": sensor_id,
                "value": float(value),
                "ts": float(ts) if ts is not None else None,
            },
        )

    async def _broadcast_pir_state(dev: dict[str, Any], state: str, ts: float | None) -> None:
        subnet = int(dev["subnet_id"])
        did = int(dev["device_id"])
        sensor_id = int(dev["channel"])
        await hub.broadcast(
            "pir_state",
            {
                "subnet_id": subnet,
                "device_id": did,
                "channel": sensor_id,
                "state": str(state).upper(),
                "ts": float(ts) if ts is not None else None,
            },
        )

    async def _broadcast_ultrasonic_state(dev: dict[str, Any], state: str, ts: float | None) -> None:
        subnet = int(dev["subnet_id"])
        did = int(dev["device_id"])
        sensor_id = int(dev["channel"])
        await hub.broadcast(
            "ultrasonic_state",
            {
                "subnet_id": subnet,
                "device_id": did,
                "channel": sensor_id,
                "state": str(state).upper(),
                "ts": float(ts) if ts is not None else None,
            },
        )

    async def _broadcast_dry_contact_state(dev: dict[str, Any], state: str, ts: float | None, payload_x: int | None) -> None:
        subnet = int(dev["subnet_id"])
        did = int(dev["device_id"])
        input_id = int(dev["channel"])
        await hub.broadcast(
            "dry_contact_state",
            {
                "subnet_id": subnet,
                "device_id": did,
                "channel": input_id,
                "state": str(state).upper(),
                "x": int(payload_x) if payload_x is not None else None,
                "ts": float(ts) if ts is not None else None,
            },
        )


    async def _broadcast_devices() -> None:
        await hub.broadcast(
            "devices",
            {
                "devices": _list_user_devices(),
            },
        )

    async def _republish_discovery() -> None:
        devices = store.list_devices()
        for dev in devices:
            dtype = str(dev.get("type") or "light").strip().lower()
            if dtype == "cover":
                topic, payload = cover_discovery(
                    discovery_prefix=settings.mqtt.discovery_prefix,
                    base_topic=settings.mqtt.base_topic,
                    gateway_host=settings.gateway.host,
                    gateway_port=settings.gateway.port,
                    device=dev,
                )
                mqtt.publish(topic, payload, retain=True)
                topic2, payload2 = cover_no_pct_discovery(
                    discovery_prefix=settings.mqtt.discovery_prefix,
                    base_topic=settings.mqtt.base_topic,
                    gateway_host=settings.gateway.host,
                    gateway_port=settings.gateway.port,
                    device=dev,
                )
                mqtt.publish(topic2, payload2, retain=True)
            elif dtype == "humidity":
                topic, payload = humidity_discovery(
                    discovery_prefix=settings.mqtt.discovery_prefix,
                    base_topic=settings.mqtt.base_topic,
                    gateway_host=settings.gateway.host,
                    gateway_port=settings.gateway.port,
                    device=dev,
                )
                mqtt.publish(topic, payload, retain=True)
            elif dtype == "illuminance":
                topic, payload = illuminance_discovery(
                    discovery_prefix=settings.mqtt.discovery_prefix,
                    base_topic=settings.mqtt.base_topic,
                    gateway_host=settings.gateway.host,
                    gateway_port=settings.gateway.port,
                    device=dev,
                )
                mqtt.publish(topic, payload, retain=True)
            elif dtype == "temp":
                topic, payload = temperature_discovery(
                    discovery_prefix=settings.mqtt.discovery_prefix,
                    base_topic=settings.mqtt.base_topic,
                    gateway_host=settings.gateway.host,
                    gateway_port=settings.gateway.port,
                    device=dev,
                )
                mqtt.publish(topic, payload, retain=True)
            elif dtype == "dry_contact":
                topic, payload = dry_contact_discovery(
                    discovery_prefix=settings.mqtt.discovery_prefix,
                    base_topic=settings.mqtt.base_topic,
                    gateway_host=settings.gateway.host,
                    gateway_port=settings.gateway.port,
                    device=dev,
                )
                mqtt.publish(topic, payload, retain=True)
            elif dtype == "pir":
                topic, payload = pir_discovery(
                    discovery_prefix=settings.mqtt.discovery_prefix,
                    base_topic=settings.mqtt.base_topic,
                    gateway_host=settings.gateway.host,
                    gateway_port=settings.gateway.port,
                    device=dev,
                )
                mqtt.publish(topic, payload, retain=True)
            elif dtype == "ultrasonic":
                topic, payload = ultrasonic_discovery(
                    discovery_prefix=settings.mqtt.discovery_prefix,
                    base_topic=settings.mqtt.base_topic,
                    gateway_host=settings.gateway.host,
                    gateway_port=settings.gateway.port,
                    device=dev,
                )
                mqtt.publish(topic, payload, retain=True)
            elif dtype == "air":
                topic, payload = air_quality_discovery(
                    discovery_prefix=settings.mqtt.discovery_prefix,
                    base_topic=settings.mqtt.base_topic,
                    gateway_host=settings.gateway.host,
                    gateway_port=settings.gateway.port,
                    device=dev,
                )
                mqtt.publish(topic, payload, retain=True)
                topic2, payload2 = gas_percent_discovery(
                    discovery_prefix=settings.mqtt.discovery_prefix,
                    base_topic=settings.mqtt.base_topic,
                    gateway_host=settings.gateway.host,
                    gateway_port=settings.gateway.port,
                    device=dev,
                )
                mqtt.publish(topic2, payload2, retain=True)
            else:
                topic, payload = light_discovery(
                    discovery_prefix=settings.mqtt.discovery_prefix,
                    base_topic=settings.mqtt.base_topic,
                    gateway_host=settings.gateway.host,
                    gateway_port=settings.gateway.port,
                    device=dev,
                )
                mqtt.publish(topic, payload, retain=True)

        # Cover groups (group blinds) as MQTT cover entities + cleanup removed ones
        groups = store.list_cover_groups()
        current_gids: list[str] = []
        for g in groups:
            name = str(g.get("name") or "").strip()
            gid = str(g.get("id") or "").strip() or slugify(name)
            if not name or not gid:
                continue
            current_gids.append(gid)

        prev_gids = store.get_published_cover_group_ids()
        for gid in prev_gids:
            if gid not in current_gids:
                mqtt.publish(_cover_group_config_topic(gid=gid), "", retain=True)
                mqtt.publish(_cover_group_no_pct_config_topic(gid=gid), "", retain=True)
                mqtt.publish(f"{settings.mqtt.base_topic}/state/cover_group_state/{gid}", "", retain=True)
                mqtt.publish(f"{settings.mqtt.base_topic}/state/cover_group_pos/{gid}", "", retain=True)
                store.delete_cover_group_state(group_id=gid)

        for g in groups:
            try:
                topic, payload = cover_group_discovery(
                    discovery_prefix=settings.mqtt.discovery_prefix,
                    base_topic=settings.mqtt.base_topic,
                    gateway_host=settings.gateway.host,
                    gateway_port=settings.gateway.port,
                    group=g,
                    category="Cover",
                )
                mqtt.publish(topic, payload, retain=True)
                topic2, payload2 = cover_group_no_pct_discovery(
                    discovery_prefix=settings.mqtt.discovery_prefix,
                    base_topic=settings.mqtt.base_topic,
                    gateway_host=settings.gateway.host,
                    gateway_port=settings.gateway.port,
                    group=g,
                )
                mqtt.publish(topic2, payload2, retain=True)
            except Exception:
                continue

        store.set_published_cover_group_ids(current_gids)

        # Light scenarios as MQTT button entities + cleanup removed ones
        scenarios = store.list_light_scenarios()
        current_sids: list[str] = []
        for sc in scenarios:
            try:
                sid = str(sc.get("id") or "").strip()
            except Exception:
                sid = ""
            if sid:
                current_sids.append(sid)

        prev_sids = store.get_published_light_scenario_ids()
        for sid in prev_sids:
            if sid not in current_sids:
                mqtt.publish(_light_scenario_config_topic(sid=sid), "", retain=True)

        for sc in scenarios:
            try:
                topic, payload = light_scenario_button_discovery(
                    discovery_prefix=settings.mqtt.discovery_prefix,
                    base_topic=settings.mqtt.base_topic,
                    gateway_host=settings.gateway.host,
                    gateway_port=settings.gateway.port,
                    scenario=sc,
                )
                mqtt.publish(topic, payload, retain=True)
            except Exception:
                continue

        store.set_published_light_scenario_ids(current_sids)

    @api.on_event("startup")
    async def _startup() -> None:
        loop = asyncio.get_running_loop()
        api.state.loop = loop
        api.state.ha_states = {}
        api.state.ha_caps = {}
        api.state.ha_poll_task = None
        api.state._last_light_state = {}
        api.state._last_cover_state = {}
        api.state._last_cover_group_state = {}
        api.state._last_temp_value = {}
        api.state._last_humidity_value = {}
        api.state._last_illuminance_value = {}
        api.state._last_dry_contact_state = {}
        api.state._last_pir_state = {}
        api.state._last_ultrasonic_state = {}
        api.state._last_air_quality = {}
        api.state._last_gas_percent = {}
        api.state.cover_groups_by_gid = {}
        api.state.cover_group_membership = {}
        api.state.temp_index = {}
        api.state.dry_contact_index = {}
        api.state.air_index = {}
        api.state.pir_index = {}
        api.state.ultrasonic_index = {}

        # Prefill last-known states from persistent store to avoid broadcasting unchanged states.
        try:
            raw0 = store.read_raw()
            states0 = dict(raw0.get("states", {}) or {})
            for k, v in states0.items():
                try:
                    if str(k).startswith("light:"):
                        addr = str(k).split(":", 1)[1]
                        st = str((v or {}).get("state") or "").upper() or "?"
                        br = int((v or {}).get("brightness") or 0)
                        api.state._last_light_state[addr] = (st, br)
                    elif str(k).startswith("cover:"):
                        addr = str(k).split(":", 1)[1]
                        st = str((v or {}).get("state") or "").upper() or "?"
                        pos = (v or {}).get("position")
                        api.state._last_cover_state[addr] = (st, int(pos) if pos is not None else None)
                    elif str(k).startswith("cover_group:"):
                        gid = str(k).split(":", 1)[1]
                        st = str((v or {}).get("state") or "").upper() or "?"
                        pos = (v or {}).get("position")
                        api.state._last_cover_group_state[gid] = (st, int(pos) if pos is not None else None)
                    elif str(k).startswith("temp:"):
                        addr = str(k).split(":", 1)[1]
                        try:
                            api.state._last_temp_value[addr] = float((v or {}).get("value"))
                        except Exception:
                            pass
                    elif str(k).startswith("humidity:"):
                        addr = str(k).split(":", 1)[1]
                        try:
                            api.state._last_humidity_value[addr] = float((v or {}).get("value"))
                        except Exception:
                            pass
                    elif str(k).startswith("illuminance:"):
                        addr = str(k).split(":", 1)[1]
                        try:
                            api.state._last_illuminance_value[addr] = float((v or {}).get("value"))
                        except Exception:
                            pass
                    elif str(k).startswith("dry_contact:"):
                        addr = str(k).split(":", 1)[1]
                        st = str((v or {}).get("state") or "").upper() or "?"
                        api.state._last_dry_contact_state[addr] = st
                    elif str(k).startswith("pir:"):
                        addr = str(k).split(":", 1)[1]
                        st = str((v or {}).get("state") or "").upper() or "?"
                        api.state._last_pir_state[addr] = st
                    elif str(k).startswith("ultrasonic:"):
                        addr = str(k).split(":", 1)[1]
                        st = str((v or {}).get("state") or "").upper() or "?"
                        api.state._last_ultrasonic_state[addr] = st
                    elif str(k).startswith("air_quality:"):
                        addr = str(k).split(":", 1)[1]
                        st = str((v or {}).get("state") or "").strip() or "unknown"
                        api.state._last_air_quality[addr] = st
                    elif str(k).startswith("gas_percent:"):
                        addr = str(k).split(":", 1)[1]
                        try:
                            api.state._last_gas_percent[addr] = float((v or {}).get("value"))
                        except Exception:
                            pass
                except Exception:
                    continue
        except Exception:
            pass

        # Ensure telegram source IP override is applied before BusPro starts.
        try:
            if str(getattr(settings.gateway, "local_ip", "") or "").strip():
                os.environ["BUSPRO_LOCAL_IP"] = str(getattr(settings.gateway, "local_ip")).strip()
        except Exception:
            pass

        # Start BusPro gateway
        gateway = BusproGateway(
            host=settings.gateway.host,
            port=settings.gateway.port,
            loop=loop,
            light_cmd_interval_s=float(getattr(settings, "light_cmd_interval_s", 0.12) or 0.0),
            udp_send_interval_s=float(getattr(settings, "udp_send_interval_s", 0.0) or 0.0),
        )
        api.state.gateway = gateway
        try:
            gateway.add_telegram_listener(api.state.sniffer.on_telegram)
        except Exception:
            pass

        _rebuild_temp_index()
        _rebuild_humidity_index()
        _rebuild_illuminance_index()
        _rebuild_dry_contact_index()
        _rebuild_air_index()
        _rebuild_pir_index()
        _rebuild_ultrasonic_index()

        def _decode_temp_value(dev: dict[str, Any], payload: list[Any] | tuple[Any, ...]) -> float | None:
            # Supported formats:
            # - float32: payload [sensor_id, aux, b0, b1, b2, b3] (LE)
            # - short:  payload [sensor_id, value] with configurable scale/offset
            try:
                fmt = str(dev.get("temp_format") or dev.get("format") or "auto").strip().lower()
            except Exception:
                fmt = "auto"

            if isinstance(payload, (list, tuple)) and len(payload) >= 6 and fmt in ("auto", "float32", "float"):
                raw = bytes(int(x) & 0xFF for x in payload[2:6])
                return float(struct.unpack("<f", raw)[0])

            if not isinstance(payload, (list, tuple)) or len(payload) != 2:
                return None

            # Default for "auto" on 2-byte payloads: many HDL sensors encode in 0.5°C steps.
            scale: float | None = None
            if fmt in ("short_half", "half", "0.5", "x0.5"):
                scale = 0.5
            elif fmt in ("short_tenths", "tenths", "0.1", "x0.1"):
                scale = 0.1
            elif fmt in ("short_int", "int", "1", "x1"):
                scale = 1.0
            elif fmt in ("auto", "short", "2b", "2byte"):
                scale = 0.5

            if dev.get("temp_scale") is not None:
                try:
                    scale = float(dev.get("temp_scale"))
                except Exception:
                    pass

            if scale is None:
                return None

            offset = 0.0
            if dev.get("temp_offset") is not None:
                try:
                    offset = float(dev.get("temp_offset"))
                except Exception:
                    offset = 0.0

            raw_val = int(payload[1]) & 0xFF
            return float(raw_val) * float(scale) + float(offset)

        def _on_temp_telegram(telegram: Any) -> None:
            # Manual sensors: process only if configured in temp_index.
            try:
                op = getattr(telegram, "operate_code", None)
                if "BroadcastTemperatureResponse" not in str(op):
                    return

                src = getattr(telegram, "source_address", None)
                payload = getattr(telegram, "payload", None)
                if not isinstance(src, (list, tuple)) or len(src) < 2:
                    return
                if not isinstance(payload, (list, tuple)) or len(payload) < 2:
                    return

                subnet_id = int(src[0])
                device_id = int(src[1])
                sensor_id = int(payload[0])

                idx: dict[tuple[int, int, int], dict[str, Any]] = getattr(api.state, "temp_index", {}) or {}
                dev = idx.get((subnet_id, device_id, sensor_id))
                if not dev:
                    return

                value = _decode_temp_value(dev, payload)
                if value is None:
                    return

                mn = dev.get("min_value")
                mx = dev.get("max_value")
                if mn is not None and value < float(mn):
                    return
                if mx is not None and value > float(mx):
                    return

                ts = time.time()
                _publish_temp_value(dev, value, ts=ts)
                asyncio.run_coroutine_threadsafe(_broadcast_temp_value(dev, value, ts), loop)
            except Exception:
                return

        try:
            gateway.add_telegram_listener(_on_temp_telegram)
        except Exception:
            pass

        def _on_humidity_telegram(telegram: Any) -> None:
            # 12-in-1: humidity appears in ReadSensorsInOneStatusResponse payload.
            try:
                op = getattr(telegram, "operate_code", None)
                op_s = str(op or "")

                # Primary: ReadSensorsInOneStatusResponse (0x1605)
                if "ReadSensorsInOneStatusResponse" not in op_s:
                    # Fallback: some devices emit a similar payload on raw opcode 0x1630
                    raw_hex = getattr(telegram, "operate_code_raw_hex", None)
                    if str(raw_hex or "").lower() != "1630":
                        return

                src = getattr(telegram, "source_address", None)
                payload = getattr(telegram, "payload", None)
                if not isinstance(src, (list, tuple)) or len(src) < 2:
                    return
                if not isinstance(payload, (list, tuple)):
                    return

                subnet_id = int(src[0])
                device_id = int(src[1])

                idx: dict[tuple[int, int], list[dict[str, Any]]] = getattr(api.state, "humidity_index", {}) or {}
                devs = idx.get((subnet_id, device_id)) or []
                if not devs:
                    return

                humidity: int | None = None
                if "ReadSensorsInOneStatusResponse" in op_s:
                    # Observed payload: [248, temp_raw, 0, 0, humidity, lux24?, 0,0,0,0]
                    if len(payload) >= 5 and int(payload[0]) == 248:
                        hv = int(payload[4]) & 0xFF
                        humidity = None if hv == 0xFF else hv
                else:
                    # 0x1630: similar but without leading 248
                    if len(payload) >= 4:
                        hv = int(payload[3]) & 0xFF
                        humidity = None if hv == 0xFF else hv

                if humidity is None:
                    return

                ts = time.time()
                for dev in devs:
                    _publish_humidity_value(dev, float(humidity), ts=ts)
                    asyncio.run_coroutine_threadsafe(_broadcast_humidity_value(dev, float(humidity), ts), loop)
            except Exception:
                return

        try:
            gateway.add_telegram_listener(_on_humidity_telegram)
        except Exception:
            pass

        def _on_illuminance_telegram(telegram: Any) -> None:
            # Illuminance can appear in multiple payload formats depending on device/firmware:
            # - ReadSensorsInOneStatusResponse (0x1605): 24-bit lux at payload[5:8] (with leading 248).
            # - Raw opcode 0x1630: similar to 0x1605 but without leading 248.
            # - ReadSensorStatusResponse (0x1646): 16-bit lux at payload[2:4] (with leading 248).
            try:
                op = getattr(telegram, "operate_code", None)
                op_s = str(op or "")

                raw_hex = str(getattr(telegram, "operate_code_raw_hex", "") or "").lower()

                is_1605 = "ReadSensorsInOneStatusResponse" in op_s
                is_1646 = ("ReadSensorStatusResponse" in op_s) or (raw_hex == "1646")
                is_1630 = raw_hex == "1630"

                if not (is_1605 or is_1630 or is_1646):
                    return

                src = getattr(telegram, "source_address", None)
                payload = getattr(telegram, "payload", None)
                if not isinstance(src, (list, tuple)) or len(src) < 2:
                    return
                if not isinstance(payload, (list, tuple)):
                    return

                subnet_id = int(src[0])
                device_id = int(src[1])

                idx: dict[tuple[int, int], list[dict[str, Any]]] = getattr(api.state, "illuminance_index", {}) or {}
                devs = idx.get((subnet_id, device_id)) or []
                if not devs:
                    return

                lux_raw: int | None = None
                if is_1605:
                    if len(payload) >= 4 and int(payload[0]) == 248:
                        # Common 12-in-1 (MASLA.2C etc.): 16-bit lux at payload[2:4]
                        b0_16 = int(payload[2]) & 0xFF
                        b1_16 = int(payload[3]) & 0xFF
                        lux16 = None if (b0_16 == 0xFF and b1_16 == 0xFF) else ((b0_16 << 8) + b1_16)

                        # Some variants expose 24-bit lux at payload[5:8]
                        lux24 = None
                        if len(payload) >= 8:
                            b0 = int(payload[5]) & 0xFF
                            b1 = int(payload[6]) & 0xFF
                            b2 = int(payload[7]) & 0xFF
                            if not (b0 == 0xFF and b1 == 0xFF and b2 == 0xFF):
                                lux24 = (b0 << 16) + (b1 << 8) + b2

                        # Heuristic: if payload looks like MASLA (AIR at index 5 is 0..3), prefer lux16.
                        try:
                            maybe_air = int(payload[5]) & 0xFF if len(payload) >= 6 else 0xFF
                        except Exception:
                            maybe_air = 0xFF
                        if lux16 is not None and maybe_air in (0, 1, 2, 3):
                            lux_raw = lux16
                        else:
                            lux_raw = lux24 if lux24 is not None else lux16
                elif is_1630:
                    # 0x1630: similar but without leading 248
                    if len(payload) >= 7:
                        b0 = int(payload[4]) & 0xFF
                        b1 = int(payload[5]) & 0xFF
                        b2 = int(payload[6]) & 0xFF
                        if not (b0 == 0xFF and b1 == 0xFF and b2 == 0xFF):
                            lux_raw = (b0 << 16) + (b1 << 8) + b2
                else:
                    # 0x1646 / ReadSensorStatusResponse: examples observed from logs:
                    # payload [248, 48, 0, 150, 0, 1, 0, 0, 0, 0] => 150 lux
                    # payload [248, 48, 3, 33,  0, 1, 0, 0, 0, 0] => 0x0321 = 801 lux
                    if len(payload) >= 4:
                        if int(payload[0]) == 248:
                            b0 = int(payload[2]) & 0xFF
                            b1 = int(payload[3]) & 0xFF
                        else:
                            # Fallback: if header differs, assume first 2 bytes are the value.
                            b0 = int(payload[0]) & 0xFF
                            b1 = int(payload[1]) & 0xFF

                        if not (b0 == 0xFF and b1 == 0xFF):
                            lux_raw = (b0 << 8) + b1

                if lux_raw is None:
                    return

                ts = time.time()
                for dev in devs:
                    _publish_illuminance_value(dev, float(lux_raw), ts=ts)
                    asyncio.run_coroutine_threadsafe(_broadcast_illuminance_value(dev, float(lux_raw), ts), loop)
            except Exception:
                return

        try:
            gateway.add_telegram_listener(_on_illuminance_telegram)
        except Exception:
            pass

        def _on_air_telegram(telegram: Any) -> None:
            # MASLA.2C / 12-in-1: AIR (0..3) + Gas% appear in ReadSensorsInOneStatusResponse payload.
            try:
                op = getattr(telegram, "operate_code", None)
                op_s = str(op or "")
                raw_hex = str(getattr(telegram, "operate_code_raw_hex", "") or "").lower()

                is_1605 = "ReadSensorsInOneStatusResponse" in op_s
                is_1630 = raw_hex == "1630"
                if not (is_1605 or is_1630):
                    return

                src = getattr(telegram, "source_address", None)
                payload = getattr(telegram, "payload", None)
                if not isinstance(src, (list, tuple)) or len(src) < 2:
                    return
                if not isinstance(payload, (list, tuple)):
                    return

                subnet_id = int(src[0])
                device_id = int(src[1])

                # Air sensors are indexed by (subnet, device, sensor_id)
                idx: dict[tuple[int, int, int], dict[str, Any]] = getattr(api.state, "air_index", {}) or {}

                # Extract sensor_id + fields (best-effort for MASLA layouts)
                sensor_id = None
                air_level: int | None = None
                gas_percent: int | None = None

                if is_1605:
                    if len(payload) >= 7 and int(payload[0]) in (248, 245):
                        sensor_id = int(payload[0]) & 0xFF
                        al = int(payload[5]) & 0xFF
                        gp = int(payload[6]) & 0xFF
                        air_level = None if al == 0xFF else al
                        gas_percent = None if gp == 0xFF else gp
                else:
                    # 0x1630: similar but without leading sensor_id byte
                    if len(payload) >= 6:
                        sensor_id = 248
                        al = int(payload[4]) & 0xFF
                        gp = int(payload[5]) & 0xFF
                        air_level = None if al == 0xFF else al
                        gas_percent = None if gp == 0xFF else gp

                if sensor_id is None:
                    return

                dev = idx.get((subnet_id, device_id, int(sensor_id)))
                if not dev:
                    return

                ts = time.time()
                if air_level is not None:
                    _publish_air_quality(dev, int(air_level), ts=ts)
                    asyncio.run_coroutine_threadsafe(_broadcast_air_quality(dev, _air_level_to_text(int(air_level)), ts), loop)
                if gas_percent is not None and 0 <= int(gas_percent) <= 100:
                    _publish_gas_percent(dev, float(gas_percent), ts=ts)
                    asyncio.run_coroutine_threadsafe(_broadcast_gas_percent(dev, float(gas_percent), ts), loop)
            except Exception:
                return

        try:
            gateway.add_telegram_listener(_on_air_telegram)
        except Exception:
            pass

        def _on_presence_telegram(telegram: Any) -> None:
            # MS12.2C / 12-in-1: PIR + Ultrasonic presence flags are seen in:
            # - ReadSensorStatusResponse (0x1646): payload [248, sensor_id, 0, 0, ultrasonic, pir, ...]
            # - BroadcastSensorStatusAutoResponse (0x1647): payload [sensor_id, 0, 0, 0, ultrasonic, pir, ...]
            #
            # Observed mapping from logs:
            #   pir -> payload[4]
            #   ultrasonic -> payload[5]
            try:
                op = getattr(telegram, "operate_code", None)
                op_s = str(op or "")
                raw_hex = str(getattr(telegram, "operate_code_raw_hex", "") or "").lower()

                is_1646 = ("ReadSensorStatusResponse" in op_s) or (raw_hex == "1646")
                is_1647 = ("BroadcastSensorStatusAutoResponse" in op_s) or (raw_hex == "1647")
                if not (is_1646 or is_1647):
                    return

                src = getattr(telegram, "source_address", None)
                payload = getattr(telegram, "payload", None)
                if not isinstance(src, (list, tuple)) or len(src) < 2:
                    return
                if not isinstance(payload, (list, tuple)):
                    return

                subnet_id = int(src[0])
                device_id = int(src[1])

                sensor_id: int | None = None
                pir_on: bool | None = None
                ultrasonic_on: bool | None = None

                if is_1646:
                    if len(payload) >= 6 and int(payload[0]) == 248:
                        sensor_id = int(payload[1]) & 0xFF
                        pir_on = bool(int(payload[4]) & 0xFF)
                        ultrasonic_on = bool(int(payload[5]) & 0xFF)
                else:
                    if len(payload) >= 6:
                        sensor_id = int(payload[0]) & 0xFF
                        pir_on = bool(int(payload[4]) & 0xFF)
                        ultrasonic_on = bool(int(payload[5]) & 0xFF)

                if sensor_id is None or pir_on is None or ultrasonic_on is None:
                    return

                pir_idx: dict[tuple[int, int, int], dict[str, Any]] = getattr(api.state, "pir_index", {}) or {}
                ultra_idx: dict[tuple[int, int, int], dict[str, Any]] = getattr(api.state, "ultrasonic_index", {}) or {}
                key = (subnet_id, device_id, int(sensor_id))

                ts = time.time()
                pir_dev = pir_idx.get(key)
                if pir_dev:
                    st = "ON" if pir_on else "OFF"
                    _publish_pir_state(pir_dev, st, ts=ts)
                    asyncio.run_coroutine_threadsafe(_broadcast_pir_state(pir_dev, st, ts), loop)

                ultra_dev = ultra_idx.get(key)
                if ultra_dev:
                    st = "ON" if ultrasonic_on else "OFF"
                    _publish_ultrasonic_state(ultra_dev, st, ts=ts)
                    asyncio.run_coroutine_threadsafe(_broadcast_ultrasonic_state(ultra_dev, st, ts), loop)
            except Exception:
                return

        try:
            gateway.add_telegram_listener(_on_presence_telegram)
        except Exception:
            pass

        def _on_dry_contact_telegram(telegram: Any) -> None:
            try:
                op = getattr(telegram, "operate_code", None)
                op_s = str(op or "")
                raw_hex = str(getattr(telegram, "operate_code_raw_hex", "") or "").lower()
                if "ControlPanelACResponse" not in op_s and raw_hex != "e3d9":
                    return

                src = getattr(telegram, "source_address", None)
                payload = getattr(telegram, "payload", None)
                if not isinstance(src, (list, tuple)) or len(src) < 2:
                    return
                if not isinstance(payload, (list, tuple)) or len(payload) < 3:
                    return

                subnet_id = int(src[0])
                device_id = int(src[1])
                input_id = int(payload[1])
                v = int(payload[2]) & 0xFF
                x = int(payload[0]) & 0xFF
                if v == 1:
                    state_u = "ON"
                elif v == 0:
                    state_u = "OFF"
                else:
                    return

                idx: dict[tuple[int, int, int], dict[str, Any]] = getattr(api.state, "dry_contact_index", {}) or {}
                dev = idx.get((subnet_id, device_id, input_id))
                if not dev:
                    return

                if bool(dev.get("invert")):
                    state_u = "OFF" if state_u == "ON" else "ON"

                addr = f"{subnet_id}.{device_id}.{input_id}"
                last_dc: dict[str, str] = getattr(api.state, "_last_dry_contact_state", {}) or {}
                if last_dc.get(addr) == state_u:
                    return
                last_dc[addr] = state_u
                api.state._last_dry_contact_state = last_dc

                ts = time.time()
                _publish_dry_contact_state(dev, state_u, ts=ts, payload_x=x)
                asyncio.run_coroutine_threadsafe(_broadcast_dry_contact_state(dev, state_u, ts, x), loop)
            except Exception:
                return

        try:
            gateway.add_telegram_listener(_on_dry_contact_telegram)
        except Exception:
            pass

        # Realtime + MQTT on updates
        def _on_state(key: LightKey, st: LightState) -> None:
            devices = store.list_devices()
            for dev in devices:
                if str(dev.get("type") or "light") != "light":
                    continue
                if int(dev["subnet_id"]) == key.subnet_id and int(dev["device_id"]) == key.device_id and int(dev["channel"]) == key.channel:
                    subnet = int(dev["subnet_id"])
                    did = int(dev["device_id"])
                    ch = int(dev["channel"])
                    addr = f"{subnet}.{did}.{ch}"
                    state_s = "ON" if st.is_on else "OFF"
                    br = int(st.brightness or 0)
                    prev = api.state._last_light_state.get(addr)
                    cur = (state_s, br)
                    if prev == cur:
                        break
                    api.state._last_light_state[addr] = cur
                    _publish_light_state(dev, st)
                    asyncio.run_coroutine_threadsafe(_broadcast_light_state(dev, st), loop)
                    break

        gateway.add_state_listener(_on_state)

        def _on_cover(key: CoverKey, st: CoverState) -> None:
            devices = store.list_devices()
            for dev in devices:
                if str(dev.get("type") or "") != "cover":
                    continue
                if int(dev["subnet_id"]) == key.subnet_id and int(dev["device_id"]) == key.device_id and int(dev["channel"]) == key.channel:
                    subnet = int(dev["subnet_id"])
                    did = int(dev["device_id"])
                    ch = int(dev["channel"])
                    addr = f"{subnet}.{did}.{ch}"
                    state_s = str(st.state).upper()
                    pos = int(st.position) if st.position is not None else None
                    prev = api.state._last_cover_state.get(addr)
                    cur = (state_s, pos)
                    if prev == cur:
                        break
                    api.state._last_cover_state[addr] = cur
                    _publish_cover_state(dev, st)
                    _publish_cover_groups_for_member(addr)
                    asyncio.run_coroutine_threadsafe(_broadcast_cover_state(dev, st), loop)
                    break

        gateway.add_cover_listener(_on_cover)
        await gateway.start()

        _rebuild_cover_group_index()
        _publish_all_cover_group_states()

        async def _poll_loop() -> None:
            # Periodic status reads so UI/HA updates even if the bus is quiet.
            # Pace reads to avoid UDP burst when many devices are configured.
            poll_interval_s = float(getattr(settings, "poll_interval_s", 180.0) or 0.0)
            poll_pace_s = float(getattr(settings, "poll_pace_s", 0.15) or 0.0)
            if poll_interval_s <= 0:
                return
            while True:
                await asyncio.sleep(poll_interval_s)
                for dev in store.list_devices():
                    dtype = str(dev.get("type") or "light").strip().lower()
                    if dtype == "cover":
                        await gateway.read_cover_status(
                            subnet_id=int(dev["subnet_id"]),
                            device_id=int(dev["device_id"]),
                            channel=int(dev["channel"]),
                        )
                    elif dtype in ("temp", "humidity", "illuminance", "dry_contact"):
                        continue
                    else:
                        await gateway.read_light_status(
                            subnet_id=int(dev["subnet_id"]),
                            device_id=int(dev["device_id"]),
                            channel=int(dev["channel"]),
                        )
                    if poll_pace_s > 0:
                        await asyncio.sleep(poll_pace_s)

        api.state.poll_task = asyncio.create_task(_poll_loop())
        # Ensure devices exist and ask initial status
        for dev in store.list_devices():
            dtype = str(dev.get("type") or "light").strip().lower()
            if dtype == "cover":
                gateway.ensure_cover(
                    subnet_id=int(dev["subnet_id"]),
                    device_id=int(dev["device_id"]),
                    channel=int(dev["channel"]),
                    name=str(dev.get("name") or ""),
                    opening_time_up=int(dev.get("opening_time_up") or dev.get("opening_time") or 20),
                    opening_time_down=int(dev.get("opening_time_down") or dev.get("opening_time") or 20),
                    start_delay_s=float(dev.get("start_delay_s") or 0.0),
                )
            elif dtype in ("temp", "humidity", "illuminance", "dry_contact"):
                continue
            else:
                gateway.ensure_light(
                    subnet_id=int(dev["subnet_id"]),
                    device_id=int(dev["device_id"]),
                    channel=int(dev["channel"]),
                    name=str(dev.get("name") or ""),
                )
        poll_pace_s0 = float(getattr(settings, "poll_pace_s", 0.15) or 0.0)
        for dev in store.list_devices():
            dtype = str(dev.get("type") or "light").strip().lower()
            if dtype == "cover":
                await gateway.read_cover_status(
                    subnet_id=int(dev["subnet_id"]),
                    device_id=int(dev["device_id"]),
                    channel=int(dev["channel"]),
                )
            elif dtype in ("temp", "humidity", "illuminance", "dry_contact"):
                continue
            else:
                await gateway.read_light_status(
                    subnet_id=int(dev["subnet_id"]),
                    device_id=int(dev["device_id"]),
                    channel=int(dev["channel"]),
                )
            if poll_pace_s0 > 0:
                await asyncio.sleep(poll_pace_s0)

        # MQTT connect and discovery
        _LOGGER.info("Starting MQTT client %s:%s", settings.mqtt.host, settings.mqtt.port)
        def _on_mqtt_connect() -> None:
            # Broker restart can drop retained messages if persistence is off.
            # Re-publish availability and discovery on every (re)connect.
            mqtt.publish(f"{settings.mqtt.base_topic}/availability", "online", retain=True)
            asyncio.run_coroutine_threadsafe(_republish_discovery(), loop)

        mqtt.set_connect_handler(_on_mqtt_connect)
        mqtt.connect()

        async def _ha_poll_loop() -> None:
            if not _ha_enabled():
                return
            while True:
                try:
                    interval = float(getattr(settings, "ha_poll_interval_s", 2.0) or 2.0)
                    interval = max(0.5, min(60.0, interval))
                    ha_devices = store.list_ha_devices()
                    eids: list[str] = []
                    domains: dict[str, str] = {}
                    for it in ha_devices:
                        eid = str(it.get("entity_id") or "").strip().lower()
                        if not eid:
                            continue
                        dom = str(it.get("domain") or "").strip().lower() or (eid.split(".", 1)[0] if "." in eid else "")
                        if dom not in ("light", "switch", "cover"):
                            continue
                        eids.append(eid)
                        domains[eid] = dom
                    if not eids:
                        await asyncio.sleep(interval)
                        continue

                    raw = await asyncio.to_thread(_ha_request, "GET", "/api/states", payload=None, timeout_s=10)
                    if not isinstance(raw, list):
                        await asyncio.sleep(interval)
                        continue
                    by_eid: dict[str, dict[str, Any]] = {}
                    for st in raw:
                        if not isinstance(st, dict):
                            continue
                        eid = str(st.get("entity_id") or "").strip().lower()
                        if eid in domains:
                            by_eid[eid] = st

                    last: dict[str, Any] = getattr(api.state, "ha_states", {}) or {}
                    last_caps: dict[str, Any] = getattr(api.state, "ha_caps", {}) or {}
                    next_states: dict[str, Any] = dict(last)
                    next_caps: dict[str, Any] = dict(last_caps)
                    caps_changed = False

                    for eid in eids:
                        st = by_eid.get(eid)
                        if not st:
                            continue
                        dom = domains.get(eid) or "light"

                        fn = _ha_friendly_name(st)
                        if fn:
                            prevn = ""
                            if isinstance(last_caps.get(eid), dict):
                                prevn = str((last_caps.get(eid) or {}).get("name") or "")
                            if prevn != fn:
                                next_caps[eid] = dict(next_caps.get(eid) or {})
                                next_caps[eid]["name"] = fn
                                caps_changed = True

                        if dom == "light":
                            dim = _ha_light_is_dimmable(st)
                            prevd = None
                            if isinstance(last_caps.get(eid), dict):
                                prevd = (last_caps.get(eid) or {}).get("dimmable")
                            if prevd is None or bool(prevd) != bool(dim):
                                next_caps[eid] = dict(next_caps.get(eid) or {})
                                next_caps[eid]["dimmable"] = bool(dim)
                                caps_changed = True
                        if dom == "cover":
                            mapped = _map_ha_state_to_cover(st)
                            prev = last.get(eid)
                            if prev != mapped:
                                next_states[eid] = mapped
                                await hub.broadcast("ha_cover_state", mapped)
                        elif dom == "switch":
                            mapped = _map_ha_state_to_switch(st)
                            prev = last.get(eid)
                            if prev != mapped:
                                next_states[eid] = mapped
                                await hub.broadcast("ha_switch_state", mapped)
                        else:
                            mapped = _map_ha_state_to_light(st)
                            prev = last.get(eid)
                            if prev != mapped:
                                next_states[eid] = mapped
                                await hub.broadcast("ha_light_state", mapped)

                    api.state.ha_states = next_states
                    api.state.ha_caps = next_caps
                    if caps_changed:
                        await _broadcast_devices()
                    await asyncio.sleep(interval)
                except asyncio.CancelledError:
                    return
                except Exception:
                    continue

        try:
            api.state.ha_poll_task = asyncio.create_task(_ha_poll_loop())
        except Exception:
            api.state.ha_poll_task = None

        # Best-effort icon sync on boot (non-blocking)
        asyncio.create_task(_sync_icons_for_devices(store.list_devices()))
        asyncio.create_task(_sync_icons_for_cover_groups(store.list_cover_groups()))
        asyncio.create_task(_sync_icons_for_hub_links(store.list_hub_links()))
        asyncio.create_task(_sync_icons_for_hub_config({"hub_icons": store.get_hub_icons()}))
        asyncio.create_task(_sync_icons_for_ha_devices(store.list_ha_devices()))

        # publish stored retained states (so HA/UI have last-known values after reboot)
        for k, v in store.get_states().items():
            try:
                if isinstance(k, str) and k.startswith("light:"):
                    addr = k.split(":", 1)[1]
                    subnet_s, dev_s, ch_s = addr.split(".")
                    topic = f"{settings.mqtt.base_topic}/state/light/{int(subnet_s)}/{int(dev_s)}/{int(ch_s)}"
                    mqtt.publish(topic, v, retain=True)
                if isinstance(k, str) and k.startswith("cover:"):
                    addr = k.split(":", 1)[1]
                    subnet_s, dev_s, ch_s = addr.split(".")
                    st = v or {}
                    if isinstance(st, dict):
                        if "state" in st:
                            mqtt.publish(f"{settings.mqtt.base_topic}/state/cover_state/{int(subnet_s)}/{int(dev_s)}/{int(ch_s)}", str(st.get("state") or ""), retain=True)
                        if st.get("position") is not None:
                            mqtt.publish(f"{settings.mqtt.base_topic}/state/cover_pos/{int(subnet_s)}/{int(dev_s)}/{int(ch_s)}", str(int(st.get("position"))), retain=True)
                if isinstance(k, str) and k.startswith("cover_group:"):
                    gid = k.split(":", 1)[1]
                    st = v or {}
                    if isinstance(st, dict):
                        if "state" in st:
                            mqtt.publish(f"{settings.mqtt.base_topic}/state/cover_group_state/{gid}", str(st.get("state") or ""), retain=True)
                        if st.get("position") is not None:
                            mqtt.publish(f"{settings.mqtt.base_topic}/state/cover_group_pos/{gid}", str(int(st.get("position"))), retain=True)
                if isinstance(k, str) and k.startswith("temp:"):
                    addr = k.split(":", 1)[1]
                    subnet_s, dev_s, ch_s = addr.split(".")
                    st = v or {}
                    if isinstance(st, dict) and st.get("value") is not None:
                        mqtt.publish(
                            f"{settings.mqtt.base_topic}/state/temp/{int(subnet_s)}/{int(dev_s)}/{int(ch_s)}",
                            str(float(st.get("value"))),
                            retain=True,
                        )
                if isinstance(k, str) and k.startswith("humidity:"):
                    addr = k.split(":", 1)[1]
                    subnet_s, dev_s, ch_s = addr.split(".")
                    st = v or {}
                    if isinstance(st, dict) and st.get("value") is not None:
                        mqtt.publish(
                            f"{settings.mqtt.base_topic}/state/humidity/{int(subnet_s)}/{int(dev_s)}/{int(ch_s)}",
                            str(float(st.get("value"))),
                            retain=True,
                        )
                if isinstance(k, str) and k.startswith("illuminance:"):
                    addr = k.split(":", 1)[1]
                    subnet_s, dev_s, ch_s = addr.split(".")
                    st = v or {}
                    if isinstance(st, dict) and st.get("value") is not None:
                        mqtt.publish(
                            f"{settings.mqtt.base_topic}/state/illuminance/{int(subnet_s)}/{int(dev_s)}/{int(ch_s)}",
                            str(float(st.get("value"))),
                            retain=True,
                        )
                if isinstance(k, str) and k.startswith("dry_contact:"):
                    addr = k.split(":", 1)[1]
                    subnet_s, dev_s, ch_s = addr.split(".")
                    st = v or {}
                    if isinstance(st, dict) and st.get("state") is not None:
                        mqtt.publish(
                            f"{settings.mqtt.base_topic}/state/dry_contact/{int(subnet_s)}/{int(dev_s)}/{int(ch_s)}",
                            str(st.get("state") or ""),
                            retain=True,
                        )
            except Exception:
                pass

        # (re)publish discovery
        await _republish_discovery()
        # Subscribe to light command topics
        mqtt.subscribe(f"{settings.mqtt.base_topic}/cmd/light/+/+/+")
        mqtt.subscribe(f"{settings.mqtt.base_topic}/cmd/light_scenario/+")
        mqtt.subscribe(f"{settings.mqtt.base_topic}/cmd/cover/+/+/+")
        mqtt.subscribe(f"{settings.mqtt.base_topic}/cmd/cover_raw/+/+/+")
        mqtt.subscribe(f"{settings.mqtt.base_topic}/cmd/cover_pos/+/+/+")
        mqtt.subscribe(f"{settings.mqtt.base_topic}/cmd/cover_group/+")
        mqtt.subscribe(f"{settings.mqtt.base_topic}/cmd/cover_group_raw/+")
        mqtt.subscribe(f"{settings.mqtt.base_topic}/cmd/cover_group_pos/+")

        def _on_mqtt_message(topic: str, payload: str) -> None:
            try:
                parts = topic.split("/")
                if len(parts) < 4:
                    return

                kind2 = parts[-2]
                if kind2 == "light_scenario":
                    sid = parts[-1]
                    asyncio.run_coroutine_threadsafe(run_light_scenario(scenario_id=sid), loop)
                    return
                if kind2 == "cover_group":
                    gid = parts[-1]
                    cmd = payload.strip().upper()
                    if cmd in ("OPEN", "CLOSE", "STOP"):
                        asyncio.run_coroutine_threadsafe(_run_cover_group_command(gid, cmd), loop)
                    return
                if kind2 == "cover_group_raw":
                    gid = parts[-1]
                    cmd = payload.strip().upper()
                    if cmd in ("OPEN", "CLOSE", "STOP"):
                        asyncio.run_coroutine_threadsafe(_run_cover_group_command(gid, cmd, raw=True), loop)
                    return
                if kind2 == "cover_group_pos":
                    gid = parts[-1]
                    s = payload.strip()
                    if s and s[0] == "{":
                        obj = json.loads(s)
                        pos = int(obj.get("position"))
                    else:
                        pos = int(float(s))
                    asyncio.run_coroutine_threadsafe(_run_cover_group_command(gid, "SET_POSITION", pos=pos), loop)
                    return

                # topic: base/cmd/light/subnet/device/channel
                if len(parts) < 6:
                    return
                kind = parts[-4]
                subnet = int(parts[-3])
                did = int(parts[-2])
                ch = int(parts[-1])
                if kind == "light":
                    on, br = _parse_light_cmd(payload)
                    asyncio.run_coroutine_threadsafe(
                        gateway.set_light(subnet_id=subnet, device_id=did, channel=ch, on=on, brightness255=br),
                        loop,
                    )
                elif kind == "cover":
                    cmd = payload.strip().upper()
                    if cmd == "OPEN":
                        asyncio.run_coroutine_threadsafe(gateway.cover_open(subnet_id=subnet, device_id=did, channel=ch), loop)
                    elif cmd == "CLOSE":
                        asyncio.run_coroutine_threadsafe(gateway.cover_close(subnet_id=subnet, device_id=did, channel=ch), loop)
                    elif cmd == "STOP":
                        asyncio.run_coroutine_threadsafe(gateway.cover_stop(subnet_id=subnet, device_id=did, channel=ch), loop)
                elif kind == "cover_raw":
                    cmd = payload.strip().upper()
                    if cmd == "OPEN":
                        asyncio.run_coroutine_threadsafe(gateway.cover_open_raw(subnet_id=subnet, device_id=did, channel=ch), loop)
                    elif cmd == "CLOSE":
                        asyncio.run_coroutine_threadsafe(gateway.cover_close_raw(subnet_id=subnet, device_id=did, channel=ch), loop)
                    elif cmd == "STOP":
                        asyncio.run_coroutine_threadsafe(gateway.cover_stop(subnet_id=subnet, device_id=did, channel=ch), loop)
                elif kind == "cover_pos":
                    s = payload.strip()
                    if s and s[0] == "{":
                        obj = json.loads(s)
                        pos = int(obj.get("position"))
                    else:
                        pos = int(float(s))
                    asyncio.run_coroutine_threadsafe(gateway.cover_set_position(subnet_id=subnet, device_id=did, channel=ch, position=pos), loop)
            except Exception:
                return

        mqtt.set_message_handler(_on_mqtt_message)

    @api.on_event("shutdown")
    async def _shutdown() -> None:
        try:
            mqtt.publish(f"{settings.mqtt.base_topic}/availability", "offline", retain=True)
        finally:
            mqtt.disconnect()

        poll = getattr(api.state, "poll_task", None)
        if poll is not None:
            poll.cancel()
        ha_poll = getattr(api.state, "ha_poll_task", None)
        if ha_poll is not None:
            ha_poll.cancel()

        gw: BusproGateway | None = api.state.gateway
        if gw is not None:
            await gw.stop()

        try:
            api.state.sniffer.stop()
        except Exception:
            pass

        await hub.close_all()

    @api.get("/health")
    async def health():
        return {"status": "ok"}

    def _server_port(scope: dict[str, Any]) -> int | None:
        try:
            return int((scope.get("server") or ("", 0))[1])
        except Exception:
            return None

    @api.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        # Home Assistant "Open Web UI" via Ingress should show Admin UI.
        try:
            headers = {k.lower(): v for k, v in request.headers.items()}
            if _is_ingress_headers(headers):
                index_path = os.path.join(static_dir, "index.html")
                with open(index_path, "r", encoding="utf-8") as f:
                    html = f.read()
                resp = HTMLResponse(content=html)
                try:
                    resp.set_cookie("buspro_ingress", "1", path="/", samesite="lax")
                except Exception:
                    pass
                return resp
        except Exception:
            pass
        port = _server_port(request.scope)
        if port == USER_PORT:
            # default user landing
            return await user_home()
        index_path = os.path.join(static_dir, "index.html")
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()

    @api.get("/index.html", response_class=HTMLResponse)
    async def index_html(request: Request):
        # Used by Ingress entry to avoid double-slash URLs (…/hassio_ingress/<token>//).
        index_path = os.path.join(static_dir, "index.html")
        with open(index_path, "r", encoding="utf-8") as f:
            html = f.read()
        resp = HTMLResponse(content=html)
        try:
            headers = {k.lower(): v for k, v in request.headers.items()}
            if _is_ingress_headers(headers):
                resp.set_cookie("buspro_ingress", "1", path="/", samesite="lax")
        except Exception:
            pass
        return resp

    @api.get("/home", response_class=HTMLResponse)
    async def user_home():
        p = os.path.join(static_dir, "user", "home.html")
        with open(p, "r", encoding="utf-8") as f:
            return f.read()

    @api.get("/home2", response_class=HTMLResponse)
    async def user_home2():
        p = os.path.join(static_dir, "user", "home2.html")
        with open(p, "r", encoding="utf-8") as f:
            return f.read()

    @api.get("/lights", response_class=HTMLResponse)
    async def user_lights():
        p = os.path.join(static_dir, "user", "lights.html")
        with open(p, "r", encoding="utf-8") as f:
            return f.read()

    @api.get("/scenarios", response_class=HTMLResponse)
    async def user_scenarios():
        p = os.path.join(static_dir, "user", "scenarios.html")
        with open(p, "r", encoding="utf-8") as f:
            return f.read()

    @api.get("/covers", response_class=HTMLResponse) 
    async def user_covers(): 
        p = os.path.join(static_dir, "user", "covers.html") 
        with open(p, "r", encoding="utf-8") as f: 
            return f.read() 

    @api.get("/extra", response_class=HTMLResponse)
    async def user_extra():
        p = os.path.join(static_dir, "user", "extra.html")
        with open(p, "r", encoding="utf-8") as f:
            return f.read()

    @api.get("/api/options")
    async def api_options():
        return read_options()

    @api.get("/api/meta")
    async def api_meta(): 
        return {
            "version": ADDON_VERSION,
            "group_order": store.get_group_order(),
            "hub_links": store.list_visible_hub_links(),
            "hub_icons": store.get_hub_icons(),
            "hub_show": store.get_hub_show(),
            "hub_order": store.get_hub_order(),
        } 

    @api.get("/api/user/devices")
    async def api_user_devices():
        return _list_user_devices()

    @api.get("/api/ui") 
    async def api_ui(): 
        return {"group_order": store.get_group_order()} 

    @api.put("/api/ui") 
    async def api_ui_update(payload: dict[str, Any]): 
        raw = payload.get("group_order")
        order: list[str] = []
        if isinstance(raw, str):
            order = [s for s in raw.splitlines()]
        elif isinstance(raw, list):
            order = [str(x) for x in raw]
        else:
            raise HTTPException(status_code=400, detail="group_order must be list or string")

        cleaned = store.set_group_order(order)
        await hub.broadcast("ui", {"group_order": cleaned})
        return {"group_order": cleaned}

    @api.get("/api/hub_links")
    async def api_hub_links_list():
        return {"links": store.list_hub_links()}

    @api.get("/api/proxy_targets")
    async def api_proxy_targets_list():
        # Admin-only via port gate
        return {"targets": store.list_proxy_targets()}

    @api.get("/api/pwa_config")
    async def api_pwa_config_get():
        # Admin-only via port gate (useful to edit title/icon/theme)
        return store.get_pwa_config()

    @api.put("/api/pwa_config")
    async def api_pwa_config_set(payload: dict[str, Any]):
        # Admin-only via port gate
        try:
            cfg = store.set_pwa_config(payload)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        await hub.broadcast("pwa_config", {"pwa": cfg})
        return cfg

    @api.post("/api/proxy_targets")
    async def api_proxy_targets_upsert(payload: dict[str, Any]):
        # Admin-only via port gate
        try:
            item = store.upsert_proxy_target(payload)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        await hub.broadcast("proxy_targets", {"targets": store.list_proxy_targets()})
        return item

    @api.delete("/api/proxy_targets/{name}")
    async def api_proxy_targets_delete(name: str):
        # Admin-only via port gate
        removed = store.delete_proxy_target(name=name)
        if not removed:
            raise HTTPException(status_code=404, detail="Not Found")
        await hub.broadcast("proxy_targets", {"targets": store.list_proxy_targets()})
        return {"ok": True}

    @api.get("/api/hub_config")
    async def api_hub_config_get():
        return {"hub_icons": store.get_hub_icons(), "hub_show": store.get_hub_show(), "hub_order": store.get_hub_order()}

    @api.put("/api/hub_config")
    async def api_hub_config_set(payload: dict[str, Any]):
        icons = payload.get("hub_icons", {})
        if not isinstance(icons, dict):
            raise HTTPException(status_code=400, detail="hub_icons must be an object")
        cleaned = store.set_hub_icons(icons)
        show = payload.get("hub_show", {})
        if not isinstance(show, dict):
            raise HTTPException(status_code=400, detail="hub_show must be an object")
        cleaned_show = store.set_hub_show(show)
        order_raw = payload.get("hub_order", None)
        if order_raw is None:
            cleaned_order = store.get_hub_order()
        elif not isinstance(order_raw, list):
            raise HTTPException(status_code=400, detail="hub_order must be a list")
        else:
            cleaned_order = store.set_hub_order(order_raw)
        asyncio.create_task(_sync_icons_for_hub_config({"hub_icons": cleaned}))
        await hub.broadcast("hub_config", {"hub_icons": cleaned, "hub_show": cleaned_show, "hub_order": cleaned_order})
        return {"hub_icons": cleaned, "hub_show": cleaned_show, "hub_order": cleaned_order}

    @api.get("/api/ha_devices")
    async def api_ha_devices_list():
        # Admin-only via port gate
        return {"items": store.list_ha_devices()}

    @api.post("/api/ha_devices")
    async def api_ha_devices_add(payload: dict[str, Any]):
        # Admin-only via port gate
        try:
            item = store.add_ha_device(payload)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        asyncio.create_task(_sync_icons_for_ha_devices(store.list_ha_devices()))
        await _broadcast_devices()
        return item

    @api.put("/api/ha_devices/{device_id}")
    async def api_ha_devices_update(device_id: str, payload: dict[str, Any]):
        # Admin-only via port gate
        try:
            item = store.update_ha_device(device_id=device_id, payload=payload)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        if item is None:
            raise HTTPException(status_code=404, detail="Not Found")
        asyncio.create_task(_sync_icons_for_ha_devices(store.list_ha_devices()))
        await _broadcast_devices()
        return item

    @api.delete("/api/ha_devices/{device_id}")
    async def api_ha_devices_delete(device_id: str):
        # Admin-only via port gate
        ok = store.delete_ha_device(device_id=device_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Not Found")
        asyncio.create_task(_sync_icons_for_ha_devices(store.list_ha_devices()))
        await _broadcast_devices()
        return {"ok": True}

    @api.post("/api/hub_links")
    async def api_hub_links_upsert(payload: dict[str, Any]):
        try:
            item = store.upsert_hub_link(payload)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        asyncio.create_task(_sync_icons_for_hub_links(store.list_hub_links()))
        await hub.broadcast("hub_links", {"links": store.list_hub_links()})
        await _republish_discovery()
        return item

    @api.put("/api/hub_links")
    async def api_hub_links_replace(payload: dict[str, Any]):
        links = payload.get("links", [])
        if not isinstance(links, list):
            raise HTTPException(status_code=400, detail="links must be a list")
        cleaned = store.set_hub_links(links)
        asyncio.create_task(_sync_icons_for_hub_links(cleaned))
        await hub.broadcast("hub_links", {"links": cleaned})
        await _republish_discovery()
        return {"links": cleaned}

    @api.delete("/api/hub_links/{link_id}")
    async def api_hub_links_delete(link_id: str):
        removed = store.delete_hub_link(link_id=link_id)
        if not removed:
            raise HTTPException(status_code=404, detail="Not Found")
        asyncio.create_task(_sync_icons_for_hub_links(store.list_hub_links()))
        await hub.broadcast("hub_links", {"links": store.list_hub_links()})
        await _republish_discovery()
        return {"ok": True}

    @api.post("/api/devices/dedupe")
    async def api_devices_dedupe():
        # Admin-only via port gate
        res = store.dedupe_devices()
        devices = store.list_devices()
        _rebuild_temp_index()
        _rebuild_humidity_index()
        _rebuild_illuminance_index()
        _rebuild_dry_contact_index()
        _rebuild_air_index()
        _rebuild_pir_index()
        _rebuild_ultrasonic_index()
        asyncio.create_task(_sync_icons_for_devices(devices))
        await _republish_discovery()
        await _broadcast_devices()
        return res

    def _mdi_names_from_devices(devices: list[dict[str, Any]]) -> list[str]:
        names: list[str] = []
        for d in devices:
            mdi = parse_mdi_icon(str(d.get("icon") or ""))
            if mdi:
                names.append(mdi)
        return names

    def _mdi_names_from_cover_groups(groups: list[dict[str, Any]]) -> list[str]:
        names: list[str] = []
        for g in groups:
            mdi = parse_mdi_icon(str(g.get("icon") or ""))
            if mdi:
                names.append(mdi)
        return names

    def _mdi_names_from_hub_links(links: list[dict[str, Any]]) -> list[str]:
        names: list[str] = []
        for it in links:
            mdi = parse_mdi_icon(str(it.get("icon") or ""))
            if mdi:
                names.append(mdi)
        return names

    def _mdi_names_from_hub_config(cfg: dict[str, Any]) -> list[str]:
        names: list[str] = []
        if not isinstance(cfg, dict):
            return names
        icons = cfg.get("hub_icons") if "hub_icons" in cfg else cfg
        if not isinstance(icons, dict):
            return names
        for k in ("lights", "scenarios", "covers", "extra"):
            mdi = parse_mdi_icon(str(icons.get(k) or ""))
            if mdi:
                names.append(mdi)
        return names

    def _mdi_names_from_ha_devices(items: list[dict[str, Any]]) -> list[str]:
        names: list[str] = []
        for it in items or []:
            mdi = parse_mdi_icon(str(it.get("icon") or ""))
            if mdi:
                names.append(mdi)
        return names

    async def _sync_icons_for_devices(devices: list[dict[str, Any]]) -> None:
        names = _mdi_names_from_devices(devices)
        if not names:
            return
        lock: asyncio.Lock = api.state.icon_lock
        icons_dir: str = api.state.icons_dir
        async with lock:
            try:
                await asyncio.to_thread(ensure_mdi_icons, icons_dir, names)
            except Exception:
                return

    async def _sync_icons_for_cover_groups(groups: list[dict[str, Any]]) -> None:
        names = _mdi_names_from_cover_groups(groups)
        if not names:
            return
        lock: asyncio.Lock = api.state.icon_lock
        icons_dir: str = api.state.icons_dir
        async with lock:
            try:
                await asyncio.to_thread(ensure_mdi_icons, icons_dir, names)
            except Exception:
                return

    async def _sync_icons_for_hub_links(links: list[dict[str, Any]]) -> None:
        names = _mdi_names_from_hub_links(links)
        if not names:
            return
        lock: asyncio.Lock = api.state.icon_lock
        icons_dir: str = api.state.icons_dir
        async with lock:
            try:
                await asyncio.to_thread(ensure_mdi_icons, icons_dir, names)
            except Exception:
                return

    async def _sync_icons_for_hub_config(cfg: dict[str, Any]) -> None:
        names = _mdi_names_from_hub_config(cfg)
        if not names:
            return
        lock: asyncio.Lock = api.state.icon_lock
        icons_dir: str = api.state.icons_dir
        async with lock:
            try:
                await asyncio.to_thread(ensure_mdi_icons, icons_dir, names)
            except Exception:
                return

    async def _sync_icons_for_ha_devices(items: list[dict[str, Any]]) -> None:
        names = _mdi_names_from_ha_devices(items)
        if not names:
            return
        lock: asyncio.Lock = api.state.icon_lock
        icons_dir: str = api.state.icons_dir
        async with lock:
            try:
                await asyncio.to_thread(ensure_mdi_icons, icons_dir, names)
            except Exception:
                return

    @api.get("/api/icons/mdi/{name}.svg") 
    async def mdi_icon(name: str): 
        # Always return something (placeholder if missing/offline)
        try:
            safe = parse_mdi_icon(f"mdi:{name}") or ""
            if safe:
                icons_dir: str = api.state.icons_dir
                path = os.path.join(icons_dir, "mdi", f"{safe}.svg")
                if os.path.exists(path):
                    with open(path, "rb") as f:
                        return Response(content=f.read(), media_type="image/svg+xml")
        except Exception:
            pass
        return Response(content=placeholder_svg(), media_type="image/svg+xml") 

    @api.get("/api/icons/used")
    async def used_icons():
        # Admin-only via port gate
        icons: set[str] = set()
        for d in store.list_devices():
            v = str(d.get("icon") or "").strip()
            mdi = parse_mdi_icon(v)
            if mdi:
                icons.add(f"mdi:{mdi}")
        for g in store.list_cover_groups():
            v = str(g.get("icon") or "").strip()
            mdi = parse_mdi_icon(v)
            if mdi:
                icons.add(f"mdi:{mdi}")
        for it in store.list_hub_links():
            v = str(it.get("icon") or "").strip()
            mdi = parse_mdi_icon(v)
            if mdi:
                icons.add(f"mdi:{mdi}")
        for v in store.get_hub_icons().values():
            mdi = parse_mdi_icon(str(v or ""))
            if mdi:
                icons.add(f"mdi:{mdi}")
        for it in store.list_ha_devices():
            mdi = parse_mdi_icon(str(it.get("icon") or ""))
            if mdi:
                icons.add(f"mdi:{mdi}")
        return {"icons": sorted(icons)}

    @api.get("/api/backup")
    async def api_backup():
        # Admin-only via port gate
        return {"text": store.export_backup_text()}

    @api.get("/api/backup/file")
    async def api_backup_file():
        # Admin-only via port gate
        content = store.export_backup_text()
        ts = time.strftime("%Y%m%d-%H%M%S")
        headers = {"Content-Disposition": f'attachment; filename="buspro_backup_{ts}.json"'}
        return Response(content=content, media_type="text/plain; charset=utf-8", headers=headers)

    @api.get("/api/sniffer/status")
    async def api_sniffer_status():
        return api.state.sniffer.status()

    @api.post("/api/sniffer/start")
    async def api_sniffer_start(payload: dict[str, Any]):
        # Admin-only via port gate
        ops_raw = payload.get("op_contains")
        if isinstance(ops_raw, str):
            ops = [s.strip() for s in ops_raw.split(",") if s.strip()]
        elif isinstance(ops_raw, list):
            ops = [str(s).strip() for s in ops_raw if str(s).strip()]
        else:
            ops = []

        src = payload.get("src")
        dst = payload.get("dst")
        include_raw = bool(payload.get("include_raw", False))
        write_file = bool(payload.get("write_file", True))
        filename = payload.get("filename")
        clear = bool(payload.get("clear", False))

        api.state.sniffer.start(
            op_contains=ops or None,
            src=src if isinstance(src, list) else None,
            dst=dst if isinstance(dst, list) else None,
            include_raw=include_raw,
            write_file=write_file,
            filename=str(filename).strip() if filename is not None else None,
            clear=clear,
        )
        return api.state.sniffer.status()

    @api.post("/api/sniffer/stop")
    async def api_sniffer_stop():
        api.state.sniffer.stop()
        return api.state.sniffer.status()

    @api.post("/api/sniffer/clear")
    async def api_sniffer_clear():
        api.state.sniffer.clear()
        return api.state.sniffer.status()

    @api.get("/api/sniffer/file")
    async def api_sniffer_file():
        st = api.state.sniffer.status()
        path = st.get("file_path")
        if isinstance(path, str) and path and os.path.exists(path):
            headers = {"Content-Disposition": f'attachment; filename="{os.path.basename(path)}"'}
            return FileResponse(path, media_type="application/x-ndjson; charset=utf-8", headers=headers)
        content = api.state.sniffer.dump_jsonl()
        ts = time.strftime("%Y%m%d-%H%M%S")
        headers = {"Content-Disposition": f'attachment; filename="buspro_sniffer_buffer_{ts}.jsonl"'}
        return Response(content=content, media_type="application/x-ndjson; charset=utf-8", headers=headers)

    @api.get("/api/sniffer/recent")
    async def api_sniffer_recent(limit: int = 50):
        try:
            return {"items": api.state.sniffer.recent(limit=limit), "status": api.state.sniffer.status()}
        except Exception:
            return {"items": [], "status": api.state.sniffer.status()}

    @api.post("/api/restore")
    async def api_restore(payload: dict[str, Any]):
        # Admin-only via port gate
        text = payload.get("text")
        data = payload.get("data")
        backup_path = store.backup_current()
        try:
            if isinstance(text, str) and text.strip():
                cleaned = _clean_backup_text(text)
                if not cleaned:
                    raise HTTPException(status_code=400, detail="Empty backup text")
                state = json.loads(cleaned)
            elif isinstance(data, dict):
                state = data
            else:
                raise HTTPException(status_code=400, detail="Provide 'text' or 'data'")
            store.import_backup(state)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

        devices = store.list_devices()
        _rebuild_temp_index()
        _rebuild_humidity_index()
        _rebuild_illuminance_index()
        _rebuild_dry_contact_index()
        _rebuild_air_index()
        _rebuild_pir_index()
        _rebuild_ultrasonic_index()
        asyncio.create_task(_sync_icons_for_devices(devices))
        asyncio.create_task(_sync_icons_for_cover_groups(store.list_cover_groups()))
        await _republish_discovery()
        await _broadcast_devices()
        await hub.broadcast("ui", {"group_order": store.get_group_order()})
        return {"ok": True, "backup_path": backup_path}

    @api.get("/api/cover_groups")
    async def api_cover_groups():
        return {"groups": store.list_cover_groups()}

    @api.post("/api/cover_groups")
    async def api_cover_groups_upsert(payload: dict[str, Any]):
        gid_in = payload.get("id")
        name = str(payload.get("name") or "").strip()
        members = payload.get("members") or []
        icon = payload.get("icon")
        if not name:
            raise HTTPException(status_code=400, detail="Missing: name")
        if not isinstance(members, list):
            raise HTTPException(status_code=400, detail="members must be a list")
        members_s = [str(m or "").strip() for m in members if str(m or "").strip()]
        g = store.upsert_cover_group(
            group_id=str(gid_in).strip() if gid_in is not None else None,
            name=name,
            members=members_s,
            icon=str(icon).strip() if icon is not None else None,
        )
        _rebuild_cover_group_index()
        _publish_all_cover_group_states()
        asyncio.create_task(_sync_icons_for_cover_groups([g]))
        await _republish_discovery()
        await hub.broadcast("cover_groups", {"groups": store.list_cover_groups()})
        return g

    @api.delete("/api/cover_groups/{name}")
    async def api_cover_groups_delete(name: str):
        nm = str(name or "").strip()
        if not nm:
            raise HTTPException(status_code=400, detail="name required")

        # Accept both id and name in path
        existing = store.get_cover_group(nm)
        if existing is None:
            raise HTTPException(status_code=404, detail="Group not found")

        gid = str(existing.get("id") or "").strip() or slugify(str(existing.get("name") or ""))
        nm = str(existing.get("name") or nm).strip()

        ok = store.delete_cover_group(gid)
        if not ok:
            raise HTTPException(status_code=404, detail="Group not found")

        # Clear retained discovery/state
        mqtt.publish(_cover_group_config_topic(gid=gid), "", retain=True)
        mqtt.publish(f"{settings.mqtt.base_topic}/state/cover_group_state/{gid}", "", retain=True)
        mqtt.publish(f"{settings.mqtt.base_topic}/state/cover_group_pos/{gid}", "", retain=True)
        store.delete_cover_group_state(group_id=gid)

        _rebuild_cover_group_index()
        _publish_all_cover_group_states()
        await _republish_discovery()
        await hub.broadcast("cover_groups", {"groups": store.list_cover_groups()})
        return {"ok": True}

    @api.post("/api/control/cover_group/{gid}")
    async def api_control_cover_group(gid: str, payload: dict[str, Any]):
        cmd = str(payload.get("command") or payload.get("cmd") or "").strip().upper()
        if cmd not in ("OPEN", "CLOSE", "STOP", "SET_POSITION"):
            raise HTTPException(status_code=400, detail="command must be OPEN/CLOSE/STOP/SET_POSITION")
        pos: int | None = None
        if cmd == "SET_POSITION":
            try:
                pos = int(payload.get("position"))
            except Exception:
                raise HTTPException(status_code=400, detail="position required for SET_POSITION")

        gw: BusproGateway | None = api.state.gateway
        if gw is None:
            raise HTTPException(status_code=503, detail="gateway not ready")

        t0 = time.time()
        await _run_cover_group_command(str(gid or "").strip(), cmd, pos=pos)
        _LOGGER.debug("cover_group control gid=%s cmd=%s took=%.3fs", gid, cmd, time.time() - t0)
        return {"ok": True}

    @api.post("/api/icons/sync")
    async def sync_icons():
        # Admin-only via port gate; safe to call multiple times.
        devices = store.list_devices()
        names = _mdi_names_from_devices(devices) + _mdi_names_from_cover_groups(store.list_cover_groups())
        lock: asyncio.Lock = api.state.icon_lock
        icons_dir: str = api.state.icons_dir
        async with lock:
            res = await asyncio.to_thread(ensure_mdi_icons, icons_dir, names)
        return {
            "requested": res.requested,
            "downloaded": res.downloaded,
            "failed": res.failed,
            "missing": res.missing,
        }

    @api.get("/api/devices")
    async def list_devices():
        return store.list_devices()

    @api.post("/api/devices") 
    async def add_device(payload: dict[str, Any]): 
        required = ("name", "subnet_id", "device_id", "channel", "dimmable")
        missing = [k for k in required if k not in payload]
        if missing:
            raise HTTPException(status_code=400, detail=f"Missing: {', '.join(missing)}")

        subnet_id = int(payload["subnet_id"])
        device_id = int(payload["device_id"])
        channel = int(payload["channel"])
        if store.find_device(type_="light", subnet_id=subnet_id, device_id=device_id, channel=channel) is not None:
            raise HTTPException(status_code=409, detail="Device already exists with same address")

        device = { 
            "name": str(payload["name"]), 
            "subnet_id": subnet_id, 
            "device_id": device_id, 
            "channel": channel, 
            "dimmable": bool(payload["dimmable"]), 
            "type": "light", 
        } 
        icon = payload.get("icon")
        if icon:
            device["icon"] = str(icon)
        category = payload.get("category") 
        if category: 
            device["category"] = str(category) 
        group = payload.get("group")
        if group is not None:
            g = str(group).strip()
            if g.startswith("#"):
                g = g[1:].strip()
            if g:
                device["group"] = g
        store.add_device(device) 
        asyncio.create_task(_sync_icons_for_devices([device])) 

        gw: BusproGateway | None = api.state.gateway
        if gw is not None:
            gw.ensure_light(
                subnet_id=device["subnet_id"],
                device_id=device["device_id"],
                channel=device["channel"],
                name=device["name"],
            )
            await gw.read_light_status(
                subnet_id=device["subnet_id"],
                device_id=device["device_id"],
                channel=device["channel"],
            )

        await _republish_discovery()
        await _broadcast_devices()
        return device

    @api.post("/api/devices/cover") 
    async def add_cover(payload: dict[str, Any]): 
        required = ("name", "subnet_id", "device_id", "channel")
        missing = [k for k in required if k not in payload]
        if missing:
            raise HTTPException(status_code=400, detail=f"Missing: {', '.join(missing)}")

        subnet_id = int(payload["subnet_id"])
        device_id = int(payload["device_id"])
        channel = int(payload["channel"])
        if store.find_device(type_="cover", subnet_id=subnet_id, device_id=device_id, channel=channel) is not None:
            raise HTTPException(status_code=409, detail="Device already exists with same address")

        device = { 
            "name": str(payload["name"]), 
            "subnet_id": subnet_id, 
            "device_id": device_id, 
            "channel": channel, 
            "type": "cover", 
            "opening_time_up": int(payload.get("opening_time_up") or 20), 
            "opening_time_down": int(payload.get("opening_time_down") or 20), 
            "start_delay_s": float(payload.get("start_delay_s") or 0.0),
        } 
        if "reverse_icon" in payload:
            device["reverse_icon"] = bool(payload.get("reverse_icon"))
        icon = payload.get("icon")
        if icon:
            device["icon"] = str(icon)
        category = payload.get("category") 
        if category: 
            device["category"] = str(category) 
        group = payload.get("group")
        if group is not None:
            g = str(group).strip()
            if g.startswith("#"):
                g = g[1:].strip()
            if g:
                device["group"] = g

        store.add_device(device) 
        asyncio.create_task(_sync_icons_for_devices([device])) 

        gw: BusproGateway | None = api.state.gateway
        if gw is not None:
            gw.ensure_cover(
                subnet_id=device["subnet_id"],
                device_id=device["device_id"],
                channel=device["channel"],
                name=device["name"],
                opening_time_up=device["opening_time_up"],
                opening_time_down=device["opening_time_down"],
                start_delay_s=float(device.get("start_delay_s") or 0.0),
            )
            await gw.read_cover_status(subnet_id=device["subnet_id"], device_id=device["device_id"], channel=device["channel"])

        await _republish_discovery()
        await _broadcast_devices()
        return device

    def _temp_config_topic(*, subnet_id: int, device_id: int, sensor_id: int) -> str:
        nid = f"buspro_{settings.gateway.host.replace('.', '_')}_{settings.gateway.port}"
        oid = f"temp_{int(subnet_id)}_{int(device_id)}_{int(sensor_id)}"
        return f"{settings.mqtt.discovery_prefix}/sensor/{nid}/{oid}/config"

    def _humidity_config_topic(*, subnet_id: int, device_id: int, sensor_id: int) -> str:
        nid = f"buspro_{settings.gateway.host.replace('.', '_')}_{settings.gateway.port}"
        oid = f"humidity_{int(subnet_id)}_{int(device_id)}_{int(sensor_id)}"
        return f"{settings.mqtt.discovery_prefix}/sensor/{nid}/{oid}/config"

    def _illuminance_config_topic(*, subnet_id: int, device_id: int, sensor_id: int) -> str:
        nid = f"buspro_{settings.gateway.host.replace('.', '_')}_{settings.gateway.port}"
        oid = f"illuminance_{int(subnet_id)}_{int(device_id)}_{int(sensor_id)}"
        return f"{settings.mqtt.discovery_prefix}/sensor/{nid}/{oid}/config"

    def _air_quality_config_topic(*, subnet_id: int, device_id: int, sensor_id: int) -> str:
        nid = f"buspro_{settings.gateway.host.replace('.', '_')}_{settings.gateway.port}"
        oid = f"air_quality_{int(subnet_id)}_{int(device_id)}_{int(sensor_id)}"
        return f"{settings.mqtt.discovery_prefix}/sensor/{nid}/{oid}/config"

    def _gas_percent_config_topic(*, subnet_id: int, device_id: int, sensor_id: int) -> str:
        nid = f"buspro_{settings.gateway.host.replace('.', '_')}_{settings.gateway.port}"
        oid = f"gas_percent_{int(subnet_id)}_{int(device_id)}_{int(sensor_id)}"
        return f"{settings.mqtt.discovery_prefix}/sensor/{nid}/{oid}/config"

    def _dry_contact_config_topic(*, subnet_id: int, device_id: int, input_id: int) -> str:
        nid = f"buspro_{settings.gateway.host.replace('.', '_')}_{settings.gateway.port}"
        oid = f"dry_contact_{int(subnet_id)}_{int(device_id)}_{int(input_id)}"
        return f"{settings.mqtt.discovery_prefix}/binary_sensor/{nid}/{oid}/config"

    def _pir_config_topic(*, subnet_id: int, device_id: int, sensor_id: int) -> str:
        nid = f"buspro_{settings.gateway.host.replace('.', '_')}_{settings.gateway.port}"
        oid = f"pir_{int(subnet_id)}_{int(device_id)}_{int(sensor_id)}"
        return f"{settings.mqtt.discovery_prefix}/binary_sensor/{nid}/{oid}/config"

    def _ultrasonic_config_topic(*, subnet_id: int, device_id: int, sensor_id: int) -> str:
        nid = f"buspro_{settings.gateway.host.replace('.', '_')}_{settings.gateway.port}"
        oid = f"ultrasonic_{int(subnet_id)}_{int(device_id)}_{int(sensor_id)}"
        return f"{settings.mqtt.discovery_prefix}/binary_sensor/{nid}/{oid}/config"

    @api.get("/api/temp/states")
    async def api_temp_states():
        # Admin-only via port gate
        return {"states": store.get_temp_states()}

    @api.get("/api/humidity/states")
    async def api_humidity_states():
        # Admin-only via port gate
        return {"states": store.get_humidity_states()}

    @api.get("/api/illuminance/states")
    async def api_illuminance_states():
        # Admin-only via port gate
        return {"states": store.get_illuminance_states()}

    @api.get("/api/air/states")
    async def api_air_states():
        # Admin-only via port gate
        return {"air_quality_states": store.get_air_quality_states(), "gas_percent_states": store.get_gas_percent_states()}

    @api.get("/api/dry_contact/states")
    async def api_dry_contact_states():
        # Admin-only via port gate
        return {"states": store.get_dry_contact_states()}

    @api.get("/api/presence/states")
    async def api_presence_states():
        # Admin-only via port gate
        return {"pir_states": store.get_pir_states(), "ultrasonic_states": store.get_ultrasonic_states()}

    @api.post("/api/devices/temp")
    async def add_temp(payload: dict[str, Any]):
        required = ("name", "subnet_id", "device_id")
        missing = [k for k in required if k not in payload]
        if missing:
            raise HTTPException(status_code=400, detail=f"Missing: {', '.join(missing)}")

        sensor_id = payload.get("sensor_id", payload.get("channel"))
        if sensor_id is None:
            raise HTTPException(status_code=400, detail="Missing: sensor_id")

        subnet_id = int(payload["subnet_id"])
        device_id = int(payload["device_id"])
        channel = int(sensor_id)
        if store.find_device(type_="temp", subnet_id=subnet_id, device_id=device_id, channel=channel) is not None:
            raise HTTPException(status_code=409, detail="Device already exists with same address")

        device: dict[str, Any] = {
            "name": str(payload["name"]),
            "subnet_id": subnet_id,
            "device_id": device_id,
            "channel": channel,
            "type": "temp",
        }

        # Optional config
        if payload.get("decimals") is not None:
            try:
                device["decimals"] = max(0, min(3, int(payload.get("decimals"))))  # 0..3
            except Exception:
                device["decimals"] = 1
        if payload.get("min_value") is not None:
            try:
                device["min_value"] = float(payload.get("min_value"))
            except Exception:
                pass
        if payload.get("max_value") is not None:
            try:
                device["max_value"] = float(payload.get("max_value"))
            except Exception:
                pass

        icon = payload.get("icon")
        if icon:
            device["icon"] = str(icon)
        category = payload.get("category")
        if category:
            device["category"] = str(category)
        group = payload.get("group")
        if group is not None:
            g = str(group).strip()
            if g.startswith("#"):
                g = g[1:].strip()
            if g:
                device["group"] = g

        # Optional decoding (for 12-in-1 style sensors that send 2-byte temperature payloads)
        tf = payload.get("temp_format", payload.get("format"))
        if tf is not None:
            tf_s = str(tf).strip()
            if tf_s:
                device["temp_format"] = tf_s
        if payload.get("temp_scale") is not None:
            try:
                device["temp_scale"] = float(payload.get("temp_scale"))
            except Exception:
                pass
        if payload.get("temp_offset") is not None:
            try:
                device["temp_offset"] = float(payload.get("temp_offset"))
            except Exception:
                pass

        store.add_device(device)
        _rebuild_temp_index()
        asyncio.create_task(_sync_icons_for_devices([device]))

        await _republish_discovery()
        await _broadcast_devices()
        return device

    @api.post("/api/devices/humidity")
    async def add_humidity(payload: dict[str, Any]):
        required = ("name", "subnet_id", "device_id")
        missing = [k for k in required if k not in payload]
        if missing:
            raise HTTPException(status_code=400, detail=f"Missing: {', '.join(missing)}")

        subnet_id = int(payload["subnet_id"])
        device_id = int(payload["device_id"])
        sensor_id = payload.get("sensor_id", payload.get("channel", 0))
        channel = int(sensor_id) if sensor_id is not None else 0

        if store.find_device(type_="humidity", subnet_id=subnet_id, device_id=device_id, channel=channel) is not None:
            raise HTTPException(status_code=409, detail="Device already exists with same address")

        device: dict[str, Any] = {
            "name": str(payload["name"]),
            "subnet_id": subnet_id,
            "device_id": device_id,
            "channel": channel,
            "type": "humidity",
        }

        # Optional config
        if payload.get("decimals") is not None:
            try:
                device["decimals"] = max(0, min(3, int(payload.get("decimals"))))  # 0..3
            except Exception:
                device["decimals"] = 0
        if payload.get("min_value") is not None:
            try:
                device["min_value"] = float(payload.get("min_value"))
            except Exception:
                pass
        if payload.get("max_value") is not None:
            try:
                device["max_value"] = float(payload.get("max_value"))
            except Exception:
                pass

        icon = payload.get("icon")
        if icon:
            device["icon"] = str(icon)
        category = payload.get("category")
        if category:
            device["category"] = str(category)
        group = payload.get("group")
        if group is not None:
            g = str(group).strip()
            if g.startswith("#"):
                g = g[1:].strip()
            if g:
                device["group"] = g

        store.add_device(device)
        _rebuild_humidity_index()
        asyncio.create_task(_sync_icons_for_devices([device]))

        await _republish_discovery()
        await _broadcast_devices()
        return device

    @api.post("/api/devices/illuminance")
    async def add_illuminance(payload: dict[str, Any]):
        required = ("name", "subnet_id", "device_id")
        missing = [k for k in required if k not in payload]
        if missing:
            raise HTTPException(status_code=400, detail=f"Missing: {', '.join(missing)}")

        subnet_id = int(payload["subnet_id"])
        device_id = int(payload["device_id"])
        sensor_id = payload.get("sensor_id", payload.get("channel", 0))
        channel = int(sensor_id) if sensor_id is not None else 0

        if store.find_device(type_="illuminance", subnet_id=subnet_id, device_id=device_id, channel=channel) is not None:
            raise HTTPException(status_code=409, detail="Device already exists with same address")

        device: dict[str, Any] = {
            "name": str(payload["name"]),
            "subnet_id": subnet_id,
            "device_id": device_id,
            "channel": channel,
            "type": "illuminance",
        }

        # Optional config
        if payload.get("decimals") is not None:
            try:
                device["decimals"] = max(0, min(3, int(payload.get("decimals"))))  # 0..3
            except Exception:
                device["decimals"] = 0
        if payload.get("min_value") is not None:
            try:
                device["min_value"] = float(payload.get("min_value"))
            except Exception:
                pass
        if payload.get("max_value") is not None:
            try:
                device["max_value"] = float(payload.get("max_value"))
            except Exception:
                pass

        if payload.get("lux_scale") is not None:
            try:
                device["lux_scale"] = float(payload.get("lux_scale"))
            except Exception:
                pass
        if payload.get("lux_offset") is not None:
            try:
                device["lux_offset"] = float(payload.get("lux_offset"))
            except Exception:
                pass

        icon = payload.get("icon")
        if icon:
            device["icon"] = str(icon)
        category = payload.get("category")
        if category:
            device["category"] = str(category)
        group = payload.get("group")
        if group is not None:
            g = str(group).strip()
            if g.startswith("#"):
                g = g[1:].strip()
            if g:
                device["group"] = g

        store.add_device(device)
        _rebuild_illuminance_index()
        asyncio.create_task(_sync_icons_for_devices([device]))

        await _republish_discovery()
        await _broadcast_devices()
        return device

    @api.post("/api/devices/air")
    async def add_air(payload: dict[str, Any]):
        required = ("name", "subnet_id", "device_id")
        missing = [k for k in required if k not in payload]
        if missing:
            raise HTTPException(status_code=400, detail=f"Missing: {', '.join(missing)}")

        subnet_id = int(payload["subnet_id"])
        device_id = int(payload["device_id"])
        sensor_id = payload.get("sensor_id", payload.get("channel", 248))
        channel = int(sensor_id) if sensor_id is not None else 248

        if store.find_device(type_="air", subnet_id=subnet_id, device_id=device_id, channel=channel) is not None:
            raise HTTPException(status_code=409, detail="Device already exists with same address")

        device: dict[str, Any] = {
            "name": str(payload["name"]),
            "subnet_id": subnet_id,
            "device_id": device_id,
            "channel": channel,
            "type": "air",
        }

        icon = payload.get("icon")
        if icon:
            device["icon"] = str(icon)
        gas_icon = payload.get("gas_icon")
        if gas_icon:
            device["gas_icon"] = str(gas_icon)
        category = payload.get("category")
        if category:
            device["category"] = str(category)
        group = payload.get("group")
        if group is not None:
            g = str(group).strip()
            if g.startswith("#"):
                g = g[1:].strip()
            if g:
                device["group"] = g

        store.add_device(device)
        _rebuild_air_index()
        asyncio.create_task(_sync_icons_for_devices([device]))

        await _republish_discovery()
        await _broadcast_devices()
        return device

    @api.post("/api/devices/pir")
    async def add_pir(payload: dict[str, Any]):
        required = ("name", "subnet_id", "device_id")
        missing = [k for k in required if k not in payload]
        if missing:
            raise HTTPException(status_code=400, detail=f"Missing: {', '.join(missing)}")

        subnet_id = int(payload["subnet_id"])
        device_id = int(payload["device_id"])
        sensor_id = payload.get("sensor_id", payload.get("channel"))
        if sensor_id is None:
            raise HTTPException(status_code=400, detail="Missing: sensor_id")
        channel = int(sensor_id)

        if store.find_device(type_="pir", subnet_id=subnet_id, device_id=device_id, channel=channel) is not None:
            raise HTTPException(status_code=409, detail="Device already exists with same address")

        device: dict[str, Any] = {
            "name": str(payload["name"]),
            "subnet_id": subnet_id,
            "device_id": device_id,
            "channel": channel,
            "type": "pir",
        }

        icon = payload.get("icon")
        if icon:
            device["icon"] = str(icon)
        category = payload.get("category")
        if category:
            device["category"] = str(category)
        group = payload.get("group")
        if group is not None:
            g = str(group).strip()
            if g.startswith("#"):
                g = g[1:].strip()
            if g:
                device["group"] = g

        store.add_device(device)
        _rebuild_pir_index()
        asyncio.create_task(_sync_icons_for_devices([device]))

        await _republish_discovery()
        await _broadcast_devices()
        return device

    @api.post("/api/devices/ultrasonic")
    async def add_ultrasonic(payload: dict[str, Any]):
        required = ("name", "subnet_id", "device_id")
        missing = [k for k in required if k not in payload]
        if missing:
            raise HTTPException(status_code=400, detail=f"Missing: {', '.join(missing)}")

        subnet_id = int(payload["subnet_id"])
        device_id = int(payload["device_id"])
        sensor_id = payload.get("sensor_id", payload.get("channel"))
        if sensor_id is None:
            raise HTTPException(status_code=400, detail="Missing: sensor_id")
        channel = int(sensor_id)

        if store.find_device(type_="ultrasonic", subnet_id=subnet_id, device_id=device_id, channel=channel) is not None:
            raise HTTPException(status_code=409, detail="Device already exists with same address")

        device: dict[str, Any] = {
            "name": str(payload["name"]),
            "subnet_id": subnet_id,
            "device_id": device_id,
            "channel": channel,
            "type": "ultrasonic",
        }

        icon = payload.get("icon")
        if icon:
            device["icon"] = str(icon)
        category = payload.get("category")
        if category:
            device["category"] = str(category)
        group = payload.get("group")
        if group is not None:
            g = str(group).strip()
            if g.startswith("#"):
                g = g[1:].strip()
            if g:
                device["group"] = g

        store.add_device(device)
        _rebuild_ultrasonic_index()
        asyncio.create_task(_sync_icons_for_devices([device]))

        await _republish_discovery()
        await _broadcast_devices()
        return device

    @api.post("/api/devices/dry_contact")
    async def add_dry_contact(payload: dict[str, Any]):
        required = ("name", "subnet_id", "device_id")
        missing = [k for k in required if k not in payload]
        if missing:
            raise HTTPException(status_code=400, detail=f"Missing: {', '.join(missing)}")

        input_id = payload.get("input_id", payload.get("channel"))
        if input_id is None:
            raise HTTPException(status_code=400, detail="Missing: input_id")

        subnet_id = int(payload["subnet_id"])
        device_id = int(payload["device_id"])
        channel = int(input_id)

        if store.find_device(type_="dry_contact", subnet_id=subnet_id, device_id=device_id, channel=channel) is not None:
            raise HTTPException(status_code=409, detail="Device already exists with same address")

        device: dict[str, Any] = {
            "name": str(payload["name"]),
            "subnet_id": subnet_id,
            "device_id": device_id,
            "channel": channel,
            "type": "dry_contact",
        }

        icon = payload.get("icon")
        if icon:
            device["icon"] = str(icon)
        category = payload.get("category")
        if category:
            device["category"] = str(category)
        group = payload.get("group")
        if group is not None:
            g = str(group).strip()
            if g.startswith("#"):
                g = g[1:].strip()
            if g:
                device["group"] = g
        device_class = payload.get("device_class")
        if device_class is not None:
            dc = str(device_class or "").strip()
            if dc:
                device["device_class"] = dc
        if "invert" in payload:
            device["invert"] = bool(payload.get("invert"))

        store.add_device(device)
        _rebuild_dry_contact_index()
        asyncio.create_task(_sync_icons_for_devices([device]))

        await _republish_discovery()
        await _broadcast_devices()
        return device

    @api.post("/api/control/cover/{subnet_id}/{device_id}/{channel}")
    async def control_cover(subnet_id: int, device_id: int, channel: int, payload: dict[str, Any]):
        gw: BusproGateway | None = api.state.gateway
        if gw is None:
            raise HTTPException(status_code=503, detail="Gateway not ready")
        if not gw.started or not gw.transport_ready():
            raise HTTPException(status_code=503, detail=gw.last_error or "UDP transport not ready")

        t0 = time.monotonic()
        cmd = str(payload.get("command") or "").upper()
        if cmd not in ("OPEN", "CLOSE", "STOP", "SET_POSITION", "OPEN_RAW", "CLOSE_RAW"):
            raise HTTPException(status_code=400, detail="command must be OPEN/CLOSE/STOP/SET_POSITION/OPEN_RAW/CLOSE_RAW")
        if cmd == "OPEN":
            await gw.cover_open(subnet_id=subnet_id, device_id=device_id, channel=channel)
        elif cmd == "OPEN_RAW":
            await gw.cover_open_raw(subnet_id=subnet_id, device_id=device_id, channel=channel)
        elif cmd == "CLOSE":
            await gw.cover_close(subnet_id=subnet_id, device_id=device_id, channel=channel)
        elif cmd == "CLOSE_RAW":
            await gw.cover_close_raw(subnet_id=subnet_id, device_id=device_id, channel=channel)
        elif cmd == "STOP":
            await gw.cover_stop(subnet_id=subnet_id, device_id=device_id, channel=channel)
        else:
            pos = int(payload.get("position") or 0)
            await gw.cover_set_position(subnet_id=subnet_id, device_id=device_id, channel=channel, position=pos)
        _LOGGER.debug(
            "control_cover %s %s.%s.%s in %.1fms",
            cmd,
            subnet_id,
            device_id,
            channel,
            (time.monotonic() - t0) * 1000.0,
        )
        return {"ok": True}

    @api.patch("/api/devices/light/{subnet_id}/{device_id}/{channel}")
    async def update_light(subnet_id: int, device_id: int, channel: int, payload: dict[str, Any]): 
        updates: dict[str, Any] = {} 
        move_to = None
        if "name" in payload: 
            updates["name"] = str(payload["name"]) 
        if "dimmable" in payload: 
            updates["dimmable"] = bool(payload["dimmable"]) 
        if "subnet_id" in payload or "device_id" in payload or "channel" in payload:
            move_to = (
                int(payload.get("subnet_id") or subnet_id),
                int(payload.get("device_id") or device_id),
                int(payload.get("channel") or channel),
            )
        if "icon" in payload: 
            icon = str(payload.get("icon") or "").strip() 
            updates["icon"] = icon or None 
        if "category" in payload: 
            category = str(payload.get("category") or "").strip() 
            updates["category"] = category or None 
        if "group" in payload:
            group = str(payload.get("group") or "").strip()
            if group.startswith("#"):
                group = group[1:].strip()
            updates["group"] = group or None 
 
        try:
            if move_to and (move_to[0], move_to[1], move_to[2]) != (subnet_id, device_id, channel):
                updated = store.move_device(
                    type_="light",
                    from_subnet_id=subnet_id,
                    from_device_id=device_id,
                    from_channel=channel,
                    to_subnet_id=move_to[0],
                    to_device_id=move_to[1],
                    to_channel=move_to[2],
                    updates=updates,
                )
            else:
                updated = store.update_device_typed(type_="light", subnet_id=subnet_id, device_id=device_id, channel=channel, updates=updates)
        except ValueError as e:
            if "duplicate" in str(e).lower():
                raise HTTPException(status_code=409, detail="Device already exists with same address")
            raise HTTPException(status_code=400, detail=str(e))
        if updated is None: 
            raise HTTPException(status_code=404, detail="Not Found") 
 
        asyncio.create_task(_sync_icons_for_devices([updated])) 
        gw: BusproGateway | None = api.state.gateway
        if gw is not None:
            gw.ensure_light(
                subnet_id=int(updated["subnet_id"]),
                device_id=int(updated["device_id"]),
                channel=int(updated["channel"]),
                name=str(updated.get("name") or ""),
            )
            await gw.read_light_status(
                subnet_id=int(updated["subnet_id"]),
                device_id=int(updated["device_id"]),
                channel=int(updated["channel"]),
            )
        await _republish_discovery() 
        await _broadcast_devices() 
        return updated 

    @api.patch("/api/devices/cover/{subnet_id}/{device_id}/{channel}")
    async def update_cover(subnet_id: int, device_id: int, channel: int, payload: dict[str, Any]): 
        updates: dict[str, Any] = {} 
        move_to = None
        if "name" in payload: 
            updates["name"] = str(payload["name"]) 
        if "reverse_icon" in payload: 
            updates["reverse_icon"] = bool(payload.get("reverse_icon")) 
        if "subnet_id" in payload or "device_id" in payload or "channel" in payload:
            move_to = (
                int(payload.get("subnet_id") or subnet_id),
                int(payload.get("device_id") or device_id),
                int(payload.get("channel") or channel),
            )
        if "icon" in payload: 
            icon = str(payload.get("icon") or "").strip() 
            updates["icon"] = icon or None 
        if "category" in payload: 
            category = str(payload.get("category") or "").strip() 
            updates["category"] = category or None 
        if "opening_time_up" in payload: 
            updates["opening_time_up"] = int(payload.get("opening_time_up") or 20) 
        if "opening_time_down" in payload: 
            updates["opening_time_down"] = int(payload.get("opening_time_down") or 20) 
        if "start_delay_s" in payload:
            updates["start_delay_s"] = float(payload.get("start_delay_s") or 0.0)
        if "group" in payload:
            group = str(payload.get("group") or "").strip()
            if group.startswith("#"):
                group = group[1:].strip()
            updates["group"] = group or None 

        try:
            if move_to and (move_to[0], move_to[1], move_to[2]) != (subnet_id, device_id, channel):
                updated = store.move_device(
                    type_="cover",
                    from_subnet_id=subnet_id,
                    from_device_id=device_id,
                    from_channel=channel,
                    to_subnet_id=move_to[0],
                    to_device_id=move_to[1],
                    to_channel=move_to[2],
                    updates=updates,
                )
            else:
                updated = store.update_device_typed(type_="cover", subnet_id=subnet_id, device_id=device_id, channel=channel, updates=updates)
        except ValueError as e:
            if "duplicate" in str(e).lower():
                raise HTTPException(status_code=409, detail="Device already exists with same address")
            raise HTTPException(status_code=400, detail=str(e))
        if updated is None: 
            raise HTTPException(status_code=404, detail="Not Found") 
 
        asyncio.create_task(_sync_icons_for_devices([updated])) 
        gw: BusproGateway | None = api.state.gateway 
        if gw is not None: 
            gw.ensure_cover( 
                subnet_id=int(updated["subnet_id"]), 
                device_id=int(updated["device_id"]), 
                channel=int(updated["channel"]), 
                name=str(updated.get("name") or ""), 
                opening_time_up=int(updated.get("opening_time_up") or 20), 
                opening_time_down=int(updated.get("opening_time_down") or 20), 
                start_delay_s=float(updated.get("start_delay_s") or 0.0),
            ) 
            # if address changed, force a status read
            await gw.read_cover_status(subnet_id=int(updated["subnet_id"]), device_id=int(updated["device_id"]), channel=int(updated["channel"]))
 
        await _republish_discovery() 
        await _broadcast_devices() 
        return updated 

    @api.patch("/api/devices/temp/{subnet_id}/{device_id}/{channel}")
    async def update_temp(subnet_id: int, device_id: int, channel: int, payload: dict[str, Any]):
        updates: dict[str, Any] = {}
        move_to = None
        if "name" in payload:
            updates["name"] = str(payload["name"])
        if "subnet_id" in payload or "device_id" in payload or "sensor_id" in payload or "channel" in payload:
            move_to = (
                int(payload.get("subnet_id") or subnet_id),
                int(payload.get("device_id") or device_id),
                int(payload.get("sensor_id") or payload.get("channel") or channel),
            )
        if "icon" in payload:
            icon = str(payload.get("icon") or "").strip()
            updates["icon"] = icon or None
        if "category" in payload:
            category = str(payload.get("category") or "").strip()
            updates["category"] = category or None
        if "group" in payload:
            group = str(payload.get("group") or "").strip()
            if group.startswith("#"):
                group = group[1:].strip()
            updates["group"] = group or None
        if "decimals" in payload:
            try:
                updates["decimals"] = max(0, min(3, int(payload.get("decimals"))))
            except Exception:
                updates["decimals"] = 1
        if "min_value" in payload:
            mv = payload.get("min_value")
            updates["min_value"] = float(mv) if mv is not None and str(mv).strip() != "" else None
        if "max_value" in payload:
            mv = payload.get("max_value")
            updates["max_value"] = float(mv) if mv is not None and str(mv).strip() != "" else None
        if "temp_format" in payload or "format" in payload:
            tf = payload.get("temp_format", payload.get("format"))
            tf_s = str(tf or "").strip()
            updates["temp_format"] = tf_s or None
        if "temp_scale" in payload:
            v = payload.get("temp_scale")
            updates["temp_scale"] = float(v) if v is not None and str(v).strip() != "" else None
        if "temp_offset" in payload:
            v = payload.get("temp_offset")
            updates["temp_offset"] = float(v) if v is not None and str(v).strip() != "" else None

        old_addr = f"{int(subnet_id)}.{int(device_id)}.{int(channel)}"
        try:
            if move_to and (move_to[0], move_to[1], move_to[2]) != (subnet_id, device_id, channel):
                # Clear retained discovery/state for old address to avoid duplicates in HA.
                mqtt.publish(_temp_config_topic(subnet_id=subnet_id, device_id=device_id, sensor_id=channel), "", retain=True)
                mqtt.publish(f"{settings.mqtt.base_topic}/state/temp/{subnet_id}/{device_id}/{channel}", "", retain=True)

                updated = store.move_device(
                    type_="temp",
                    from_subnet_id=subnet_id,
                    from_device_id=device_id,
                    from_channel=channel,
                    to_subnet_id=move_to[0],
                    to_device_id=move_to[1],
                    to_channel=move_to[2],
                    updates=updates,
                )
            else:
                updated = store.update_device_typed(type_="temp", subnet_id=subnet_id, device_id=device_id, channel=channel, updates=updates)
        except ValueError as e:
            if "duplicate" in str(e).lower():
                raise HTTPException(status_code=409, detail="Device already exists with same address")
            raise HTTPException(status_code=400, detail=str(e))
        if updated is None:
            raise HTTPException(status_code=404, detail="Not Found")

        # Keep runtime index/cache aligned
        last_t: dict[str, float] = getattr(api.state, "_last_temp_value", {}) or {}
        last_t.pop(old_addr, None)
        api.state._last_temp_value = last_t
        _rebuild_temp_index()

        asyncio.create_task(_sync_icons_for_devices([updated]))
        await _republish_discovery()
        await _broadcast_devices()
        return updated

    @api.delete("/api/devices/temp/{subnet_id}/{device_id}/{channel}")
    async def delete_temp(subnet_id: int, device_id: int, channel: int):
        removed = store.remove_device_typed(type_="temp", subnet_id=subnet_id, device_id=device_id, channel=channel)
        if not removed:
            raise HTTPException(status_code=404, detail="Not Found")

        mqtt.publish(_temp_config_topic(subnet_id=subnet_id, device_id=device_id, sensor_id=channel), "", retain=True)
        mqtt.publish(f"{settings.mqtt.base_topic}/state/temp/{subnet_id}/{device_id}/{channel}", "", retain=True)

        last_t: dict[str, float] = getattr(api.state, "_last_temp_value", {}) or {}
        last_t.pop(f"{int(subnet_id)}.{int(device_id)}.{int(channel)}", None)
        api.state._last_temp_value = last_t
        _rebuild_temp_index()

        await _republish_discovery()
        await _broadcast_devices()
        return {"ok": True}

    @api.patch("/api/devices/humidity/{subnet_id}/{device_id}/{channel}")
    async def update_humidity(subnet_id: int, device_id: int, channel: int, payload: dict[str, Any]):
        updates: dict[str, Any] = {}
        move_to = None
        if "name" in payload:
            updates["name"] = str(payload["name"])
        if "subnet_id" in payload or "device_id" in payload or "sensor_id" in payload or "channel" in payload:
            move_to = (
                int(payload.get("subnet_id") or subnet_id),
                int(payload.get("device_id") or device_id),
                int(payload.get("sensor_id") or payload.get("channel") or channel),
            )
        if "icon" in payload:
            icon = str(payload.get("icon") or "").strip()
            updates["icon"] = icon or None
        if "category" in payload:
            category = str(payload.get("category") or "").strip()
            updates["category"] = category or None
        if "group" in payload:
            group = str(payload.get("group") or "").strip()
            if group.startswith("#"):
                group = group[1:].strip()
            updates["group"] = group or None
        if "decimals" in payload:
            try:
                updates["decimals"] = max(0, min(3, int(payload.get("decimals"))))
            except Exception:
                updates["decimals"] = 0
        if "min_value" in payload:
            mv = payload.get("min_value")
            updates["min_value"] = float(mv) if mv is not None and str(mv).strip() != "" else None
        if "max_value" in payload:
            mv = payload.get("max_value")
            updates["max_value"] = float(mv) if mv is not None and str(mv).strip() != "" else None

        old_addr = f"{int(subnet_id)}.{int(device_id)}.{int(channel)}"
        try:
            if move_to and (move_to[0], move_to[1], move_to[2]) != (subnet_id, device_id, channel):
                mqtt.publish(_humidity_config_topic(subnet_id=subnet_id, device_id=device_id, sensor_id=channel), "", retain=True)
                mqtt.publish(f"{settings.mqtt.base_topic}/state/humidity/{subnet_id}/{device_id}/{channel}", "", retain=True)

                updated = store.move_device(
                    type_="humidity",
                    from_subnet_id=subnet_id,
                    from_device_id=device_id,
                    from_channel=channel,
                    to_subnet_id=move_to[0],
                    to_device_id=move_to[1],
                    to_channel=move_to[2],
                    updates=updates,
                )
            else:
                updated = store.update_device_typed(type_="humidity", subnet_id=subnet_id, device_id=device_id, channel=channel, updates=updates)
        except ValueError as e:
            if "duplicate" in str(e).lower():
                raise HTTPException(status_code=409, detail="Device already exists with same address")
            raise HTTPException(status_code=400, detail=str(e))
        if updated is None:
            raise HTTPException(status_code=404, detail="Not Found")

        last_h: dict[str, float] = getattr(api.state, "_last_humidity_value", {}) or {}
        last_h.pop(old_addr, None)
        api.state._last_humidity_value = last_h
        _rebuild_humidity_index()

        asyncio.create_task(_sync_icons_for_devices([updated]))
        await _republish_discovery()
        await _broadcast_devices()
        return updated

    @api.delete("/api/devices/humidity/{subnet_id}/{device_id}/{channel}")
    async def delete_humidity(subnet_id: int, device_id: int, channel: int):
        removed = store.remove_device_typed(type_="humidity", subnet_id=subnet_id, device_id=device_id, channel=channel)
        if not removed:
            raise HTTPException(status_code=404, detail="Not Found")

        mqtt.publish(_humidity_config_topic(subnet_id=subnet_id, device_id=device_id, sensor_id=channel), "", retain=True)
        mqtt.publish(f"{settings.mqtt.base_topic}/state/humidity/{subnet_id}/{device_id}/{channel}", "", retain=True)

        last_h: dict[str, float] = getattr(api.state, "_last_humidity_value", {}) or {}
        last_h.pop(f"{int(subnet_id)}.{int(device_id)}.{int(channel)}", None)
        api.state._last_humidity_value = last_h
        _rebuild_humidity_index()

        await _republish_discovery()
        await _broadcast_devices()
        return {"ok": True}

    @api.patch("/api/devices/illuminance/{subnet_id}/{device_id}/{channel}")
    async def update_illuminance(subnet_id: int, device_id: int, channel: int, payload: dict[str, Any]):
        updates: dict[str, Any] = {}
        move_to = None

        old_addr = f"{int(subnet_id)}.{int(device_id)}.{int(channel)}"

        if "name" in payload:
            updates["name"] = str(payload["name"])
        if "decimals" in payload:
            try:
                updates["decimals"] = max(0, min(3, int(payload.get("decimals"))))
            except Exception:
                updates["decimals"] = 0
        if "min_value" in payload:
            updates["min_value"] = payload.get("min_value")
        if "max_value" in payload:
            updates["max_value"] = payload.get("max_value")
        if "lux_scale" in payload:
            updates["lux_scale"] = payload.get("lux_scale")
        if "lux_offset" in payload:
            updates["lux_offset"] = payload.get("lux_offset")
        if "icon" in payload:
            icon = str(payload.get("icon") or "").strip()
            updates["icon"] = icon or None
        if "category" in payload:
            category = str(payload.get("category") or "").strip()
            updates["category"] = category or None
        if "group" in payload:
            group = str(payload.get("group") or "").strip()
            if group.startswith("#"):
                group = group[1:].strip()
            updates["group"] = group or None

        if "subnet_id" in payload or "device_id" in payload or "sensor_id" in payload or "channel" in payload:
            move_to = (
                int(payload.get("subnet_id") or subnet_id),
                int(payload.get("device_id") or device_id),
                int(payload.get("sensor_id", payload.get("channel", channel)) or channel),
            )

        try:
            if move_to and (move_to[0], move_to[1], move_to[2]) != (subnet_id, device_id, channel):
                mqtt.publish(_illuminance_config_topic(subnet_id=subnet_id, device_id=device_id, sensor_id=channel), "", retain=True)
                mqtt.publish(f"{settings.mqtt.base_topic}/state/illuminance/{subnet_id}/{device_id}/{channel}", "", retain=True)

                updated = store.move_device(
                    type_="illuminance",
                    from_subnet_id=subnet_id,
                    from_device_id=device_id,
                    from_channel=channel,
                    to_subnet_id=move_to[0],
                    to_device_id=move_to[1],
                    to_channel=move_to[2],
                    updates=updates,
                )
            else:
                updated = store.update_device_typed(type_="illuminance", subnet_id=subnet_id, device_id=device_id, channel=channel, updates=updates)
        except ValueError as e:
            if "duplicate" in str(e).lower():
                raise HTTPException(status_code=409, detail="Device already exists with same address")
            raise HTTPException(status_code=400, detail=str(e))
        if updated is None:
            raise HTTPException(status_code=404, detail="Not Found")

        last_lx: dict[str, float] = getattr(api.state, "_last_illuminance_value", {}) or {}
        last_lx.pop(old_addr, None)
        api.state._last_illuminance_value = last_lx
        _rebuild_illuminance_index()

        asyncio.create_task(_sync_icons_for_devices([updated]))
        await _republish_discovery()
        await _broadcast_devices()
        return updated

    @api.delete("/api/devices/illuminance/{subnet_id}/{device_id}/{channel}")
    async def delete_illuminance(subnet_id: int, device_id: int, channel: int):
        removed = store.remove_device_typed(type_="illuminance", subnet_id=subnet_id, device_id=device_id, channel=channel)
        if not removed:
            raise HTTPException(status_code=404, detail="Not Found")

        mqtt.publish(_illuminance_config_topic(subnet_id=subnet_id, device_id=device_id, sensor_id=channel), "", retain=True)
        mqtt.publish(f"{settings.mqtt.base_topic}/state/illuminance/{subnet_id}/{device_id}/{channel}", "", retain=True)

        last_lx: dict[str, float] = getattr(api.state, "_last_illuminance_value", {}) or {}
        last_lx.pop(f"{int(subnet_id)}.{int(device_id)}.{int(channel)}", None)
        api.state._last_illuminance_value = last_lx
        _rebuild_illuminance_index()

        await _republish_discovery()
        await _broadcast_devices()
        return {"ok": True}

    @api.patch("/api/devices/air/{subnet_id}/{device_id}/{channel}")
    async def update_air(subnet_id: int, device_id: int, channel: int, payload: dict[str, Any]):
        updates: dict[str, Any] = {}
        move_to = None
        old_addr = f"{int(subnet_id)}.{int(device_id)}.{int(channel)}"

        if "name" in payload:
            updates["name"] = str(payload["name"])
        if "icon" in payload:
            icon = str(payload.get("icon") or "").strip()
            updates["icon"] = icon or None
        if "gas_icon" in payload:
            icon = str(payload.get("gas_icon") or "").strip()
            updates["gas_icon"] = icon or None
        if "category" in payload:
            category = str(payload.get("category") or "").strip()
            updates["category"] = category or None
        if "group" in payload:
            group = str(payload.get("group") or "").strip()
            if group.startswith("#"):
                group = group[1:].strip()
            updates["group"] = group or None

        if "subnet_id" in payload or "device_id" in payload or "sensor_id" in payload or "channel" in payload:
            move_to = (
                int(payload.get("subnet_id") or subnet_id),
                int(payload.get("device_id") or device_id),
                int(payload.get("sensor_id", payload.get("channel", channel)) or channel),
            )

        try:
            if move_to and (move_to[0], move_to[1], move_to[2]) != (subnet_id, device_id, channel):
                mqtt.publish(_air_quality_config_topic(subnet_id=subnet_id, device_id=device_id, sensor_id=channel), "", retain=True)
                mqtt.publish(_gas_percent_config_topic(subnet_id=subnet_id, device_id=device_id, sensor_id=channel), "", retain=True)
                mqtt.publish(f"{settings.mqtt.base_topic}/state/air_quality/{subnet_id}/{device_id}/{channel}", "", retain=True)
                mqtt.publish(f"{settings.mqtt.base_topic}/state/gas_percent/{subnet_id}/{device_id}/{channel}", "", retain=True)

                updated = store.move_device(
                    type_="air",
                    from_subnet_id=subnet_id,
                    from_device_id=device_id,
                    from_channel=channel,
                    to_subnet_id=move_to[0],
                    to_device_id=move_to[1],
                    to_channel=move_to[2],
                    updates=updates,
                )
            else:
                updated = store.update_device_typed(type_="air", subnet_id=subnet_id, device_id=device_id, channel=channel, updates=updates)
        except ValueError as e:
            if "duplicate" in str(e).lower():
                raise HTTPException(status_code=409, detail="Device already exists with same address")
            raise HTTPException(status_code=400, detail=str(e))
        if updated is None:
            raise HTTPException(status_code=404, detail="Not Found")

        last_a: dict[str, str] = getattr(api.state, "_last_air_quality", {}) or {}
        last_a.pop(old_addr, None)
        api.state._last_air_quality = last_a
        last_g: dict[str, float] = getattr(api.state, "_last_gas_percent", {}) or {}
        last_g.pop(old_addr, None)
        api.state._last_gas_percent = last_g
        _rebuild_air_index()

        asyncio.create_task(_sync_icons_for_devices([updated]))
        await _republish_discovery()
        await _broadcast_devices()
        return updated

    @api.delete("/api/devices/air/{subnet_id}/{device_id}/{channel}")
    async def delete_air(subnet_id: int, device_id: int, channel: int):
        removed = store.remove_device_typed(type_="air", subnet_id=subnet_id, device_id=device_id, channel=channel)
        if not removed:
            raise HTTPException(status_code=404, detail="Not Found")

        mqtt.publish(_air_quality_config_topic(subnet_id=subnet_id, device_id=device_id, sensor_id=channel), "", retain=True)
        mqtt.publish(_gas_percent_config_topic(subnet_id=subnet_id, device_id=device_id, sensor_id=channel), "", retain=True)
        mqtt.publish(f"{settings.mqtt.base_topic}/state/air_quality/{subnet_id}/{device_id}/{channel}", "", retain=True)
        mqtt.publish(f"{settings.mqtt.base_topic}/state/gas_percent/{subnet_id}/{device_id}/{channel}", "", retain=True)

        last_a: dict[str, str] = getattr(api.state, "_last_air_quality", {}) or {}
        last_a.pop(f"{int(subnet_id)}.{int(device_id)}.{int(channel)}", None)
        api.state._last_air_quality = last_a
        last_g: dict[str, float] = getattr(api.state, "_last_gas_percent", {}) or {}
        last_g.pop(f"{int(subnet_id)}.{int(device_id)}.{int(channel)}", None)
        api.state._last_gas_percent = last_g
        _rebuild_air_index()

        await _republish_discovery()
        await _broadcast_devices()
        return {"ok": True}

    @api.patch("/api/devices/pir/{subnet_id}/{device_id}/{channel}")
    async def update_pir(subnet_id: int, device_id: int, channel: int, payload: dict[str, Any]):
        updates: dict[str, Any] = {}
        move_to = None

        old_addr = f"{int(subnet_id)}.{int(device_id)}.{int(channel)}"

        if "name" in payload:
            updates["name"] = str(payload["name"])
        if "icon" in payload:
            icon = str(payload.get("icon") or "").strip()
            updates["icon"] = icon or None
        if "category" in payload:
            category = str(payload.get("category") or "").strip()
            updates["category"] = category or None
        if "group" in payload:
            group = str(payload.get("group") or "").strip()
            if group.startswith("#"):
                group = group[1:].strip()
            updates["group"] = group or None

        if "subnet_id" in payload or "device_id" in payload or "sensor_id" in payload or "channel" in payload:
            move_to = (
                int(payload.get("subnet_id") or subnet_id),
                int(payload.get("device_id") or device_id),
                int(payload.get("sensor_id") or payload.get("channel") or channel),
            )

        try:
            if move_to and (move_to[0], move_to[1], move_to[2]) != (subnet_id, device_id, channel):
                mqtt.publish(_pir_config_topic(subnet_id=subnet_id, device_id=device_id, sensor_id=channel), "", retain=True)
                mqtt.publish(f"{settings.mqtt.base_topic}/state/pir/{subnet_id}/{device_id}/{channel}", "", retain=True)

                updated = store.move_device(
                    type_="pir",
                    from_subnet_id=subnet_id,
                    from_device_id=device_id,
                    from_channel=channel,
                    to_subnet_id=move_to[0],
                    to_device_id=move_to[1],
                    to_channel=move_to[2],
                    updates=updates,
                )
            else:
                updated = store.update_device_typed(type_="pir", subnet_id=subnet_id, device_id=device_id, channel=channel, updates=updates)
        except ValueError as e:
            if "duplicate" in str(e).lower():
                raise HTTPException(status_code=409, detail="Device already exists with same address")
            raise HTTPException(status_code=400, detail=str(e))
        if updated is None:
            raise HTTPException(status_code=404, detail="Not Found")

        last_p: dict[str, str] = getattr(api.state, "_last_pir_state", {}) or {}
        last_p.pop(old_addr, None)
        api.state._last_pir_state = last_p
        _rebuild_pir_index()

        asyncio.create_task(_sync_icons_for_devices([updated]))
        await _republish_discovery()
        await _broadcast_devices()
        return updated

    @api.delete("/api/devices/pir/{subnet_id}/{device_id}/{channel}")
    async def delete_pir(subnet_id: int, device_id: int, channel: int):
        removed = store.remove_device_typed(type_="pir", subnet_id=subnet_id, device_id=device_id, channel=channel)
        if not removed:
            raise HTTPException(status_code=404, detail="Not Found")

        mqtt.publish(_pir_config_topic(subnet_id=subnet_id, device_id=device_id, sensor_id=channel), "", retain=True)
        mqtt.publish(f"{settings.mqtt.base_topic}/state/pir/{subnet_id}/{device_id}/{channel}", "", retain=True)

        last_p: dict[str, str] = getattr(api.state, "_last_pir_state", {}) or {}
        last_p.pop(f"{int(subnet_id)}.{int(device_id)}.{int(channel)}", None)
        api.state._last_pir_state = last_p
        _rebuild_pir_index()

        await _republish_discovery()
        await _broadcast_devices()
        return {"ok": True}

    @api.patch("/api/devices/ultrasonic/{subnet_id}/{device_id}/{channel}")
    async def update_ultrasonic(subnet_id: int, device_id: int, channel: int, payload: dict[str, Any]):
        updates: dict[str, Any] = {}
        move_to = None

        old_addr = f"{int(subnet_id)}.{int(device_id)}.{int(channel)}"

        if "name" in payload:
            updates["name"] = str(payload["name"])
        if "icon" in payload:
            icon = str(payload.get("icon") or "").strip()
            updates["icon"] = icon or None
        if "category" in payload:
            category = str(payload.get("category") or "").strip()
            updates["category"] = category or None
        if "group" in payload:
            group = str(payload.get("group") or "").strip()
            if group.startswith("#"):
                group = group[1:].strip()
            updates["group"] = group or None

        if "subnet_id" in payload or "device_id" in payload or "sensor_id" in payload or "channel" in payload:
            move_to = (
                int(payload.get("subnet_id") or subnet_id),
                int(payload.get("device_id") or device_id),
                int(payload.get("sensor_id") or payload.get("channel") or channel),
            )

        try:
            if move_to and (move_to[0], move_to[1], move_to[2]) != (subnet_id, device_id, channel):
                mqtt.publish(_ultrasonic_config_topic(subnet_id=subnet_id, device_id=device_id, sensor_id=channel), "", retain=True)
                mqtt.publish(f"{settings.mqtt.base_topic}/state/ultrasonic/{subnet_id}/{device_id}/{channel}", "", retain=True)

                updated = store.move_device(
                    type_="ultrasonic",
                    from_subnet_id=subnet_id,
                    from_device_id=device_id,
                    from_channel=channel,
                    to_subnet_id=move_to[0],
                    to_device_id=move_to[1],
                    to_channel=move_to[2],
                    updates=updates,
                )
            else:
                updated = store.update_device_typed(type_="ultrasonic", subnet_id=subnet_id, device_id=device_id, channel=channel, updates=updates)
        except ValueError as e:
            if "duplicate" in str(e).lower():
                raise HTTPException(status_code=409, detail="Device already exists with same address")
            raise HTTPException(status_code=400, detail=str(e))
        if updated is None:
            raise HTTPException(status_code=404, detail="Not Found")

        last_u: dict[str, str] = getattr(api.state, "_last_ultrasonic_state", {}) or {}
        last_u.pop(old_addr, None)
        api.state._last_ultrasonic_state = last_u
        _rebuild_ultrasonic_index()

        asyncio.create_task(_sync_icons_for_devices([updated]))
        await _republish_discovery()
        await _broadcast_devices()
        return updated

    @api.delete("/api/devices/ultrasonic/{subnet_id}/{device_id}/{channel}")
    async def delete_ultrasonic(subnet_id: int, device_id: int, channel: int):
        removed = store.remove_device_typed(type_="ultrasonic", subnet_id=subnet_id, device_id=device_id, channel=channel)
        if not removed:
            raise HTTPException(status_code=404, detail="Not Found")

        mqtt.publish(_ultrasonic_config_topic(subnet_id=subnet_id, device_id=device_id, sensor_id=channel), "", retain=True)
        mqtt.publish(f"{settings.mqtt.base_topic}/state/ultrasonic/{subnet_id}/{device_id}/{channel}", "", retain=True)

        last_u: dict[str, str] = getattr(api.state, "_last_ultrasonic_state", {}) or {}
        last_u.pop(f"{int(subnet_id)}.{int(device_id)}.{int(channel)}", None)
        api.state._last_ultrasonic_state = last_u
        _rebuild_ultrasonic_index()

        await _republish_discovery()
        await _broadcast_devices()
        return {"ok": True}

    @api.patch("/api/devices/dry_contact/{subnet_id}/{device_id}/{channel}")
    async def update_dry_contact(subnet_id: int, device_id: int, channel: int, payload: dict[str, Any]):
        updates: dict[str, Any] = {}
        move_to = None

        old_addr = f"{int(subnet_id)}.{int(device_id)}.{int(channel)}"

        if "name" in payload:
            updates["name"] = str(payload["name"])
        if "icon" in payload:
            icon = str(payload.get("icon") or "").strip()
            updates["icon"] = icon or None
        if "category" in payload:
            category = str(payload.get("category") or "").strip()
            updates["category"] = category or None
        if "group" in payload:
            group = str(payload.get("group") or "").strip()
            if group.startswith("#"):
                group = group[1:].strip()
            updates["group"] = group or None
        if "device_class" in payload:
            dc = str(payload.get("device_class") or "").strip()
            updates["device_class"] = dc or None
        if "invert" in payload:
            updates["invert"] = bool(payload.get("invert"))

        if "subnet_id" in payload or "device_id" in payload or "input_id" in payload or "channel" in payload:
            move_to = (
                int(payload.get("subnet_id") or subnet_id),
                int(payload.get("device_id") or device_id),
                int(payload.get("input_id") or payload.get("channel") or channel),
            )

        try:
            if move_to and (move_to[0], move_to[1], move_to[2]) != (subnet_id, device_id, channel):
                mqtt.publish(_dry_contact_config_topic(subnet_id=subnet_id, device_id=device_id, input_id=channel), "", retain=True)
                mqtt.publish(f"{settings.mqtt.base_topic}/state/dry_contact/{subnet_id}/{device_id}/{channel}", "", retain=True)

                updated = store.move_device(
                    type_="dry_contact",
                    from_subnet_id=subnet_id,
                    from_device_id=device_id,
                    from_channel=channel,
                    to_subnet_id=move_to[0],
                    to_device_id=move_to[1],
                    to_channel=move_to[2],
                    updates=updates,
                )
            else:
                updated = store.update_device_typed(type_="dry_contact", subnet_id=subnet_id, device_id=device_id, channel=channel, updates=updates)
        except ValueError as e:
            if "duplicate" in str(e).lower():
                raise HTTPException(status_code=409, detail="Device already exists with same address")
            raise HTTPException(status_code=400, detail=str(e))
        if updated is None:
            raise HTTPException(status_code=404, detail="Not Found")

        last_dc: dict[str, str] = getattr(api.state, "_last_dry_contact_state", {}) or {}
        last_dc.pop(old_addr, None)
        api.state._last_dry_contact_state = last_dc
        _rebuild_dry_contact_index()

        asyncio.create_task(_sync_icons_for_devices([updated]))
        await _republish_discovery()
        await _broadcast_devices()
        return updated

    @api.delete("/api/devices/dry_contact/{subnet_id}/{device_id}/{channel}")
    async def delete_dry_contact(subnet_id: int, device_id: int, channel: int):
        removed = store.remove_device_typed(type_="dry_contact", subnet_id=subnet_id, device_id=device_id, channel=channel)
        if not removed:
            raise HTTPException(status_code=404, detail="Not Found")

        mqtt.publish(_dry_contact_config_topic(subnet_id=subnet_id, device_id=device_id, input_id=channel), "", retain=True)
        mqtt.publish(f"{settings.mqtt.base_topic}/state/dry_contact/{subnet_id}/{device_id}/{channel}", "", retain=True)

        last_dc: dict[str, str] = getattr(api.state, "_last_dry_contact_state", {}) or {}
        last_dc.pop(f"{int(subnet_id)}.{int(device_id)}.{int(channel)}", None)
        api.state._last_dry_contact_state = last_dc
        _rebuild_dry_contact_index()

        await _republish_discovery()
        await _broadcast_devices()
        return {"ok": True}

     
    @api.delete("/api/devices/light/{subnet_id}/{device_id}/{channel}")
    async def delete_light(subnet_id: int, device_id: int, channel: int):
        removed = store.remove_device_typed(type_="light", subnet_id=subnet_id, device_id=device_id, channel=channel)
        if not removed:
            raise HTTPException(status_code=404, detail="Not Found")

        # Re-publish discovery (we don't delete retained discovery yet; we'll add cleanup later)
        await _republish_discovery()
        await _broadcast_devices()
        return {"ok": True}

    @api.delete("/api/devices/cover/{subnet_id}/{device_id}/{channel}")
    async def delete_cover(subnet_id: int, device_id: int, channel: int):
        removed = store.remove_device_typed(type_="cover", subnet_id=subnet_id, device_id=device_id, channel=channel)
        if not removed:
            raise HTTPException(status_code=404, detail="Not Found")

        await _republish_discovery()
        await _broadcast_devices()
        return {"ok": True}
    @api.delete("/api/devices")
    async def delete_all_devices():
        store.clear_devices()
        _rebuild_temp_index()
        _rebuild_humidity_index()
        _rebuild_illuminance_index()
        _rebuild_dry_contact_index()
        _rebuild_air_index()
        _rebuild_pir_index()
        _rebuild_ultrasonic_index()
        await _republish_discovery()
        await _broadcast_devices()
        return {"ok": True}


    @api.get("/api/buspro/status")
    async def buspro_status():
        gw: BusproGateway | None = api.state.gateway
        if gw is None:
            return {"ready": False, "error": "Gateway not initialized"}
        tx_host, tx_port = gw.send_target()
        rx = gw.last_rx
        return {
            "ready": bool(gw.started and gw.transport_ready()),
            "started": bool(gw.started),
            "transport_ready": bool(gw.transport_ready()),
            "host": gw.host,
            "port": gw.port,
            "tx_host": tx_host,
            "tx_port": tx_port,
            "rx_host": rx[0] if rx else None,
            "rx_port": rx[1] if rx else None,
            "last_error": gw.last_error,
        }
    @api.get("/api/mqtt/status")
    async def mqtt_status():
        st = mqtt.status()
        return {"connected": st.connected, "last_error": st.last_error}

    @api.post("/api/mqtt/republish")
    async def mqtt_republish():
        await _republish_discovery()
        return {"ok": True}

    @api.get("/api/user/light_scenarios")
    async def list_light_scenarios():
        return {"items": store.list_light_scenarios()}

    @api.post("/api/user/light_scenarios")
    async def create_light_scenario(payload: dict[str, Any]):
        try:
            out = store.add_light_scenario(payload)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        try:
            await _republish_discovery()
        except Exception:
            pass
        return out

    @api.put("/api/user/light_scenarios/{scenario_id}")
    async def update_light_scenario(scenario_id: str, payload: dict[str, Any]):
        try:
            out = store.update_light_scenario(scenario_id=scenario_id, payload=payload)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        if out is None:
            raise HTTPException(status_code=404, detail="Not Found")
        try:
            await _republish_discovery()
        except Exception:
            pass
        return out

    @api.delete("/api/user/light_scenarios/{scenario_id}")
    async def delete_light_scenario(scenario_id: str):
        ok = store.delete_light_scenario(scenario_id=scenario_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Not Found")
        try:
            await _republish_discovery()
        except Exception:
            pass
        return {"ok": True}

    @api.post("/api/control/light_scenario/{scenario_id}")
    async def run_light_scenario(scenario_id: str):
        gw: BusproGateway | None = api.state.gateway
        if gw is None:
            raise HTTPException(status_code=503, detail="Gateway not ready")
        if not gw.started or not gw.transport_ready():
            raise HTTPException(status_code=503, detail=gw.last_error or "UDP transport not ready")

        sc = store.find_light_scenario(scenario_id=scenario_id)
        if not sc:
            raise HTTPException(status_code=404, detail="Not Found")
        items = sc.get("items") or []
        if not isinstance(items, list) or not items:
            return {"ok": True, "sent": 0}

        sent = 0
        for it in items:
            if not isinstance(it, dict):
                continue
            try:
                subnet_id = int(it.get("subnet_id"))
                device_id = int(it.get("device_id"))
                channel = int(it.get("channel"))
            except Exception:
                continue
            state = str(it.get("state") or "").strip().upper()
            if state not in ("ON", "OFF"):
                continue
            on = state == "ON"
            br = it.get("brightness")
            try:
                br255 = int(br) if (br is not None and on) else None
            except Exception:
                br255 = None
            try:
                await gw.set_light(subnet_id=subnet_id, device_id=device_id, channel=channel, on=on, brightness255=br255)
                sent += 1
            except Exception:
                # Best-effort: continue other lights
                continue

        return {"ok": True, "sent": sent}

    @api.post("/api/control/light/{subnet_id}/{device_id}/{channel}")
    async def control_light(subnet_id: int, device_id: int, channel: int, payload: dict[str, Any]):
        gw: BusproGateway | None = api.state.gateway
        if gw is None:
            raise HTTPException(status_code=503, detail="Gateway not ready")
        if not gw.started or not gw.transport_ready():
            raise HTTPException(status_code=503, detail=gw.last_error or "UDP transport not ready")

        state = str(payload.get("state") or "").upper()
        if state not in ("ON", "OFF"):
            raise HTTPException(status_code=400, detail="state must be ON/OFF")
        on = state == "ON"
        br = payload.get("brightness")
        br255 = int(br) if br is not None else None

        await gw.set_light(subnet_id=subnet_id, device_id=device_id, channel=channel, on=on, brightness255=br255)
        try:
            await gw.read_light_status(subnet_id=subnet_id, device_id=device_id, channel=channel)
        except Exception:
            pass
        return {"ok": True}

    @api.post("/api/control/ha/light/{entity_id}")
    async def control_ha_light(entity_id: str, payload: dict[str, Any]):
        if not _ha_enabled():
            raise HTTPException(status_code=503, detail="Home Assistant API not available (SUPERVISOR_TOKEN missing)")
        eid = str(entity_id or "").strip().lower()
        if not eid.startswith("light."):
            raise HTTPException(status_code=400, detail="entity_id must start with light.")
        state = str(payload.get("state") or "").upper()
        if state not in ("ON", "OFF"):
            raise HTTPException(status_code=400, detail="state must be ON/OFF")
        if state == "OFF":
            await asyncio.to_thread(_ha_request, "POST", "/api/services/light/turn_off", payload={"entity_id": eid}, timeout_s=10)
            return {"ok": True}
        data: dict[str, Any] = {"entity_id": eid}
        br = payload.get("brightness")
        if br is not None:
            try:
                data["brightness"] = int(br)
            except Exception:
                pass
        await asyncio.to_thread(_ha_request, "POST", "/api/services/light/turn_on", payload=data, timeout_s=10)
        return {"ok": True}

    @api.post("/api/control/ha/switch/{entity_id}")
    async def control_ha_switch(entity_id: str, payload: dict[str, Any]):
        if not _ha_enabled():
            raise HTTPException(status_code=503, detail="Home Assistant API not available (SUPERVISOR_TOKEN missing)")
        eid = str(entity_id or "").strip().lower()
        if not eid.startswith("switch."):
            raise HTTPException(status_code=400, detail="entity_id must start with switch.")
        state = str(payload.get("state") or "").upper()
        if state not in ("ON", "OFF"):
            raise HTTPException(status_code=400, detail="state must be ON/OFF")
        svc = "turn_on" if state == "ON" else "turn_off"
        await asyncio.to_thread(_ha_request, "POST", f"/api/services/switch/{svc}", payload={"entity_id": eid}, timeout_s=10)
        return {"ok": True}

    @api.post("/api/control/ha/cover/{entity_id}")
    async def control_ha_cover(entity_id: str, payload: dict[str, Any]):
        if not _ha_enabled():
            raise HTTPException(status_code=503, detail="Home Assistant API not available (SUPERVISOR_TOKEN missing)")
        eid = str(entity_id or "").strip().lower()
        if not eid.startswith("cover."):
            raise HTTPException(status_code=400, detail="entity_id must start with cover.")
        cmd = str(payload.get("command") or "").strip().upper()
        if cmd in ("OPEN", "CLOSE", "STOP"):
            svc = "open_cover" if cmd == "OPEN" else ("close_cover" if cmd == "CLOSE" else "stop_cover")
            await asyncio.to_thread(_ha_request, "POST", f"/api/services/cover/{svc}", payload={"entity_id": eid}, timeout_s=10)
            return {"ok": True}
        if cmd == "SET_POSITION":
            pos = payload.get("position")
            try:
                pos_i = int(pos)
            except Exception:
                raise HTTPException(status_code=400, detail="position required")
            pos_i = max(0, min(100, pos_i))
            await asyncio.to_thread(_ha_request, "POST", "/api/services/cover/set_cover_position", payload={"entity_id": eid, "position": pos_i}, timeout_s=10)
            return {"ok": True}
        raise HTTPException(status_code=400, detail="unsupported command")

    @api.websocket("/ws")
    async def ws_endpoint(ws: WebSocket):
        # websocket auth: allow if ingress, or auth_mode none, or token provided
        options_ = read_options()
        settings_ = load_settings(options_)
        headers = {k.lower(): v for k, v in ws.headers.items()}
        query = dict(ws.query_params)
        port = None
        try:
            port = int((ws.scope.get("server") or ("", 0))[1])
        except Exception:
            port = None
        if port == USER_PORT:
            if not _is_ingress_headers(headers) and not _check_auth_headers(headers, query, settings_.user_auth):
                await ws.close(code=1008)
                return
        else:
            if not _check_auth_headers(headers, query, settings_.auth):
                await ws.close(code=1008)
                return

        await hub.connect(ws)
        try:
            # snapshot
            await ws.send_text(
                json.dumps(
                    {
                        "type": "snapshot",
                        "data": {
                            "devices": _list_user_devices(),
                            "cover_groups": store.list_cover_groups(),
                            "states": {
                                k.split(":", 1)[1]: v
                                for k, v in store.get_states().items()
                                if isinstance(k, str) and k.startswith("light:")
                            },
	                            "cover_states": {
	                                k.split(":", 1)[1]: v
	                                for k, v in store.get_states().items()
	                                if isinstance(k, str) and k.startswith("cover:")
	                            },
	                            "temp_states": {
	                                k.split(":", 1)[1]: v
	                                for k, v in store.get_states().items()
	                                if isinstance(k, str) and k.startswith("temp:")
	                            },
	                            "humidity_states": {
	                                k.split(":", 1)[1]: v
	                                for k, v in store.get_states().items()
	                                if isinstance(k, str) and k.startswith("humidity:")
	                            },
                                    "illuminance_states": {
	                                k.split(":", 1)[1]: v
	                                for k, v in store.get_states().items()
	                                if isinstance(k, str) and k.startswith("illuminance:")
	                            },
	                            "air_quality_states": {
	                                k.split(":", 1)[1]: v
	                                for k, v in store.get_states().items()
	                                if isinstance(k, str) and k.startswith("air_quality:")
	                            },
	                            "gas_percent_states": {
	                                k.split(":", 1)[1]: v
	                                for k, v in store.get_states().items()
	                                if isinstance(k, str) and k.startswith("gas_percent:")
	                            },
	                            "dry_contact_states": {
	                                k.split(":", 1)[1]: v
	                                for k, v in store.get_states().items()
	                                if isinstance(k, str) and k.startswith("dry_contact:")
	                            },
	                            "pir_states": {
	                                k.split(":", 1)[1]: v
	                                for k, v in store.get_states().items()
	                                if isinstance(k, str) and k.startswith("pir:")
	                            },
	                            "ultrasonic_states": {
	                                k.split(":", 1)[1]: v
	                                for k, v in store.get_states().items()
	                                if isinstance(k, str) and k.startswith("ultrasonic:")
	                            },
                                "ha_states": getattr(api.state, "ha_states", {}) or {},
	                            "mqtt": api.state.mqtt.status().__dict__,
	                        },
	                    },
	                    ensure_ascii=False,
                )
            )

            while True:
                msg = await ws.receive_text()
                # optional ping/pong
                if msg.strip().lower() == "ping":
                    await ws.send_text("pong")
        except WebSocketDisconnect:
            pass
        finally:
            await hub.disconnect(ws)

    @api.get("/ingress", response_class=HTMLResponse, include_in_schema=False)
    @api.get("/ingress/", response_class=HTMLResponse, include_in_schema=False)
    async def ingress_index(request: Request):
        return await index(request)

    @api.get("/{full_path:path}", response_class=HTMLResponse, include_in_schema=False)
    async def spa_fallback(full_path: str, request: Request):
        # If we're on USER_PORT and a proxy target is active, proxy unknown paths to upstream.
        try:
            port = _server_port(request.scope)
            px = str(request.cookies.get("buspro_px") or "").strip()
            if port == USER_PORT and px and store.find_proxy_target(name=px):
                if not full_path.startswith(("api/", "static/", "ws", "www/", "ext/", "extws/")) and full_path not in ("health", "favicon.ico"):
                    return await ext_proxy(name=px, path=full_path, request=request)
        except Exception:
            pass

        if full_path.startswith("api/") or full_path.startswith("static/") or full_path == "health":
            raise HTTPException(status_code=404, detail="Not Found")
        return await index(request)

    return api


def main() -> None:
    import uvicorn

    app = create_app()

    async def _serve() -> None:
        cfg_user = uvicorn.Config(app, host="0.0.0.0", port=USER_PORT, log_level="info")
        cfg_admin = uvicorn.Config(app, host="0.0.0.0", port=ADMIN_PORT, log_level="info")
        srv_user = uvicorn.Server(cfg_user)
        srv_admin = uvicorn.Server(cfg_admin)
        await asyncio.gather(srv_user.serve(), srv_admin.serve())

    asyncio.run(_serve())


if __name__ == "__main__":
    main()
