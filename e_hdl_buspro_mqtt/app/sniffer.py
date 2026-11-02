from __future__ import annotations

import json
import os
import time
from collections import deque
from dataclasses import dataclass
from typing import Any


def _safe_hex(data: Any) -> str | None:
    try:
        if isinstance(data, (bytes, bytearray)):
            return bytes(data).hex()
    except Exception:
        return None
    return None


def _safe_operate_code_raw(data: Any) -> tuple[str, int] | tuple[None, None]:
    # HDL BusPro frame: operate_code is 2 bytes at index 21..22 in the UDP payload
    # (see pybuspro/helpers/telegram_helper.py index_operate_code = 21).
    try:
        if not isinstance(data, (bytes, bytearray)):
            return (None, None)
        buf = bytes(data)
        if len(buf) < 23:
            return (None, None)
        oc = buf[21:23]
        hex_s = oc.hex()
        return (hex_s, int.from_bytes(oc, byteorder="big", signed=False))
    except Exception:
        return (None, None)


def _safe_list_addr(v: Any) -> list[int] | None:
    try:
        if isinstance(v, (list, tuple)) and len(v) == 2:
            return [int(v[0]), int(v[1])]
    except Exception:
        return None
    return None


@dataclass
class SnifferConfig:
    enabled: bool = False
    op_contains: list[str] | None = None
    src: list[int] | None = None  # [subnet, device] exact match
    dst: list[int] | None = None  # [subnet, device] exact match
    include_raw: bool = False
    write_file: bool = True
    file_path: str | None = None
    started_ts: float | None = None


class TelegramSniffer:
    def __init__(self, *, share_dir: str = "/share", maxlen: int = 5000) -> None:
        self._share_dir = share_dir
        self._buf: deque[dict[str, Any]] = deque(maxlen=max(100, int(maxlen or 5000)))
        self._cfg = SnifferConfig()
        self._fh = None
        self._matched = 0
        self._dropped = 0

    def status(self) -> dict[str, Any]:
        return {
            "enabled": bool(self._cfg.enabled),
            "buffer_len": len(self._buf),
            "buffer_max": int(getattr(self._buf, "maxlen", 0) or 0),
            "matched": int(self._matched),
            "dropped": int(self._dropped),
            "filters": {
                "op_contains": self._cfg.op_contains or [],
                "src": self._cfg.src,
                "dst": self._cfg.dst,
                "include_raw": bool(self._cfg.include_raw),
            },
            "write_file": bool(self._cfg.write_file),
            "file_path": self._cfg.file_path,
            "started_ts": self._cfg.started_ts,
        }

    def clear(self) -> None:
        self._buf.clear()
        self._matched = 0
        self._dropped = 0

    def stop(self) -> None:
        self._cfg.enabled = False
        self._cfg.started_ts = None
        if self._fh is not None:
            try:
                self._fh.flush()
            except Exception:
                pass
            try:
                self._fh.close()
            except Exception:
                pass
        self._fh = None

    def start(
        self,
        *,
        op_contains: list[str] | None = None,
        src: list[int] | None = None,
        dst: list[int] | None = None,
        include_raw: bool = False,
        write_file: bool = True,
        filename: str | None = None,
        clear: bool = False,
    ) -> None:
        if clear:
            self.clear()

        self.stop()

        ops = [str(x).strip() for x in (op_contains or []) if str(x).strip()]
        self._cfg.op_contains = ops or None
        self._cfg.src = src if (isinstance(src, list) and len(src) == 2) else None
        self._cfg.dst = dst if (isinstance(dst, list) and len(dst) == 2) else None
        self._cfg.include_raw = bool(include_raw)
        self._cfg.write_file = bool(write_file)
        self._cfg.started_ts = time.time()
        self._cfg.enabled = True

        if self._cfg.write_file:
            os.makedirs(self._share_dir, exist_ok=True)
            ts = time.strftime("%Y%m%d-%H%M%S")
            safe = (filename or "").strip() or f"buspro_sniffer_{ts}.jsonl"
            safe = safe.replace("\\", "_").replace("/", "_").replace("..", "_")
            path = os.path.join(self._share_dir, safe)
            self._cfg.file_path = path
            self._fh = open(path, "a", encoding="utf-8")
        else:
            self._cfg.file_path = None

    def dump_jsonl(self) -> str:
        # Snapshot buffer as jsonlines
        out = []
        for it in list(self._buf):
            out.append(json.dumps(it, ensure_ascii=False))
        return "\n".join(out) + ("\n" if out else "")

    def recent(self, limit: int = 50) -> list[dict[str, Any]]:
        n = max(1, min(int(limit or 50), 500))
        items = list(self._buf)
        return items[-n:]

    def on_telegram(self, telegram: Any) -> None:
        if not self._cfg.enabled:
            return

        try:
            op = str(getattr(telegram, "operate_code", "") or "")
            src_addr = _safe_list_addr(getattr(telegram, "source_address", None))
            dst_addr = _safe_list_addr(getattr(telegram, "target_address", None))

            if self._cfg.op_contains:
                op_l = op.lower()
                if not any(s.lower() in op_l for s in self._cfg.op_contains):
                    return
            if self._cfg.src and src_addr != self._cfg.src:
                return
            if self._cfg.dst and dst_addr != self._cfg.dst:
                return

            self._matched += 1
            raw = getattr(telegram, "udp_data", None)
            op_raw_hex, op_raw_int = _safe_operate_code_raw(raw)
            item: dict[str, Any] = {
                "ts": time.time(),
                "operate_code": op,
                "operate_code_raw_hex": op_raw_hex,
                "operate_code_raw_int": op_raw_int,
                "source_address": src_addr,
                "target_address": dst_addr,
                "payload": getattr(telegram, "payload", None),
                "udp_address": getattr(telegram, "udp_address", None),
            }
            if self._cfg.include_raw:
                item["udp_data_hex"] = _safe_hex(raw)
                item["udp_data_repr"] = str(raw) if item.get("udp_data_hex") is None else None

            self._buf.append(item)
            if self._fh is not None:
                try:
                    self._fh.write(json.dumps(item, ensure_ascii=False) + "\n")
                    self._fh.flush()
                except Exception:
                    self._dropped += 1
        except Exception:
            self._dropped += 1
