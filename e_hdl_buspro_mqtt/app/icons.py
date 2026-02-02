from __future__ import annotations

import os
import re
import urllib.request
from dataclasses import dataclass


_MDI_RE = re.compile(r"^mdi:([a-z0-9_-]+)$", re.IGNORECASE)


def parse_mdi_icon(value: str | None) -> str | None:
    if not value:
        return None
    m = _MDI_RE.match(value.strip())
    if not m:
        return None
    return m.group(1).lower()


def _safe_name(name: str) -> str | None:
    name = (name or "").strip().lower()
    if not name:
        return None
    if not re.fullmatch(r"[a-z0-9_-]+", name):
        return None
    return name


def mdi_cache_path(cache_dir: str, name: str) -> str:
    safe = _safe_name(name)
    if not safe:
        raise ValueError("Invalid icon name")
    return os.path.join(cache_dir, "mdi", f"{safe}.svg")


def _ensure_dirs(cache_dir: str) -> None:
    os.makedirs(os.path.join(cache_dir, "mdi"), exist_ok=True)


def _download(url: str, timeout_s: int = 15) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "buspro-addon/mdi-cache",
            "Accept": "image/svg+xml,*/*;q=0.8",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout_s) as r:  # nosec - controlled URL
        return r.read()


def fetch_mdi_svg(name: str) -> bytes:
    safe = _safe_name(name)
    if not safe:
        raise ValueError("Invalid icon name")
    url = f"https://raw.githubusercontent.com/Templarian/MaterialDesign/master/svg/{safe}.svg"
    return _download(url)


@dataclass
class IconSyncResult:
    requested: int
    downloaded: int
    failed: int
    missing: list[str]


def ensure_mdi_icons(cache_dir: str, names: list[str]) -> IconSyncResult:
    _ensure_dirs(cache_dir)
    unique: list[str] = []
    seen: set[str] = set()
    for n in names:
        safe = _safe_name(n)
        if not safe or safe in seen:
            continue
        seen.add(safe)
        unique.append(safe)

    downloaded = 0
    failed = 0
    missing: list[str] = []

    for name in unique:
        path = mdi_cache_path(cache_dir, name)
        if os.path.exists(path):
            continue
        try:
            svg = fetch_mdi_svg(name)
            with open(path, "wb") as f:
                f.write(svg)
            downloaded += 1
        except Exception:
            failed += 1
            missing.append(name)

    return IconSyncResult(
        requested=len(unique),
        downloaded=downloaded,
        failed=failed,
        missing=missing,
    )


def placeholder_svg() -> bytes:
    return (
        b'<?xml version="1.0" encoding="UTF-8"?>'
        b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24">'
        b'<path fill="currentColor" d="M12 2a7 7 0 0 0-4 12.74V17a2 2 0 0 0 2 2h4a2 2 0 0 0 2-2v-2.26A7 7 0 0 0 12 2zm3 12.06-.5.35V17h-5v-2.59l-.5-.35A5 5 0 1 1 15 14.06zM9 21v-1h6v1H9z"/>'
        b"</svg>"
    )

