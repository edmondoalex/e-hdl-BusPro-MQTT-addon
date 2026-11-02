"""Restricted view of the local eFace journal. No command or identity bypass."""
from __future__ import annotations

import asyncio
from http.cookies import SimpleCookie
import urllib.error
import urllib.parse
import urllib.request

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

router = APIRouter()
UPSTREAM = "http://127.0.0.1:8130"
PREFIX = "/event-register"
SESSION = "econtrol_register_session"
READ = {
    "events", "login", "api/user/events", "api/admin/events/storage", "assets/event-register.js",
    "assets/event-register.css", "assets/eface-x4-app-icon.png",
    "assets/brand-horizontal.png", "assets/manifest.webmanifest",
}
WRITE = {("POST", "api/auth/login"), ("PUT", "api/admin/events/retention")}
MAX_RESPONSE = 4 * 1024 * 1024


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def fetch(method, path, query, headers, body):
    # Fixed loopback destination; neither URL nor port comes from the browser.
    url = UPSTREAM + "/" + path + (("?" + query) if query else "")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    req = urllib.request.Request(url, data=body if method != "GET" else None, headers=headers, method=method)
    try:
        result = opener.open(req, timeout=12)
    except urllib.error.HTTPError as error:
        result = error
    with result:
        data = result.read(MAX_RESPONSE + 1)
        if len(data) > MAX_RESPONSE:
            raise ValueError("Response too large")
        return result.code, result.headers, data


@router.api_route(PREFIX + "/{path:path}", methods=["GET", "POST", "PUT"])
async def event_register_proxy(request: Request, path: str):
    method = request.method
    if not (method == "GET" and path in READ or (method, path) in WRITE):
        return JSONResponse({"detail": "Percorso non disponibile nel registro"}, status_code=404)
    base = str(request.scope.get("root_path") or "").rstrip("/")
    prefix = base + PREFIX
    if method != "GET":
        origin = request.headers.get("origin")
        if (request.headers.get("sec-fetch-site") == "cross-site" or
                origin and urllib.parse.urlsplit(origin).netloc != request.headers.get("host")):
            return JSONResponse({"detail": "Origine non consentita"}, status_code=403)
        if request.headers.get("content-type", "").split(";", 1)[0].strip() != "application/json":
            return JSONResponse({"detail": "Richiesto JSON"}, status_code=415)
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > 8192:
            return JSONResponse({"detail": "Richiesta troppo grande"}, status_code=413)
    query = str(request.url.query)
    if len(query) > 8192:
        return JSONResponse({"detail": "Ricerca troppo lunga"}, status_code=414)
    headers = {"Accept": "*/*", "Accept-Encoding": "identity"}
    if method != "GET":
        headers["Content-Type"] = "application/json"
    # A real signed eFace session is required. Never forward Hub auth/ingress headers.
    session = request.cookies.get(SESSION) or request.cookies.get("eface_user")
    if session:
        cookies = SimpleCookie()
        cookies["eface_user"] = session
        headers["Cookie"] = cookies.output(header="", sep=";").strip()
    try:
        status, upstream_headers, payload = await asyncio.to_thread(fetch, method, path, query, headers, bytes(body))
    except Exception:
        return HTMLResponse("<h2>Registro temporaneamente non disponibile</h2><p>Verifica che eFace sia avviato sullo stesso impianto. Lo storico resta salvato in eFace.</p>", status_code=503,
                            headers={"Cache-Control": "no-store"})
    if status in (301, 302, 303, 307, 308):
        location = upstream_headers.get("Location", "")
        if location not in ("login?next=events", "/login?next=events", "events", "/events"):
            return JSONResponse({"detail": "Reindirizzamento non consentito"}, status_code=502)
        return RedirectResponse(prefix + "/" + location.lstrip("/"), status_code=status)
    content_type = upstream_headers.get("Content-Type", "application/octet-stream")
    if path == "events" and "text/html" in content_type:
        # Keep the back link in the Hub workspace, including HA Ingress prefixes.
        import html
        payload = payload.replace(b'href="tools"', ('href="' + html.escape(base + '/index.html#event_register', quote=True) + '" target="_top"').encode())
    response = Response(payload, status_code=status, headers={"Content-Type": content_type,
        "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff", "Referrer-Policy": "same-origin"})
    for value in upstream_headers.get_all("Set-Cookie", []):
        cookies = SimpleCookie()
        cookies.load(value)
        if "eface_user" in cookies:
            cookie = cookies["eface_user"]
            response.set_cookie(SESSION, cookie.value, path=prefix + "/", httponly=True, samesite="strict",
                                secure=request.url.scheme == "https", max_age=int(cookie["max-age"]) if cookie["max-age"] else None)
    return response
