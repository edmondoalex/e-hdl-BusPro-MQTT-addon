from __future__ import annotations

import json
import os
import re
import time
import uuid
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Device:
    name: str
    subnet_id: int
    device_id: int
    channel: int
    dimmable: bool

    @property
    def addr(self) -> str:
        return f"{self.subnet_id}.{self.device_id}.{self.channel}"


class StateStore:
    def __init__(self, path: str = "/data/state.json"):
        self._path = path

    @staticmethod
    def default_hub_icons() -> dict[str, str]:
        return {
            "lights": "mdi:lightbulb-group",
            "scenarios": "mdi:star",
            "covers": "mdi:window-shutter",
            "locks": "mdi:lock-smart",
            "extra": "mdi:shape",
            "guard": "mdi:cctv",
        }

    @staticmethod
    def default_hub_show() -> dict[str, bool]:
        return {
            "lights": True,
            "scenarios": True,
            "covers": True,
            "locks": True,
            "extra": True,
            "guard": True,
        }

    @staticmethod
    def _default_ui() -> dict[str, Any]:
        return {
            "group_order": [],
            "cover_groups": [],
            "cover_groups_published": [],
            "light_scenarios": [],
            "light_scenarios_published": [],
            "scenario_ha_triggers": [],
            "scenario_ha_triggers_published": [],
            "hub_order": ["lights", "scenarios", "covers", "locks", "extra", "guard"],
            "ha_devices": [],
            "hub_links": [],
            "home_actions": [],
            "home2_order": [],
            "guard_cameras": [],
            "hub_icons": StateStore.default_hub_icons(),
            "hub_show": StateStore.default_hub_show(),
            "proxy_targets": [],
            "pwa": {
                "name": "Ekonex",
                "short_name": "Ekonex",
                "start_url": "/home2",
                "icon_url": "/static/e-face-nobg.png",
                "theme_color": "#05070b",
                "background_color": "#05070b",
            },
        }

    @property
    def path(self) -> str:
        return self._path

    def read_raw(self) -> dict[str, Any]:
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except FileNotFoundError:
            raw = {
                "devices": [],
                "states": {},
                "ui": self._default_ui(),
            }
        except (json.JSONDecodeError, ValueError):
            # File corrotto: salvalo per debug e riparti da stato vuoto.
            try:
                ts = time.strftime("%Y%m%d-%H%M%S")
                os.replace(self._path, f"{self._path}.corrupt.{ts}")
            except Exception:
                pass
            raw = {
                "devices": [],
                "states": {},
                "ui": self._default_ui(),
            }

        raw.setdefault("devices", [])
        raw.setdefault("states", {})
        raw.setdefault("ui", self._default_ui())
        if not isinstance(raw.get("ui"), dict):
            raw["ui"] = self._default_ui()
        raw["ui"].setdefault("group_order", [])
        raw["ui"].setdefault("cover_groups", [])
        raw["ui"].setdefault("cover_groups_published", [])
        raw["ui"].setdefault("light_scenarios", [])
        raw["ui"].setdefault("light_scenarios_published", [])
        raw["ui"].setdefault("scenario_ha_triggers", [])
        raw["ui"].setdefault("scenario_ha_triggers_published", [])
        raw["ui"].setdefault("hub_order", self._default_ui().get("hub_order"))
        raw["ui"].setdefault("ha_devices", [])
        raw["ui"].setdefault("hub_links", [])
        raw["ui"].setdefault("home_actions", [])
        raw["ui"].setdefault("home2_order", [])
        raw["ui"].setdefault("guard_cameras", [])
        raw["ui"].setdefault("hub_icons", self.default_hub_icons())
        raw["ui"].setdefault("hub_show", self.default_hub_show())
        raw["ui"].setdefault("proxy_targets", [])
        raw["ui"].setdefault("pwa", self._default_ui().get("pwa"))
        if not isinstance(raw["ui"].get("hub_icons", {}), dict):
            raw["ui"]["hub_icons"] = self.default_hub_icons()
        else:
            icons = dict(raw["ui"].get("hub_icons") or {})
            defaults = self.default_hub_icons()
            for k, dv in defaults.items():
                if not str(icons.get(k) or "").strip():
                    icons[k] = dv
            raw["ui"]["hub_icons"] = icons

        if not isinstance(raw["ui"].get("hub_show", {}), dict):
            raw["ui"]["hub_show"] = self.default_hub_show()
        else:
            show = dict(raw["ui"].get("hub_show") or {})
            defaults_show = self.default_hub_show()
            changed = False
            for k, dv in defaults_show.items():
                if k not in show:
                    show[k] = dv
                    changed = True
                else:
                    show[k] = bool(show.get(k))
            if changed:
                raw["ui"]["hub_show"] = show

        if not isinstance(raw["ui"].get("proxy_targets", []), list):
            raw["ui"]["proxy_targets"] = []
        if not isinstance(raw["ui"].get("light_scenarios", []), list):
            raw["ui"]["light_scenarios"] = []
        if not isinstance(raw["ui"].get("light_scenarios_published", []), list):
            raw["ui"]["light_scenarios_published"] = []
        if not isinstance(raw["ui"].get("scenario_ha_triggers", []), list):
            raw["ui"]["scenario_ha_triggers"] = []
        if not isinstance(raw["ui"].get("scenario_ha_triggers_published", []), list):
            raw["ui"]["scenario_ha_triggers_published"] = []
        if not isinstance(raw["ui"].get("hub_order", []), list):
            raw["ui"]["hub_order"] = list(self._default_ui().get("hub_order") or [])
        if not isinstance(raw["ui"].get("ha_devices", []), list):
            raw["ui"]["ha_devices"] = []
        if not isinstance(raw["ui"].get("hub_links", []), list):
            raw["ui"]["hub_links"] = []
        if not isinstance(raw["ui"].get("home_actions", []), list):
            raw["ui"]["home_actions"] = []
        if not isinstance(raw["ui"].get("home2_order", []), list):
            raw["ui"]["home2_order"] = []
        if not isinstance(raw["ui"].get("pwa", {}), dict):
            raw["ui"]["pwa"] = self._default_ui().get("pwa")
        return raw

    def cleanup_light_scenarios_no_pct(self) -> dict[str, Any]:
        """
        Remove SET_POSITION from scenario covers and clear any stored position.
        This enforces direct-only commands (OPEN/CLOSE/STOP) for scenarios.
        """
        raw = self.read_raw()
        ui = dict(raw.get("ui") or {})
        items = ui.get("light_scenarios") or []
        if not isinstance(items, list):
            return {"changed": False, "updated": 0}

        changed = False
        updated = 0
        out_items: list[dict[str, Any]] = []
        for sc in items:
            if not isinstance(sc, dict):
                continue
            cur = dict(sc)
            covers = cur.get("covers") or []
            if isinstance(covers, list):
                new_covers: list[dict[str, Any]] = []
                for it in covers:
                    if not isinstance(it, dict):
                        continue
                    c = dict(it)
                    cmd = str(c.get("command") or "").strip().upper()
                    if cmd == "SET_POSITION":
                        c["command"] = "STOP"
                        c["position"] = None
                        changed = True
                    else:
                        if c.get("position") is not None:
                            c["position"] = None
                            changed = True
                    new_covers.append(c)
                if new_covers != covers:
                    cur["covers"] = new_covers
                    changed = True
            out_items.append(cur)
        if changed:
            ui["light_scenarios"] = out_items
            raw["ui"] = ui
            self.write_raw(raw)
            updated = len(out_items)
        return {"changed": changed, "updated": updated}

    def get_pwa_config(self) -> dict[str, Any]:
        ui = self.read_raw().get("ui", {}) or {}
        pwa = ui.get("pwa", {}) if isinstance(ui, dict) else {}
        if not isinstance(pwa, dict):
            pwa = {}
        d = self._default_ui().get("pwa", {}) or {}
        out = {**d, **pwa}
        # Basic normalization
        out["name"] = str(out.get("name") or "").strip() or str(d.get("name") or "Ekonex")
        out["short_name"] = str(out.get("short_name") or "").strip() or str(out["name"])
        out["start_url"] = str(out.get("start_url") or "").strip() or str(d.get("start_url") or "/home2")
        if not out["start_url"].startswith("/"):
            out["start_url"] = "/" + out["start_url"]
        out["icon_url"] = str(out.get("icon_url") or "").strip() or str(d.get("icon_url") or "/static/e-face-nobg.png")
        if not out["icon_url"].startswith("/"):
            out["icon_url"] = "/" + out["icon_url"]
        out["theme_color"] = str(out.get("theme_color") or "").strip() or str(d.get("theme_color") or "#05070b")
        out["background_color"] = str(out.get("background_color") or "").strip() or str(d.get("background_color") or "#05070b")
        return out

    def set_pwa_config(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise ValueError("payload must be an object")
        raw = self.read_raw()
        ui = raw.get("ui", self._default_ui())
        if not isinstance(ui, dict):
            ui = self._default_ui()
        current = self.get_pwa_config()
        merged = {**current, **payload}
        # Only keep known keys
        cleaned = {
            "name": str(merged.get("name") or "").strip(),
            "short_name": str(merged.get("short_name") or "").strip(),
            "start_url": str(merged.get("start_url") or "").strip(),
            "icon_url": str(merged.get("icon_url") or "").strip(),
            "theme_color": str(merged.get("theme_color") or "").strip(),
            "background_color": str(merged.get("background_color") or "").strip(),
        }
        if not cleaned["name"]:
            cleaned["name"] = current.get("name") or "Ekonex"
        if not cleaned["short_name"]:
            cleaned["short_name"] = cleaned["name"]
        if not cleaned["start_url"]:
            cleaned["start_url"] = current.get("start_url") or "/home2"
        if not cleaned["start_url"].startswith("/"):
            cleaned["start_url"] = "/" + cleaned["start_url"]
        if not cleaned["icon_url"]:
            cleaned["icon_url"] = current.get("icon_url") or "/static/e-face-nobg.png"
        if not cleaned["icon_url"].startswith("/"):
            cleaned["icon_url"] = "/" + cleaned["icon_url"]
        if not cleaned["theme_color"]:
            cleaned["theme_color"] = current.get("theme_color") or "#05070b"
        if not cleaned["background_color"]:
            cleaned["background_color"] = current.get("background_color") or "#05070b"
        ui["pwa"] = cleaned
        raw["ui"] = ui
        self.write_raw(raw)
        return cleaned

    def write_raw(self, state: dict[str, Any]) -> None:
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        tmp = self._path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self._path)

    def backup_current(self) -> str | None:
        """Create a text backup of the current state file on disk."""
        try:
            if not os.path.exists(self._path):
                return None
            ts = time.strftime("%Y%m%d-%H%M%S")
            dst = f"{self._path}.bak.{ts}"
            with open(self._path, "rb") as src_f:
                data = src_f.read()
            with open(dst, "wb") as dst_f:
                dst_f.write(data)
            return dst
        except Exception:
            return None

    def export_backup_text(self) -> str:
        raw = self.read_raw()
        raw.setdefault("devices", [])
        raw.setdefault("states", {})
        raw.setdefault("ui", self._default_ui())
        if not isinstance(raw.get("ui"), dict):
            raw["ui"] = self._default_ui()
        raw["ui"].setdefault("group_order", [])
        raw["ui"].setdefault("cover_groups", [])
        raw["ui"].setdefault("cover_groups_published", [])
        raw["ui"].setdefault("light_scenarios", [])
        raw["ui"].setdefault("light_scenarios_published", [])
        raw["ui"].setdefault("scenario_ha_triggers", [])
        raw["ui"].setdefault("scenario_ha_triggers_published", [])
        raw["ui"].setdefault("hub_order", self._default_ui().get("hub_order"))
        raw["ui"].setdefault("ha_devices", [])
        raw["ui"].setdefault("hub_links", [])
        raw["ui"].setdefault("home_actions", [])
        raw["ui"].setdefault("home2_order", [])
        raw["ui"].setdefault("hub_icons", self.default_hub_icons())
        raw["ui"].setdefault("hub_show", self.default_hub_show())
        raw["ui"].setdefault("proxy_targets", [])
        return json.dumps(raw, ensure_ascii=False, indent=2)

    def import_backup(self, state: dict[str, Any]) -> None:
        if not isinstance(state, dict):
            raise ValueError("backup must be a JSON object")
        devices = state.get("devices", [])
        states = state.get("states", {})
        ui = state.get("ui", self._default_ui())
        if not isinstance(devices, list):
            raise ValueError("backup.devices must be a list")
        if not isinstance(states, dict):
            raise ValueError("backup.states must be an object")
        if not isinstance(ui, dict):
            ui = self._default_ui()
        # Normalize group_order payload (but keep device data as-is)
        go = ui.get("group_order", [])
        if isinstance(go, str):
            go_list = [s.strip() for s in go.splitlines() if s.strip()]
        elif isinstance(go, list):
            go_list = [str(x).strip() for x in go if str(x).strip()]
        else:
            go_list = []
        ui["group_order"] = [s[1:].strip() if s.startswith("#") else s for s in go_list if s]
        if not isinstance(ui.get("cover_groups", []), list):
            ui["cover_groups"] = []
        if not isinstance(ui.get("cover_groups_published", []), list):
            ui["cover_groups_published"] = []
        if not isinstance(ui.get("light_scenarios", []), list):
            ui["light_scenarios"] = []
        if not isinstance(ui.get("light_scenarios_published", []), list):
            ui["light_scenarios_published"] = []
        if not isinstance(ui.get("scenario_ha_triggers", []), list):
            ui["scenario_ha_triggers"] = []
        if not isinstance(ui.get("scenario_ha_triggers_published", []), list):
            ui["scenario_ha_triggers_published"] = []
        if not isinstance(ui.get("hub_order", []), list):
            ui["hub_order"] = list(self._default_ui().get("hub_order") or [])
        if not isinstance(ui.get("ha_devices", []), list):
            ui["ha_devices"] = []
        if not isinstance(ui.get("hub_links", []), list):
            ui["hub_links"] = []
        if not isinstance(ui.get("home_actions", []), list):
            ui["home_actions"] = []
        if not isinstance(ui.get("home2_order", []), list):
            ui["home2_order"] = []
        if not isinstance(ui.get("hub_icons", {}), dict):
            ui["hub_icons"] = self.default_hub_icons()
        if not isinstance(ui.get("hub_show", {}), dict):
            ui["hub_show"] = self.default_hub_show()
        if not isinstance(ui.get("proxy_targets", []), list):
            ui["proxy_targets"] = []
        self.write_raw({"devices": devices, "states": states, "ui": ui})

    def list_ha_devices(self) -> list[dict[str, Any]]:
        raw = self.read_raw()
        ui = raw.get("ui") or {}
        items = ui.get("ha_devices") or []
        if not isinstance(items, list):
            return []
        out: list[dict[str, Any]] = []
        for it in items:
            if isinstance(it, dict):
                out.append(dict(it))
        return out

    @staticmethod
    def _normalize_ha_device(payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise ValueError("payload must be an object")

        entity_id = str(payload.get("entity_id") or "").strip().lower()
        if not entity_id or "." not in entity_id:
            raise ValueError("entity_id required (e.g. light.kitchen)")

        domain = entity_id.split(".", 1)[0]
        if domain not in ("light", "switch", "cover", "lock"):
            raise ValueError("only light/switch/cover/lock supported")

        page = str(payload.get("page") or "").strip().lower() or (
            "covers" if domain == "cover" else ("locks" if domain == "lock" else "lights")
        )
        if page not in ("lights", "extra", "covers", "locks"):
            raise ValueError("page must be lights/extra/covers/locks")

        name = str(payload.get("name") or "").strip()
        group = str(payload.get("group") or "").strip()
        icon = str(payload.get("icon") or "").strip()
        if icon and not icon.startswith("mdi:"):
            raise ValueError("icon must be mdi:<name>")

        def _opt_entity(key: str) -> str:
            v = str(payload.get(key) or "").strip().lower()
            if not v:
                return ""
            if "." not in v:
                raise ValueError(f"{key} must be an entity_id (e.g. sensor.xxx)")
            return v

        out = {
            "entity_id": entity_id,
            "domain": domain,
            "page": page,
            "name": name,
            "group": group,
            "icon": icon,
        }
        # Optional external HA entities for lock metrics (used when page=locks).
        out["lock_battery_entity_id"] = _opt_entity("lock_battery_entity_id")
        out["lock_battery_low_entity_id"] = _opt_entity("lock_battery_low_entity_id")
        out["lock_rssi_entity_id"] = _opt_entity("lock_rssi_entity_id")
        out["lock_linkquality_entity_id"] = _opt_entity("lock_linkquality_entity_id")
        out["lock_tamper_entity_id"] = _opt_entity("lock_tamper_entity_id")
        return out

    def add_ha_device(self, payload: dict[str, Any]) -> dict[str, Any]:
        cleaned = self._normalize_ha_device(payload)
        item = {"id": str(uuid.uuid4()), **cleaned}
        raw = self.read_raw()
        ui = dict(raw.get("ui") or {})
        items = ui.get("ha_devices") or []
        if not isinstance(items, list):
            items = []
        items2 = [dict(it) for it in items if isinstance(it, dict)]
        # de-dupe by entity_id: keep last
        items2 = [it for it in items2 if str(it.get("entity_id") or "").strip().lower() != cleaned["entity_id"]]
        items2.append(item)
        ui["ha_devices"] = items2
        raw["ui"] = ui
        self.write_raw(raw)
        return item

    def update_ha_device(self, *, device_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        did = str(device_id or "").strip()
        if not did:
            return None
        cleaned = self._normalize_ha_device(payload)
        raw = self.read_raw()
        ui = dict(raw.get("ui") or {})
        items = ui.get("ha_devices") or []
        if not isinstance(items, list):
            return None
        out: list[dict[str, Any]] = []
        updated: dict[str, Any] | None = None
        for it in items:
            if not isinstance(it, dict):
                continue
            if str(it.get("id") or "").strip() != did:
                out.append(dict(it))
                continue
            updated = {"id": did, **cleaned}
            out.append(updated)
        if updated is None:
            return None
        # de-dupe by entity_id (keep last)
        deduped: list[dict[str, Any]] = []
        seen: set[str] = set()
        for it in reversed(out):
            eid = str(it.get("entity_id") or "").strip().lower()
            if not eid or eid in seen:
                continue
            seen.add(eid)
            deduped.append(it)
        deduped.reverse()
        ui["ha_devices"] = deduped
        raw["ui"] = ui
        self.write_raw(raw)
        return updated

    def delete_ha_device(self, *, device_id: str) -> bool:
        did = str(device_id or "").strip()
        if not did:
            return False
        raw = self.read_raw()
        ui = dict(raw.get("ui") or {})
        items = ui.get("ha_devices") or []
        if not isinstance(items, list):
            return False
        before = len([it for it in items if isinstance(it, dict)])
        kept = [dict(it) for it in items if isinstance(it, dict) and str(it.get("id") or "").strip() != did]
        if len(kept) == before:
            return False
        ui["ha_devices"] = kept
        raw["ui"] = ui
        self.write_raw(raw)
        return True

    def list_guard_cameras(self) -> list[dict[str, Any]]:
        raw = self.read_raw()
        ui = raw.get("ui") or {}
        items = ui.get("guard_cameras") or []
        if not isinstance(items, list):
            return []
        out: list[dict[str, Any]] = []
        for it in items:
            if isinstance(it, dict):
                out.append(dict(it))
        return out

    def find_guard_camera_by_entity(self, entity_id: str) -> dict[str, Any] | None:
        eid = str(entity_id or "").strip().lower()
        if not eid:
            return None
        for it in self.list_guard_cameras():
            if str(it.get("entity_id") or "").strip().lower() == eid:
                return dict(it)
        return None

    @staticmethod
    def _normalize_guard_camera(payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise ValueError("payload must be an object")
        entity_id = str(payload.get("entity_id") or "").strip().lower()
        name = str(payload.get("name") or "").strip()
        if not name:
            name = entity_id
        refresh_s = payload.get("refresh_s")
        if refresh_s is None or refresh_s == "":
            refresh_s = 5
        try:
            refresh_s = int(refresh_s)
        except Exception:
            refresh_s = 5
        refresh_s = max(1, min(60, refresh_s))
        source = str(payload.get("source") or "ha").strip().lower()
        if source not in ("ha", "dahua"):
            source = "ha"
        dahua_host = str(payload.get("dahua_host") or "").strip()
        dahua_user = str(payload.get("dahua_user") or "").strip()
        dahua_pass = str(payload.get("dahua_pass") or "").strip()
        dahua_mode = str(payload.get("dahua_mode") or "nvr").strip().lower()
        if dahua_mode not in ("nvr", "camera", "custom"):
            dahua_mode = "nvr"
        dahua_url = str(payload.get("dahua_url") or "").strip()
        dahua_channel = payload.get("dahua_channel")
        if dahua_channel is None or dahua_channel == "":
            dahua_channel = 1
        try:
            dahua_channel = int(dahua_channel)
        except Exception:
            dahua_channel = 1
        dahua_channel = max(1, min(256, dahua_channel))
        if dahua_mode == "camera":
            dahua_channel = 1
        if source == "dahua":
            if not entity_id:
                entity_id = f"dahua.{uuid.uuid4()}"
            if dahua_mode == "custom":
                if not dahua_url:
                    raise ValueError("dahua_url required for source=dahua mode=custom")
            else:
                if not (dahua_host and dahua_user and dahua_pass):
                    raise ValueError("dahua_host/dahua_user/dahua_pass required for source=dahua")
        if source == "ha":
            if not entity_id.startswith("camera."):
                raise ValueError("entity_id must be a camera.* entity")
        return {
            "entity_id": entity_id,
            "name": name,
            "refresh_s": refresh_s,
            "source": source,
            "dahua_mode": dahua_mode,
            "dahua_host": dahua_host,
            "dahua_user": dahua_user,
            "dahua_pass": dahua_pass,
            "dahua_channel": dahua_channel,
            "dahua_url": dahua_url,
        }

    def add_guard_camera(self, payload: dict[str, Any]) -> dict[str, Any]:
        cleaned = self._normalize_guard_camera(payload)
        item = {"id": str(uuid.uuid4()), **cleaned}
        raw = self.read_raw()
        ui = dict(raw.get("ui") or {})
        items = ui.get("guard_cameras") or []
        if not isinstance(items, list):
            items = []
        items2 = [dict(it) for it in items if isinstance(it, dict)]
        # de-dupe by entity_id: keep last
        items2 = [it for it in items2 if str(it.get("entity_id") or "").strip().lower() != cleaned["entity_id"]]
        items2.append(item)
        ui["guard_cameras"] = items2
        raw["ui"] = ui
        self.write_raw(raw)
        return item

    def update_guard_camera(self, *, camera_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        cid = str(camera_id or "").strip()
        if not cid:
            return None
        cleaned = self._normalize_guard_camera(payload)
        raw = self.read_raw()
        ui = dict(raw.get("ui") or {})
        items = ui.get("guard_cameras") or []
        if not isinstance(items, list):
            return None
        out: list[dict[str, Any]] = []
        updated: dict[str, Any] | None = None
        for it in items:
            if not isinstance(it, dict):
                continue
            if str(it.get("id") or "").strip() != cid:
                out.append(dict(it))
                continue
            updated = {"id": cid, **cleaned}
            out.append(updated)
        if updated is None:
            return None
        # de-dupe by entity_id (keep last)
        deduped: list[dict[str, Any]] = []
        seen: set[str] = set()
        for it in reversed(out):
            eid = str(it.get("entity_id") or "").strip().lower()
            if not eid or eid in seen:
                continue
            seen.add(eid)
            deduped.append(it)
        deduped.reverse()
        ui["guard_cameras"] = deduped
        raw["ui"] = ui
        self.write_raw(raw)
        return updated

    def delete_guard_camera(self, *, camera_id: str) -> bool:
        cid = str(camera_id or "").strip()
        if not cid:
            return False
        raw = self.read_raw()
        ui = dict(raw.get("ui") or {})
        items = ui.get("guard_cameras") or []
        if not isinstance(items, list):
            return False
        before = len([it for it in items if isinstance(it, dict)])
        kept = [dict(it) for it in items if isinstance(it, dict) and str(it.get("id") or "").strip() != cid]
        if len(kept) == before:
            return False
        ui["guard_cameras"] = kept
        raw["ui"] = ui
        self.write_raw(raw)
        return True

    def get_published_light_scenario_ids(self) -> list[str]:
        raw = self.read_raw()
        ui = raw.get("ui") or {}
        ids = ui.get("light_scenarios_published") or []
        if not isinstance(ids, list):
            return []
        out: list[str] = []
        for v in ids:
            s = str(v or "").strip()
            if not s:
                continue
            out.append(s)
        # de-dupe preserving order
        cleaned: list[str] = []
        seen: set[str] = set()
        for s in out:
            k = s.casefold()
            if k in seen:
                continue
            seen.add(k)
            cleaned.append(s)
        return cleaned

    def set_published_light_scenario_ids(self, ids: list[str]) -> list[str]:
        cleaned: list[str] = []
        seen: set[str] = set()
        for v in ids or []:
            s = str(v or "").strip()
            if not s:
                continue
            k = s.casefold()
            if k in seen:
                continue
            seen.add(k)
            cleaned.append(s)
        raw = self.read_raw()
        ui = dict(raw.get("ui") or {})
        ui["light_scenarios_published"] = cleaned
        raw["ui"] = ui
        self.write_raw(raw)
        return cleaned

    def list_scenario_ha_triggers(self) -> list[dict[str, Any]]:
        raw = self.read_raw()
        ui = raw.get("ui") or {}
        items = ui.get("scenario_ha_triggers") or []
        if not isinstance(items, list):
            return []
        out: list[dict[str, Any]] = []
        for it in items:
            if not isinstance(it, dict):
                continue
            tid = str(it.get("id") or "").strip()
            name = str(it.get("name") or "").strip()
            if not tid or not name:
                continue
            out.append({"id": tid, "name": name})
        return out

    @staticmethod
    def _normalize_scenario_ha_trigger(payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise ValueError("payload must be an object")
        name = str(payload.get("name") or "").strip()
        if not name:
            raise ValueError("name is required")
        if len(name) > 80:
            name = name[:80].strip()
        return {"name": name}

    def add_scenario_ha_trigger(self, payload: dict[str, Any]) -> dict[str, Any]:
        cleaned = self._normalize_scenario_ha_trigger(payload)
        item = {"id": str(uuid.uuid4()), "name": cleaned["name"]}
        raw = self.read_raw()
        ui = dict(raw.get("ui") or {})
        items = ui.get("scenario_ha_triggers") or []
        if not isinstance(items, list):
            items = []
        out = [dict(it) for it in items if isinstance(it, dict)]
        out.append(item)
        ui["scenario_ha_triggers"] = out
        raw["ui"] = ui
        self.write_raw(raw)
        return item

    def update_scenario_ha_trigger(self, *, trigger_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        tid = str(trigger_id or "").strip()
        if not tid:
            return None
        cleaned = self._normalize_scenario_ha_trigger(payload)
        raw = self.read_raw()
        ui = dict(raw.get("ui") or {})
        items = ui.get("scenario_ha_triggers") or []
        if not isinstance(items, list):
            return None
        updated: dict[str, Any] | None = None
        out: list[dict[str, Any]] = []
        for it in items:
            if not isinstance(it, dict):
                continue
            iid = str(it.get("id") or "").strip()
            if iid != tid:
                out.append(dict(it))
                continue
            updated = {"id": tid, "name": cleaned["name"]}
            out.append(updated)
        if updated is None:
            return None
        ui["scenario_ha_triggers"] = out
        raw["ui"] = ui
        self.write_raw(raw)
        return updated

    def delete_scenario_ha_trigger(self, *, trigger_id: str) -> bool:
        tid = str(trigger_id or "").strip()
        if not tid:
            return False
        raw = self.read_raw()
        ui = dict(raw.get("ui") or {})
        items = ui.get("scenario_ha_triggers") or []
        if not isinstance(items, list):
            return False
        before = len([it for it in items if isinstance(it, dict)])
        kept = [dict(it) for it in items if isinstance(it, dict) and str(it.get("id") or "").strip() != tid]
        if len(kept) == before:
            return False
        # Also unlink deleted trigger from scenarios.
        scenarios = ui.get("light_scenarios") or []
        if isinstance(scenarios, list):
            cleaned_scenarios: list[dict[str, Any]] = []
            for sc in scenarios:
                if not isinstance(sc, dict):
                    continue
                cur = dict(sc)
                if str(cur.get("ha_trigger_id") or "").strip() == tid:
                    cur["ha_trigger_id"] = ""
                    cur["ha_trigger_enabled"] = False
                cleaned_scenarios.append(cur)
            ui["light_scenarios"] = cleaned_scenarios
        ui["scenario_ha_triggers"] = kept
        raw["ui"] = ui
        self.write_raw(raw)
        return True

    def get_published_scenario_ha_trigger_ids(self) -> list[str]:
        raw = self.read_raw()
        ui = raw.get("ui") or {}
        ids = ui.get("scenario_ha_triggers_published") or []
        if not isinstance(ids, list):
            return []
        out: list[str] = []
        for v in ids:
            s = str(v or "").strip()
            if s:
                out.append(s)
        cleaned: list[str] = []
        seen: set[str] = set()
        for s in out:
            k = s.casefold()
            if k in seen:
                continue
            seen.add(k)
            cleaned.append(s)
        return cleaned

    def set_published_scenario_ha_trigger_ids(self, ids: list[str]) -> list[str]:
        cleaned: list[str] = []
        seen: set[str] = set()
        for v in ids or []:
            s = str(v or "").strip()
            if not s:
                continue
            k = s.casefold()
            if k in seen:
                continue
            seen.add(k)
            cleaned.append(s)
        raw = self.read_raw()
        ui = dict(raw.get("ui") or {})
        ui["scenario_ha_triggers_published"] = cleaned
        raw["ui"] = ui
        self.write_raw(raw)
        return cleaned

    def list_light_scenarios(self) -> list[dict[str, Any]]:
        raw = self.read_raw()
        ui = raw.get("ui") or {}
        items = ui.get("light_scenarios") or []
        if not isinstance(items, list):
            return []
        out: list[dict[str, Any]] = []
        for it in items:
            if isinstance(it, dict):
                cur = dict(it)
                if "run_enabled" not in cur:
                    cur["run_enabled"] = False
                if "onoff_enabled" not in cur:
                    cur["onoff_enabled"] = True
                if "ha_trigger_enabled" not in cur:
                    cur["ha_trigger_enabled"] = False
                if "ha_trigger_id" not in cur:
                    cur["ha_trigger_id"] = ""
                if "combination_targets" not in cur or not isinstance(cur.get("combination_targets"), list):
                    cur["combination_targets"] = []
                out.append(cur)
        return out

    def find_light_scenario(self, *, scenario_id: str) -> dict[str, Any] | None:
        sid = str(scenario_id or "").strip()
        if not sid:
            return None
        for it in self.list_light_scenarios():
            if str(it.get("id") or "").strip() == sid:
                return it
        return None

    @staticmethod
    def _normalize_light_scenario_payload(payload: dict[str, Any], *, require_name: bool) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise ValueError("payload must be an object")

        name = str(payload.get("name") or "").strip()
        if require_name and not name:
            raise ValueError("name is required")
        if len(name) > 80:
            name = name[:80].strip()

        items_in = payload.get("items") or []
        if items_in is None:
            items_in = []
        if not isinstance(items_in, list):
            raise ValueError("items must be a list")

        items_map: dict[str, dict[str, Any]] = {}
        for it in items_in:
            if not isinstance(it, dict):
                continue

            # Home Assistant entities (light/switch) in scenarios (stored by entity_id)
            entity_id = str(it.get("entity_id") or "").strip().lower()
            if entity_id and "." in entity_id:
                domain = entity_id.split(".", 1)[0]
                if domain not in ("light", "switch"):
                    continue
                st = str(it.get("state") or "").strip().upper()
                if st not in ("ON", "OFF"):
                    continue
                br = it.get("brightness")
                if domain != "light" or br is None or st == "OFF":
                    br255 = None
                else:
                    try:
                        br255 = int(br)
                    except Exception:
                        br255 = None
                    if br255 is not None:
                        br255 = max(0, min(255, br255))
                items_map[f"ha:{entity_id}"] = {
                    "entity_id": entity_id,
                    "domain": domain,
                    "state": st,
                    "brightness": br255,
                }
                continue

            try:
                subnet_id = int(it.get("subnet_id"))
                device_id = int(it.get("device_id"))
                channel = int(it.get("channel"))
            except Exception:
                continue
            st = str(it.get("state") or "").strip().upper()
            if st not in ("ON", "OFF"):
                continue
            br = it.get("brightness")
            if br is None or st == "OFF":
                br255 = None
            else:
                try:
                    br255 = int(br)
                except Exception:
                    br255 = None
                if br255 is not None:
                    br255 = max(0, min(255, br255))
            items_map[f"buspro:{subnet_id}.{device_id}.{channel}"] = {
                "subnet_id": subnet_id,
                "device_id": device_id,
                "channel": channel,
                "state": st,
                "brightness": br255,
            }
        items: list[dict[str, Any]] = list(items_map.values())

        covers_in = payload.get("covers") or []
        if covers_in is None:
            covers_in = []
        if not isinstance(covers_in, list):
            raise ValueError("covers must be a list")

        covers: list[dict[str, Any]] = []
        for it in covers_in:
            if not isinstance(it, dict):
                continue
            kind = str(it.get("kind") or "single").strip().lower()
            if kind not in ("single", "group", "ha"):
                kind = "single"

            cmd = str(it.get("command") or "").strip().upper()
            if cmd not in ("OPEN", "CLOSE", "STOP", "SET_POSITION"):
                continue

            ramp_minutes = it.get("ramp_minutes")
            if ramp_minutes is None or ramp_minutes == "":
                ramp_minutes_i = 0
            else:
                try:
                    ramp_minutes_i = int(float(ramp_minutes))
                except Exception:
                    ramp_minutes_i = 0
            ramp_minutes_i = max(0, min(240, ramp_minutes_i))

            step_seconds = it.get("step_seconds")
            if step_seconds is None or step_seconds == "":
                step_seconds_i = 5
            else:
                try:
                    step_seconds_i = int(float(step_seconds))
                except Exception:
                    step_seconds_i = 5
            step_seconds_i = max(1, min(120, step_seconds_i))

            pos = it.get("position")
            if cmd == "SET_POSITION":
                try:
                    pos_i = int(pos)
                except Exception:
                    continue
                pos_i = max(0, min(100, pos_i))
            else:
                pos_i = None

            if kind == "group":
                gid = str(it.get("group_id") or it.get("id") or "").strip()
                if not gid:
                    continue
                covers.append(
                    {
                        "kind": "group",
                        "group_id": gid,
                        "command": cmd,
                        "position": pos_i,
                        "ramp_minutes": ramp_minutes_i,
                        "step_seconds": step_seconds_i,
                    }
                )
                continue

            if kind == "ha":
                entity_id = str(it.get("entity_id") or "").strip().lower()
                if not entity_id.startswith("cover."):
                    continue
                covers.append(
                    {
                        "kind": "ha",
                        "entity_id": entity_id,
                        "command": cmd,
                        "position": pos_i,
                        "ramp_minutes": ramp_minutes_i,
                        "step_seconds": step_seconds_i,
                    }
                )
                continue

            try:
                subnet_id = int(it.get("subnet_id"))
                device_id = int(it.get("device_id"))
                channel = int(it.get("channel"))
            except Exception:
                continue
            covers.append(
                {
                    "kind": "single",
                    "subnet_id": subnet_id,
                    "device_id": device_id,
                    "channel": channel,
                    "command": cmd,
                    "position": pos_i,
                    "ramp_minutes": ramp_minutes_i,
                    "step_seconds": step_seconds_i,
                }
            )

        combination_targets_in = payload.get("combination_targets")
        if combination_targets_in is None:
            combination_targets_in = []
        if not isinstance(combination_targets_in, list):
            raise ValueError("combination_targets must be a list")
        combination_targets_map: dict[str, dict[str, int]] = {}
        for it in combination_targets_in:
            if not isinstance(it, dict):
                continue
            try:
                subnet_id = int(it.get("subnet_id"))
                device_id = int(it.get("device_id"))
                switch_number = int(it.get("switch_number"))
            except Exception:
                continue
            if switch_number < 1 or switch_number > 255:
                continue
            combination_targets_map[f"{subnet_id}.{device_id}.{switch_number}"] = {
                "subnet_id": subnet_id,
                "device_id": device_id,
                "switch_number": switch_number,
            }
        combination_targets: list[dict[str, int]] = list(combination_targets_map.values())

        out: dict[str, Any] = {
            "name": name,
            "items": items,
            "covers": covers,
            "combination_targets": combination_targets,
        }
        if "run_enabled" in payload:
            out["run_enabled"] = bool(payload.get("run_enabled"))
        if "onoff_enabled" in payload:
            out["onoff_enabled"] = bool(payload.get("onoff_enabled"))
        if "ha_trigger_enabled" in payload:
            out["ha_trigger_enabled"] = bool(payload.get("ha_trigger_enabled"))
        if "ha_trigger_id" in payload:
            out["ha_trigger_id"] = str(payload.get("ha_trigger_id") or "").strip()
            if len(str(out["ha_trigger_id"])) > 80:
                out["ha_trigger_id"] = str(out["ha_trigger_id"])[:80].strip()
        if bool(out.get("ha_trigger_enabled")) and not str(out.get("ha_trigger_id") or "").strip():
            out["ha_trigger_enabled"] = False
        trig_in = payload.get("trigger")
        if isinstance(trig_in, dict):
            t_type = str(trig_in.get("type") or "none").strip().lower()
            if t_type not in ("none", "time", "sunrise", "sunset", "sveglia"):
                t_type = "none"
            t_enabled = bool(trig_in.get("enabled")) if "enabled" in trig_in else False
            t_time = str(trig_in.get("time") or "").strip()
            if t_time and not re.fullmatch(r"\d{1,2}:\d{2}", t_time):
                t_time = ""
            try:
                t_offset = int(float(trig_in.get("offset_min") or 0))
            except Exception:
                t_offset = 0
            t_offset = max(-1440, min(1440, t_offset))
            out["trigger"] = {
                "enabled": t_enabled,
                "type": t_type,
                "time": t_time,
                "offset_min": t_offset,
            }
        return out

    def add_light_scenario(self, payload: dict[str, Any]) -> dict[str, Any]:
        cleaned = self._normalize_light_scenario_payload(payload, require_name=True)
        scenario_id = str(uuid.uuid4())
        run_enabled = bool(cleaned.get("run_enabled")) if "run_enabled" in cleaned else False
        onoff_enabled = bool(cleaned.get("onoff_enabled")) if "onoff_enabled" in cleaned else True
        ha_trigger_enabled = bool(cleaned.get("ha_trigger_enabled")) if "ha_trigger_enabled" in cleaned else False
        ha_trigger_id = str(cleaned.get("ha_trigger_id") or "").strip() if "ha_trigger_id" in cleaned else ""
        out = {
            "id": scenario_id,
            "name": cleaned["name"],
            "items": cleaned["items"],
            "covers": cleaned.get("covers") or [],
            "combination_targets": cleaned.get("combination_targets") or [],
            "run_enabled": run_enabled,
            "onoff_enabled": onoff_enabled,
            "ha_trigger_enabled": ha_trigger_enabled,
            "ha_trigger_id": ha_trigger_id,
        }
        if "trigger" in cleaned:
            out["trigger"] = cleaned.get("trigger") or {}

        raw = self.read_raw()
        ui = dict(raw.get("ui") or {})
        items = ui.get("light_scenarios") or []
        if not isinstance(items, list):
            items = []
        items2 = [dict(x) for x in items if isinstance(x, dict)]
        items2.append(out)
        ui["light_scenarios"] = items2
        raw["ui"] = ui
        self.write_raw(raw)
        return out

    def update_light_scenario(self, *, scenario_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        sid = str(scenario_id or "").strip()
        if not sid:
            return None
        cleaned = self._normalize_light_scenario_payload(payload, require_name=False)

        raw = self.read_raw()
        ui = dict(raw.get("ui") or {})
        items = ui.get("light_scenarios") or []
        if not isinstance(items, list):
            return None

        updated: dict[str, Any] | None = None
        out_items: list[dict[str, Any]] = []
        for it in items:
            if not isinstance(it, dict):
                continue
            if str(it.get("id") or "").strip() != sid:
                out_items.append(dict(it))
                continue
            cur = dict(it)
            if cleaned.get("name"):
                cur["name"] = cleaned["name"]
            if "items" in cleaned:
                cur["items"] = cleaned["items"]
            if "covers" in cleaned:
                cur["covers"] = cleaned.get("covers") or []
            if "combination_targets" in cleaned:
                cur["combination_targets"] = cleaned.get("combination_targets") or []
            if "run_enabled" in cleaned:
                cur["run_enabled"] = bool(cleaned.get("run_enabled"))
            if "onoff_enabled" in cleaned:
                cur["onoff_enabled"] = bool(cleaned.get("onoff_enabled"))
            if "ha_trigger_enabled" in cleaned:
                cur["ha_trigger_enabled"] = bool(cleaned.get("ha_trigger_enabled"))
            if "ha_trigger_id" in cleaned:
                cur["ha_trigger_id"] = str(cleaned.get("ha_trigger_id") or "").strip()
            if "trigger" in cleaned:
                cur["trigger"] = cleaned.get("trigger") or {}
            updated = cur
            out_items.append(cur)

        if updated is None:
            return None

        ui["light_scenarios"] = out_items
        raw["ui"] = ui
        self.write_raw(raw)
        return updated

    def delete_light_scenario(self, *, scenario_id: str) -> bool:
        sid = str(scenario_id or "").strip()
        if not sid:
            return False

        raw = self.read_raw()
        ui = dict(raw.get("ui") or {})
        items = ui.get("light_scenarios") or []
        if not isinstance(items, list):
            return False

        kept = [dict(it) for it in items if isinstance(it, dict) and str(it.get("id") or "").strip() != sid]
        if len(kept) == len([it for it in items if isinstance(it, dict)]):
            return False

        ui["light_scenarios"] = kept
        raw["ui"] = ui
        self.write_raw(raw)
        return True

    def list_devices(self) -> list[dict[str, Any]]:
        return list(self.read_raw().get("devices", []))

    def find_device(self, *, type_: str, subnet_id: int, device_id: int, channel: int) -> dict[str, Any] | None:
        t = str(type_ or "").strip().lower()
        for d in self.list_devices():
            if (
                str(d.get("type") or "light").strip().lower() == t
                and int(d.get("subnet_id")) == int(subnet_id)
                and int(d.get("device_id")) == int(device_id)
                and int(d.get("channel")) == int(channel)
            ):
                return d
        return None

    def dedupe_devices(self) -> dict[str, Any]:
        """
        Remove duplicates keeping the most recent (last) definition.
        Key is (type, subnet_id, device_id, channel).
        """
        raw = self.read_raw()
        devices = list(raw.get("devices", []))
        if not devices:
            return {"changed": False, "removed": 0, "kept": 0, "keys": []}

        last_idx: dict[tuple[str, int, int, int], int] = {}
        last_dev: dict[tuple[str, int, int, int], dict[str, Any]] = {}

        for idx, d in enumerate(devices):
            try:
                key = (
                    str(d.get("type") or "light").strip().lower(),
                    int(d.get("subnet_id")),
                    int(d.get("device_id")),
                    int(d.get("channel")),
                )
            except Exception:
                # Keep invalid entries as unique by index so we don't lose data unexpectedly.
                key = (f"invalid:{idx}", idx, idx, idx)
            last_idx[key] = idx
            last_dev[key] = d

        ordered_keys = sorted(last_idx.keys(), key=lambda k: last_idx[k])
        deduped = [last_dev[k] for k in ordered_keys]

        removed = max(0, len(devices) - len(deduped))
        if removed == 0:
            return {"changed": False, "removed": 0, "kept": len(deduped), "keys": []}

        raw["devices"] = deduped
        self.write_raw(raw)

        keys_out = []
        for k in ordered_keys:
            if str(k[0]).startswith("invalid:"):
                continue
            keys_out.append({"type": k[0], "subnet_id": k[1], "device_id": k[2], "channel": k[3]})

        return {"changed": True, "removed": removed, "kept": len(deduped), "keys": keys_out}

    def add_device(self, device: dict[str, Any]) -> dict[str, Any]:
        state = self.read_raw()
        devices = list(state.get("devices", []))
        devices.append(device)
        state["devices"] = devices
        state.setdefault("states", {})
        self.write_raw(state)
        return device

    def update_device(self, *, subnet_id: int, device_id: int, channel: int, updates: dict[str, Any]) -> dict[str, Any] | None:
        raw = self.read_raw()
        devices = list(raw.get("devices", []))

        updated: dict[str, Any] | None = None
        for idx, d in enumerate(devices):
            if (
                int(d.get("subnet_id")) == int(subnet_id)
                and int(d.get("device_id")) == int(device_id)
                and int(d.get("channel")) == int(channel)
            ):
                new_d = dict(d)
                for k, v in (updates or {}).items():
                    if v is None:
                        new_d.pop(k, None)
                    else:
                        new_d[k] = v
                devices[idx] = new_d
                updated = new_d
                break

        if updated is None:
            return None

        raw["devices"] = devices
        self.write_raw(raw)
        return updated

    def update_device_typed(self, *, type_: str, subnet_id: int, device_id: int, channel: int, updates: dict[str, Any]) -> dict[str, Any] | None:
        t = str(type_ or "").strip().lower()
        raw = self.read_raw()
        devices = list(raw.get("devices", []))

        updated: dict[str, Any] | None = None
        for idx, d in enumerate(devices):
            if (
                str(d.get("type") or "light").strip().lower() == t
                and int(d.get("subnet_id")) == int(subnet_id)
                and int(d.get("device_id")) == int(device_id)
                and int(d.get("channel")) == int(channel)
            ):
                new_d = dict(d)
                for k, v in (updates or {}).items():
                    if v is None:
                        new_d.pop(k, None)
                    else:
                        new_d[k] = v
                devices[idx] = new_d
                updated = new_d
                break

        if updated is None:
            return None

        raw["devices"] = devices
        self.write_raw(raw)
        return updated

    def clear_devices(self) -> None:
        state = self.read_raw()
        state["devices"] = []
        state["states"] = {}
        self.write_raw(state)

    def get_states(self) -> dict[str, Any]:
        raw = self.read_raw()
        return dict(raw.get("states", {}) or {})

    def get_group_order(self) -> list[str]:
        raw = self.read_raw()
        ui = raw.get("ui") or {}
        order = ui.get("group_order") or []
        if not isinstance(order, list):
            return []
        out: list[str] = []
        for v in order:
            s = str(v or "").strip()
            if not s:
                continue
            if s.startswith("#"):
                s = s[1:].strip()
            if not s:
                continue
            out.append(s)
        return out

    def set_group_order(self, group_order: list[str]) -> list[str]:
        # de-duplicate preserving order
        cleaned: list[str] = []
        seen: set[str] = set()
        for v in group_order or []:
            s = str(v or "").strip()
            if not s:
                continue
            if s.startswith("#"):
                s = s[1:].strip()
            if not s:
                continue
            key = s.casefold()
            if key in seen:
                continue
            seen.add(key)
            cleaned.append(s)

        raw = self.read_raw()
        ui = dict(raw.get("ui") or {})
        ui["group_order"] = cleaned
        raw["ui"] = ui
        self.write_raw(raw)
        return cleaned

    def get_hub_icons(self) -> dict[str, str]:
        raw = self.read_raw()
        ui = raw.get("ui") or {}
        icons = ui.get("hub_icons") or {}
        out: dict[str, str] = dict(self.default_hub_icons())
        if isinstance(icons, dict):
            for k in out.keys():
                v = str(icons.get(k) or "").strip()
                if v:
                    out[k] = v
        return out

    def set_hub_icons(self, icons: dict[str, Any]) -> dict[str, str]:
        defaults = self.default_hub_icons()
        cleaned: dict[str, str] = {}
        for k, dv in defaults.items():
            v = str((icons or {}).get(k) or "").strip()
            cleaned[k] = v or dv
        raw = self.read_raw()
        ui = dict(raw.get("ui") or {})
        ui["hub_icons"] = cleaned
        raw["ui"] = ui
        self.write_raw(raw)
        return cleaned

    def get_hub_show(self) -> dict[str, bool]:
        raw = self.read_raw()
        ui = raw.get("ui") or {}
        show = ui.get("hub_show") or {}
        out: dict[str, bool] = dict(self.default_hub_show())
        if isinstance(show, dict):
            for k in out.keys():
                out[k] = bool(show.get(k, out[k]))
        return out

    def set_hub_show(self, show: dict[str, Any]) -> dict[str, bool]:
        defaults = self.default_hub_show()
        cleaned: dict[str, bool] = {}
        for k, dv in defaults.items():
            cleaned[k] = bool((show or {}).get(k, dv))
        raw = self.read_raw()
        ui = dict(raw.get("ui") or {})
        ui["hub_show"] = cleaned
        raw["ui"] = ui
        self.write_raw(raw)
        return cleaned

    def get_hub_order(self) -> list[str]:
        raw = self.read_raw()
        ui = raw.get("ui") or {}
        order = ui.get("hub_order") or []
        if not isinstance(order, list):
            order = []
        allowed = ["lights", "scenarios", "covers", "locks", "extra", "guard"]
        out: list[str] = []
        seen: set[str] = set()
        for v in order:
            k = str(v or "").strip().lower()
            if k in allowed and k not in seen:
                seen.add(k)
                out.append(k)
        for k in allowed:
            if k not in seen:
                out.append(k)
        return out

    def set_hub_order(self, order: list[Any]) -> list[str]:
        allowed = ["lights", "scenarios", "covers", "locks", "extra", "guard"]
        out: list[str] = []
        seen: set[str] = set()
        for v in order or []:
            k = str(v or "").strip().lower()
            if k in allowed and k not in seen:
                seen.add(k)
                out.append(k)
        for k in allowed:
            if k not in seen:
                out.append(k)
        raw = self.read_raw()
        ui = dict(raw.get("ui") or {})
        ui["hub_order"] = out
        raw["ui"] = ui
        self.write_raw(raw)
        return out

    def get_home2_order(self) -> list[str]:
        raw = self.read_raw()
        ui = raw.get("ui") or {}
        order = ui.get("home2_order") or []
        if not isinstance(order, list):
            return []
        out: list[str] = []
        seen: set[str] = set()
        for v in order:
            token = str(v or "").strip().lower()
            if not token or token in seen:
                continue
            if re.fullmatch(r"fixed:(lights|scenarios|covers|locks|extra|guard)", token) or re.fullmatch(
                r"(action|link):[a-f0-9]{4,64}",
                token,
            ):
                seen.add(token)
                out.append(token)
        return out

    def set_home2_order(self, order: list[Any]) -> list[str]:
        out: list[str] = []
        seen: set[str] = set()
        for v in order or []:
            token = str(v or "").strip().lower()
            if not token or token in seen:
                continue
            if re.fullmatch(r"fixed:(lights|scenarios|covers|locks|extra|guard)", token) or re.fullmatch(
                r"(action|link):[a-f0-9]{4,64}",
                token,
            ):
                seen.add(token)
                out.append(token)
        raw = self.read_raw()
        ui = dict(raw.get("ui") or {})
        ui["home2_order"] = out
        raw["ui"] = ui
        self.write_raw(raw)
        return out

    def list_proxy_targets(self) -> list[dict[str, Any]]:
        raw = self.read_raw()
        ui = raw.get("ui") or {}
        items = ui.get("proxy_targets") or []
        if not isinstance(items, list):
            return []
        out: list[dict[str, Any]] = []
        for it in items:
            if isinstance(it, dict):
                out.append(dict(it))
        return out

    def upsert_proxy_target(self, target: dict[str, Any]) -> dict[str, Any]:
        name = str(target.get("name") or "").strip()
        base_url = str(target.get("base_url") or "").strip()
        if not name:
            raise ValueError("name required")
        if not re.fullmatch(r"[a-zA-Z0-9_-]{1,32}", name):
            raise ValueError("name must match [a-zA-Z0-9_-]{1,32}")
        if not base_url:
            raise ValueError("base_url required")
        if not re.match(r"^https?://", base_url, flags=re.IGNORECASE):
            raise ValueError("base_url must start with http:// or https://")

        icon = str(target.get("icon") or "").strip() or None
        show = bool(target.get("show", True))

        item: dict[str, Any] = {"name": name, "base_url": base_url, "icon": icon, "show": show}

        raw = self.read_raw()
        ui = dict(raw.get("ui") or {})
        items = ui.get("proxy_targets") or []
        if not isinstance(items, list):
            items = []
        out: list[dict[str, Any]] = []
        replaced = False
        for it in items:
            if isinstance(it, dict) and str(it.get("name") or "").strip() == name:
                out.append(item)
                replaced = True
            elif isinstance(it, dict):
                out.append(dict(it))
        if not replaced:
            out.append(item)
        ui["proxy_targets"] = out
        raw["ui"] = ui
        self.write_raw(raw)
        return item

    def delete_proxy_target(self, *, name: str) -> bool:
        key = str(name or "").strip()
        if not key:
            return False
        raw = self.read_raw()
        ui = dict(raw.get("ui") or {})
        items = ui.get("proxy_targets") or []
        if not isinstance(items, list):
            return False
        before = len(items)
        items2 = [it for it in items if not (isinstance(it, dict) and str(it.get("name") or "").strip() == key)]
        if len(items2) == before:
            return False
        ui["proxy_targets"] = items2
        raw["ui"] = ui
        self.write_raw(raw)
        return True

    def find_proxy_target(self, *, name: str) -> dict[str, Any] | None:
        key = str(name or "").strip()
        if not key:
            return None
        for it in self.list_proxy_targets():
            if str(it.get("name") or "").strip() == key:
                return it
        return None

    def list_hub_links(self) -> list[dict[str, Any]]:
        raw = self.read_raw()
        ui = raw.get("ui") or {}
        links = ui.get("hub_links") or []
        if not isinstance(links, list):
            return []
        out: list[dict[str, Any]] = []
        for it in links:
            if isinstance(it, dict):
                out.append(dict(it))
        return out

    def list_visible_hub_links(self) -> list[dict[str, Any]]:
        return [it for it in self.list_hub_links() if bool(it.get("show", True))]

    def upsert_hub_link(self, link: dict[str, Any]) -> dict[str, Any]:
        title = str(link.get("title") or "").strip()
        url = str(link.get("url") or "").strip()
        if not title:
            raise ValueError("title required")
        if not url:
            raise ValueError("url required")
        if url.lower().startswith(("javascript:", "data:")):
            raise ValueError("unsupported url scheme")

        link_id = str(link.get("id") or "").strip() or uuid.uuid4().hex

        icon = str(link.get("icon") or "").strip() or None
        show = bool(link.get("show", True))
        new_tab = bool(link.get("new_tab", True))

        item: dict[str, Any] = {
            "id": link_id,
            "title": title,
            "url": url,
            "icon": icon,
            "show": show,
            "new_tab": new_tab,
        }

        raw = self.read_raw()
        ui = dict(raw.get("ui") or {})
        links = ui.get("hub_links") or []
        if not isinstance(links, list):
            links = []

        out: list[dict[str, Any]] = []
        replaced = False
        for it in links:
            if isinstance(it, dict) and str(it.get("id") or "").strip() == link_id:
                out.append(item)
                replaced = True
            elif isinstance(it, dict):
                out.append(dict(it))
        if not replaced:
            out.append(item)

        ui["hub_links"] = out
        raw["ui"] = ui
        self.write_raw(raw)
        return item

    def delete_hub_link(self, *, link_id: str) -> bool:
        lid = str(link_id or "").strip()
        if not lid:
            return False
        raw = self.read_raw()
        ui = dict(raw.get("ui") or {})
        links = ui.get("hub_links") or []
        if not isinstance(links, list):
            return False
        before = len(links)
        links2 = [it for it in links if not (isinstance(it, dict) and str(it.get("id") or "").strip() == lid)]
        if len(links2) == before:
            return False
        ui["hub_links"] = links2
        raw["ui"] = ui
        self.write_raw(raw)
        return True

    def set_hub_links(self, links: list[dict[str, Any]]) -> list[dict[str, Any]]:
        cleaned: list[dict[str, Any]] = []
        seen: set[str] = set()
        for it in links or []:
            if not isinstance(it, dict):
                continue
            try:
                item = self.upsert_hub_link(it)
            except Exception:
                continue
            lid = str(item.get("id") or "")
            if not lid or lid in seen:
                continue
            seen.add(lid)
            cleaned.append(item)

        raw = self.read_raw()
        ui = dict(raw.get("ui") or {})
        ui["hub_links"] = cleaned
        raw["ui"] = ui
        self.write_raw(raw)
        return cleaned

    def list_home_actions(self) -> list[dict[str, Any]]:
        raw = self.read_raw()
        ui = raw.get("ui") or {}
        items = ui.get("home_actions") or []
        if not isinstance(items, list):
            return []
        out: list[dict[str, Any]] = []
        for it in items:
            if isinstance(it, dict):
                out.append(dict(it))
        return out

    def list_visible_home_actions(self) -> list[dict[str, Any]]:
        return [it for it in self.list_home_actions() if bool(it.get("show", True))]

    @staticmethod
    def _normalize_home_action(payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise ValueError("payload must be an object")

        title = str(payload.get("title") or "").strip()
        if not title:
            raise ValueError("title required")
        if len(title) > 40:
            title = title[:40].strip()

        icon = str(payload.get("icon") or "").strip() or None
        if icon and not icon.startswith("mdi:"):
            raise ValueError("icon must be mdi:<name>")

        show = bool(payload.get("show", True))
        confirm = bool(payload.get("confirm", False))

        kind = str(payload.get("kind") or "").strip().lower()
        if kind not in ("ha", "buspro_light", "buspro_cover", "cover_group", "scenario"):
            raise ValueError("kind unsupported")

        action = str(payload.get("action") or "").strip().upper()
        data = payload.get("data") or {}
        if data is None:
            data = {}
        if not isinstance(data, dict):
            raise ValueError("data must be an object")

        # minimal validation per kind
        if kind == "ha":
            entity_id = str(data.get("entity_id") or "").strip().lower()
            if not entity_id or "." not in entity_id:
                raise ValueError("data.entity_id required")
            domain = entity_id.split(".", 1)[0]
            if domain not in ("light", "switch", "cover"):
                raise ValueError("only light/switch/cover supported")
            if domain in ("light", "switch"):
                if action not in ("TOGGLE", "ON", "OFF"):
                    raise ValueError("action must be TOGGLE/ON/OFF for light/switch")
            else:
                if action not in ("OPEN", "CLOSE", "STOP", "SET_POSITION"):
                    raise ValueError("action must be OPEN/CLOSE/STOP/SET_POSITION for cover")
                if action == "SET_POSITION":
                    try:
                        pos = int(data.get("position"))
                    except Exception:
                        raise ValueError("data.position required")
                    data["position"] = max(0, min(100, pos))
        elif kind == "buspro_light":
            addr = str(data.get("addr") or "").strip()
            if not addr or addr.count(".") != 2:
                raise ValueError("data.addr required (subnet.device.channel)")
            if action not in ("TOGGLE", "ON", "OFF"):
                raise ValueError("action must be TOGGLE/ON/OFF")
        elif kind == "buspro_cover":
            addr = str(data.get("addr") or "").strip()
            if not addr or addr.count(".") != 2:
                raise ValueError("data.addr required (subnet.device.channel)")
            if action not in ("OPEN", "CLOSE", "STOP", "SET_POSITION"):
                raise ValueError("action must be OPEN/CLOSE/STOP/SET_POSITION")
            if action == "SET_POSITION":
                try:
                    pos = int(data.get("position"))
                except Exception:
                    raise ValueError("data.position required")
                data["position"] = max(0, min(100, pos))
        elif kind == "cover_group":
            gid = str(data.get("group_id") or "").strip()
            if not gid:
                raise ValueError("data.group_id required")
            if action not in ("OPEN", "CLOSE", "STOP", "SET_POSITION"):
                raise ValueError("action must be OPEN/CLOSE/STOP/SET_POSITION")
            if action == "SET_POSITION":
                try:
                    pos = int(data.get("position"))
                except Exception:
                    raise ValueError("data.position required")
                data["position"] = max(0, min(100, pos))
        else:  # scenario
            sid = str(data.get("scenario_id") or "").strip()
            if not sid:
                raise ValueError("data.scenario_id required")
            if action not in ("TOGGLE", "ON", "OFF", "RUN"):
                raise ValueError("action must be TOGGLE/ON/OFF/RUN")

        return {"title": title, "icon": icon, "show": show, "confirm": confirm, "kind": kind, "action": action, "data": data}

    def upsert_home_action(self, payload: dict[str, Any]) -> dict[str, Any]:
        action_id = str(payload.get("id") or "").strip() or uuid.uuid4().hex
        cleaned = self._normalize_home_action(payload)
        item: dict[str, Any] = {"id": action_id, **cleaned}

        raw = self.read_raw()
        ui = dict(raw.get("ui") or {})
        items = ui.get("home_actions") or []
        if not isinstance(items, list):
            items = []

        out: list[dict[str, Any]] = []
        replaced = False
        for it in items:
            if isinstance(it, dict) and str(it.get("id") or "").strip() == action_id:
                out.append(item)
                replaced = True
            elif isinstance(it, dict):
                out.append(dict(it))
        if not replaced:
            out.append(item)

        ui["home_actions"] = out
        raw["ui"] = ui
        self.write_raw(raw)
        return item

    def delete_home_action(self, *, action_id: str) -> bool:
        aid = str(action_id or "").strip()
        if not aid:
            return False
        raw = self.read_raw()
        ui = dict(raw.get("ui") or {})
        items = ui.get("home_actions") or []
        if not isinstance(items, list):
            return False
        before = len(items)
        items2 = [it for it in items if not (isinstance(it, dict) and str(it.get("id") or "").strip() == aid)]
        if len(items2) == before:
            return False
        ui["home_actions"] = items2
        raw["ui"] = ui
        self.write_raw(raw)
        return True

    def set_home_actions(self, actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
        cleaned: list[dict[str, Any]] = []
        seen: set[str] = set()
        for it in actions or []:
            if not isinstance(it, dict):
                continue
            try:
                item = self.upsert_home_action(it)
            except Exception:
                continue
            aid = str(item.get("id") or "")
            if not aid or aid in seen:
                continue
            seen.add(aid)
            cleaned.append(item)

        raw = self.read_raw()
        ui = dict(raw.get("ui") or {})
        ui["home_actions"] = cleaned
        raw["ui"] = ui
        self.write_raw(raw)
        return cleaned

    def find_home_action(self, *, action_id: str) -> dict[str, Any] | None:
        aid = str(action_id or "").strip()
        if not aid:
            return None
        for it in self.list_home_actions():
            if str(it.get("id") or "").strip() == aid:
                return it
        return None

    @staticmethod
    def _slugify(text: str) -> str:
        s = str(text or "").strip().lower()
        s = re.sub(r"[^a-z0-9_\- ]+", "", s)
        s = re.sub(r"[\s\-]+", "_", s).strip("_")
        return s or "group"

    def list_cover_groups(self) -> list[dict[str, Any]]:
        raw = self.read_raw()
        ui = raw.get("ui") or {}
        groups = ui.get("cover_groups") or []
        if not isinstance(groups, list):
            return []

        # Ensure every group has a stable unique id, persisted.
        used_ids: set[str] = set()
        changed = False
        for idx, g in enumerate(list(groups)):
            if not isinstance(g, dict):
                continue
            name = str(g.get("name") or "").strip()
            if not name:
                continue
            gid = str(g.get("id") or "").strip()
            base = gid or self._slugify(name)
            gid2 = base
            n = 2
            while gid2.casefold() in used_ids:
                gid2 = f"{base}_{n}"
                n += 1
            if gid2 != gid:
                ng = dict(g)
                ng["id"] = gid2
                groups[idx] = ng
                changed = True
            used_ids.add(gid2.casefold())

        if changed:
            ui = dict(ui)
            ui["cover_groups"] = groups
            raw["ui"] = ui
            self.write_raw(raw)
            raw = self.read_raw()
            ui = raw.get("ui") or {}
            groups = ui.get("cover_groups") or []

        out: list[dict[str, Any]] = []
        seen_ids: set[str] = set()
        for g in groups:
            if not isinstance(g, dict):
                continue
            gid = str(g.get("id") or "").strip()
            name = str(g.get("name") or "").strip()
            if not name or not gid:
                continue
            key = gid.casefold()
            if key in seen_ids:
                continue
            seen_ids.add(key)

            members = g.get("members") or []
            if not isinstance(members, list):
                members = []
            norm_members: list[str] = []
            memb_seen: set[str] = set()
            for m in members:
                s = str(m or "").strip()
                if not s:
                    continue
                mk = s.casefold()
                if mk in memb_seen:
                    continue
                memb_seen.add(mk)
                norm_members.append(s)
            out_item: dict[str, Any] = {"id": gid, "name": name, "members": norm_members}
            icon = str(g.get("icon") or "").strip()
            if icon:
                out_item["icon"] = icon
            out.append(out_item)
        return out

    def get_cover_group(self, key: str) -> dict[str, Any] | None:
        target = str(key or "").strip().casefold()
        if not target:
            return None
        for g in self.list_cover_groups():
            if str(g.get("id") or "").strip().casefold() == target or str(g.get("name") or "").strip().casefold() == target:
                return g
        return None

    def upsert_cover_group(
        self,
        *,
        group_id: str | None = None,
        name: str,
        members: list[str],
        icon: str | None = None,
    ) -> dict[str, Any]:
        nm = str(name or "").strip()
        if not nm:
            raise ValueError("group name required")

        gid_in = str(group_id or "").strip()
        icon_in = None if icon is None else str(icon or "").strip()

        norm_members: list[str] = []
        seen: set[str] = set()
        for m in members or []:
            s = str(m or "").strip()
            if not s:
                continue
            key = s.casefold()
            if key in seen:
                continue
            seen.add(key)
            norm_members.append(s)

        # Ensure ids exist before updating
        _ = self.list_cover_groups()

        raw = self.read_raw()
        ui = raw.get("ui") or {}
        groups = ui.get("cover_groups") or []
        if not isinstance(groups, list):
            groups = []

        used_ids: set[str] = set()
        for g in groups:
            if not isinstance(g, dict):
                continue
            gid0 = str(g.get("id") or "").strip()
            if gid0:
                used_ids.add(gid0.casefold())

        updated: dict[str, Any] | None = None
        out_groups: list[dict[str, Any]] = []

        if gid_in:
            for g in groups:
                if not isinstance(g, dict):
                    continue
                gid0 = str(g.get("id") or "").strip()
                if gid0 and gid0.casefold() == gid_in.casefold():
                    keep_icon = str(g.get("icon") or "").strip()
                    updated = {"id": gid0, "name": nm, "members": norm_members}
                    if icon_in is None:
                        if keep_icon:
                            updated["icon"] = keep_icon
                    else:
                        if icon_in:
                            updated["icon"] = icon_in
                    out_groups.append(updated)
                else:
                    out_groups.append(g)
            if updated is None:
                if gid_in.casefold() in used_ids:
                    raise ValueError("duplicate group id")
                updated = {"id": gid_in, "name": nm, "members": norm_members}
                if icon_in:
                    updated["icon"] = icon_in
                out_groups.append(updated)
        else:
            for g in groups:
                if not isinstance(g, dict):
                    continue
                gname = str(g.get("name") or "").strip()
                if not gname:
                    continue
                if gname.casefold() == nm.casefold():
                    gid0 = str(g.get("id") or "").strip() or self._slugify(nm)
                    keep_icon = str(g.get("icon") or "").strip()
                    updated = {"id": gid0, "name": nm, "members": norm_members}
                    if icon_in is None:
                        if keep_icon:
                            updated["icon"] = keep_icon
                    else:
                        if icon_in:
                            updated["icon"] = icon_in
                    out_groups.append(updated)
                else:
                    out_groups.append(g)

            if updated is None:
                base = self._slugify(nm)
                gid0 = base
                n = 2
                while gid0.casefold() in used_ids:
                    gid0 = f"{base}_{n}"
                    n += 1
                updated = {"id": gid0, "name": nm, "members": norm_members}
                if icon_in:
                    updated["icon"] = icon_in
                out_groups.append(updated)

        ui["cover_groups"] = out_groups
        ui.setdefault("group_order", [])
        raw["ui"] = ui
        self.write_raw(raw)
        return updated

    def delete_cover_group(self, key: str) -> bool:
        nm = str(key or "").strip()
        if not nm:
            return False

        _ = self.list_cover_groups()
        raw = self.read_raw()
        ui = raw.get("ui") or {}
        groups = ui.get("cover_groups") or []
        if not isinstance(groups, list):
            return False
        before = len(groups)
        kept: list[dict[str, Any]] = []
        for g in groups:
            if not isinstance(g, dict):
                continue
            gid0 = str(g.get("id") or "").strip()
            gname = str(g.get("name") or "").strip()
            if not gname:
                continue
            if (gid0 and gid0.casefold() == nm.casefold()) or gname.casefold() == nm.casefold():
                continue
            kept.append(g)
        if len(kept) == before:
            return False
        ui["cover_groups"] = kept
        raw["ui"] = ui
        self.write_raw(raw)
        return True

    def get_published_cover_group_ids(self) -> list[str]:
        raw = self.read_raw()
        ui = raw.get("ui") or {}
        ids = ui.get("cover_groups_published") or []
        if not isinstance(ids, list):
            return []
        out: list[str] = []
        seen: set[str] = set()
        for v in ids:
            s = str(v or "").strip()
            if not s:
                continue
            k = s.casefold()
            if k in seen:
                continue
            seen.add(k)
            out.append(s)
        return out

    def set_published_cover_group_ids(self, ids: list[str]) -> list[str]:
        cleaned: list[str] = []
        seen: set[str] = set()
        for v in ids or []:
            s = str(v or "").strip()
            if not s:
                continue
            k = s.casefold()
            if k in seen:
                continue
            seen.add(k)
            cleaned.append(s)

        raw = self.read_raw()
        ui = dict(raw.get("ui") or {})
        ui["cover_groups_published"] = cleaned
        raw["ui"] = ui
        self.write_raw(raw)
        return cleaned

    def set_light_state(self, *, subnet_id: int, device_id: int, channel: int, state: str, brightness: int | None) -> None:
        raw = self.read_raw()
        states = dict(raw.get("states", {}) or {})
        key = f"light:{subnet_id}.{device_id}.{channel}"
        states[key] = {
            "state": str(state).upper(),
            "brightness": int(brightness) if brightness is not None else None,
        }
        raw["states"] = states
        self.write_raw(raw)

    def set_cover_state(self, *, subnet_id: int, device_id: int, channel: int, state: str, position: int | None) -> None:
        raw = self.read_raw()
        states = dict(raw.get("states", {}) or {})
        key = f"cover:{subnet_id}.{device_id}.{channel}"
        states[key] = {
            "state": str(state).upper(),
            "position": int(position) if position is not None else None,
        }
        raw["states"] = states
        self.write_raw(raw)

    def set_cover_group_state(self, *, group_id: str, state: str, position: int | None) -> None:
        gid = str(group_id or "").strip()
        if not gid:
            return
        raw = self.read_raw()
        states = dict(raw.get("states", {}) or {})
        key = f"cover_group:{gid}"
        states[key] = {
            "state": str(state).upper(),
            "position": int(position) if position is not None else None,
        }
        raw["states"] = states
        self.write_raw(raw)

    def set_temp_state(self, *, subnet_id: int, device_id: int, channel: int, value: float, ts: float | None = None) -> None:
        raw = self.read_raw()
        states = dict(raw.get("states", {}) or {})
        key = f"temp:{subnet_id}.{device_id}.{channel}"
        states[key] = {
            "value": float(value),
            "ts": float(ts) if ts is not None else None,
        }
        raw["states"] = states
        self.write_raw(raw)

    def set_humidity_state(self, *, subnet_id: int, device_id: int, channel: int, value: float, ts: float | None = None) -> None:
        raw = self.read_raw()
        states = dict(raw.get("states", {}) or {})
        key = f"humidity:{subnet_id}.{device_id}.{channel}"
        states[key] = {
            "value": float(value),
            "ts": float(ts) if ts is not None else None,
        }
        raw["states"] = states
        self.write_raw(raw)

    def set_illuminance_state(self, *, subnet_id: int, device_id: int, channel: int, value: float, ts: float | None = None) -> None:
        raw = self.read_raw()
        states = dict(raw.get("states", {}) or {})
        key = f"illuminance:{subnet_id}.{device_id}.{channel}"
        states[key] = {
            "value": float(value),
            "ts": float(ts) if ts is not None else None,
        }
        raw["states"] = states
        self.write_raw(raw)

    def set_air_quality_state(self, *, subnet_id: int, device_id: int, channel: int, state: str, ts: float | None = None) -> None:
        raw = self.read_raw()
        states = dict(raw.get("states", {}) or {})
        key = f"air_quality:{subnet_id}.{device_id}.{channel}"
        states[key] = {
            "state": str(state),
            "ts": float(ts) if ts is not None else None,
        }
        raw["states"] = states
        self.write_raw(raw)

    def set_gas_percent_state(self, *, subnet_id: int, device_id: int, channel: int, value: float, ts: float | None = None) -> None:
        raw = self.read_raw()
        states = dict(raw.get("states", {}) or {})
        key = f"gas_percent:{subnet_id}.{device_id}.{channel}"
        states[key] = {
            "value": float(value),
            "ts": float(ts) if ts is not None else None,
        }
        raw["states"] = states
        self.write_raw(raw)

    def set_pir_state(self, *, subnet_id: int, device_id: int, channel: int, state: str, ts: float | None = None) -> None:
        raw = self.read_raw()
        states = dict(raw.get("states", {}) or {})
        key = f"pir:{subnet_id}.{device_id}.{channel}"
        states[key] = {
            "state": str(state).upper(),
            "ts": float(ts) if ts is not None else None,
        }
        raw["states"] = states
        self.write_raw(raw)

    def set_ultrasonic_state(self, *, subnet_id: int, device_id: int, channel: int, state: str, ts: float | None = None) -> None:
        raw = self.read_raw()
        states = dict(raw.get("states", {}) or {})
        key = f"ultrasonic:{subnet_id}.{device_id}.{channel}"
        states[key] = {
            "state": str(state).upper(),
            "ts": float(ts) if ts is not None else None,
        }
        raw["states"] = states
        self.write_raw(raw)

    def set_dry_contact_state(
        self,
        *,
        subnet_id: int,
        device_id: int,
        channel: int,
        state: str,
        ts: float | None = None,
        payload_x: int | None = None,
    ) -> None:
        raw = self.read_raw()
        states = dict(raw.get("states", {}) or {})
        key = f"dry_contact:{subnet_id}.{device_id}.{channel}"
        states[key] = {
            "state": str(state).upper(),
            "ts": float(ts) if ts is not None else None,
            "x": int(payload_x) if payload_x is not None else None,
        }
        raw["states"] = states
        self.write_raw(raw)

    def get_temp_states(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for k, v in self.get_states().items():
            if not str(k).startswith("temp:"):
                continue
            addr = str(k).split(":", 1)[1]
            out[addr] = v
        return out

    def get_humidity_states(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for k, v in self.get_states().items():
            if not str(k).startswith("humidity:"):
                continue
            addr = str(k).split(":", 1)[1]
            out[addr] = v
        return out

    def get_illuminance_states(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for k, v in self.get_states().items():
            if not str(k).startswith("illuminance:"):
                continue
            addr = str(k).split(":", 1)[1]
            out[addr] = v
        return out

    def get_air_quality_states(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for k, v in self.get_states().items():
            if not str(k).startswith("air_quality:"):
                continue
            addr = str(k).split(":", 1)[1]
            out[addr] = v
        return out

    def get_gas_percent_states(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for k, v in self.get_states().items():
            if not str(k).startswith("gas_percent:"):
                continue
            addr = str(k).split(":", 1)[1]
            out[addr] = v
        return out

    def get_pir_states(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for k, v in self.get_states().items():
            if not str(k).startswith("pir:"):
                continue
            addr = str(k).split(":", 1)[1]
            out[addr] = v
        return out

    def get_ultrasonic_states(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for k, v in self.get_states().items():
            if not str(k).startswith("ultrasonic:"):
                continue
            addr = str(k).split(":", 1)[1]
            out[addr] = v
        return out

    def get_dry_contact_states(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for k, v in self.get_states().items():
            if not str(k).startswith("dry_contact:"):
                continue
            addr = str(k).split(":", 1)[1]
            out[addr] = v
        return out

    def delete_cover_group_state(self, *, group_id: str) -> None:
        gid = str(group_id or "").strip()
        if not gid:
            return
        raw = self.read_raw()
        states = dict(raw.get("states", {}) or {})
        states.pop(f"cover_group:{gid}", None)
        raw["states"] = states
        self.write_raw(raw)

    def _state_key_for(self, type_: str, subnet_id: int, device_id: int, channel: int) -> str:
        t = str(type_ or "").strip().lower()
        if t == "cover":
            prefix = "cover"
        elif t == "temp":
            prefix = "temp"
        elif t == "humidity":
            prefix = "humidity"
        elif t == "illuminance":
            prefix = "illuminance"
        elif t == "air":
            prefix = "air_quality"
        elif t == "pir":
            prefix = "pir"
        elif t == "ultrasonic":
            prefix = "ultrasonic"
        elif t == "dry_contact":
            prefix = "dry_contact"
        else:
            prefix = "light"
        return f"{prefix}:{subnet_id}.{device_id}.{channel}"

    def move_device(
        self,
        *,
        type_: str,
        from_subnet_id: int,
        from_device_id: int,
        from_channel: int,
        to_subnet_id: int,
        to_device_id: int,
        to_channel: int,
        updates: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """
        Move a device to a new address and migrate its stored state key.
        Returns the updated device or None if not found.
        """
        raw = self.read_raw()
        devices = list(raw.get("devices", []))

        t = str(type_ or "").strip().lower()
        from_key = (t, int(from_subnet_id), int(from_device_id), int(from_channel))
        to_key = (t, int(to_subnet_id), int(to_device_id), int(to_channel))

        found_idx: int | None = None
        for idx, d in enumerate(devices):
            try:
                k = (
                    str(d.get("type") or "light").strip().lower(),
                    int(d.get("subnet_id")),
                    int(d.get("device_id")),
                    int(d.get("channel")),
                )
            except Exception:
                continue
            if k == from_key:
                found_idx = idx
                continue
            if k == to_key:
                raise ValueError("duplicate address")

        if found_idx is None:
            return None

        d0 = dict(devices[found_idx])
        d0["subnet_id"] = int(to_subnet_id)
        d0["device_id"] = int(to_device_id)
        d0["channel"] = int(to_channel)
        for k, v in (updates or {}).items():
            if v is None:
                d0.pop(k, None)
            else:
                d0[k] = v

        devices[found_idx] = d0
        raw["devices"] = devices

        states = dict(raw.get("states", {}) or {})
        old_state_key = self._state_key_for(t, from_subnet_id, from_device_id, from_channel)
        new_state_key = self._state_key_for(t, to_subnet_id, to_device_id, to_channel)
        if old_state_key in states and new_state_key not in states:
            states[new_state_key] = states.pop(old_state_key)
        else:
            # Ensure old key is removed to avoid confusion
            states.pop(old_state_key, None)
        raw["states"] = states

        self.write_raw(raw)
        return d0
    def remove_device(self, *, subnet_id: int, device_id: int, channel: int) -> bool:
        raw = self.read_raw()
        devices = list(raw.get("devices", []))
        before = len(devices)
        devices = [
            d
            for d in devices
            if not (
                int(d.get("subnet_id")) == int(subnet_id)
                and int(d.get("device_id")) == int(device_id)
                and int(d.get("channel")) == int(channel)
            )
        ]
        raw["devices"] = devices

        states = dict(raw.get("states", {}) or {})
        states.pop(f"light:{subnet_id}.{device_id}.{channel}", None)
        states.pop(f"cover:{subnet_id}.{device_id}.{channel}", None)
        states.pop(f"temp:{subnet_id}.{device_id}.{channel}", None)
        states.pop(f"humidity:{subnet_id}.{device_id}.{channel}", None)
        states.pop(f"illuminance:{subnet_id}.{device_id}.{channel}", None)
        states.pop(f"dry_contact:{subnet_id}.{device_id}.{channel}", None)
        raw["states"] = states

        self.write_raw(raw)
        return len(devices) != before

    def remove_device_typed(self, *, type_: str, subnet_id: int, device_id: int, channel: int) -> bool:
        t = str(type_ or "").strip().lower()
        raw = self.read_raw()
        devices = list(raw.get("devices", []))
        before = len(devices)
        devices = [
            d
            for d in devices
            if not (
                str(d.get("type") or "light").strip().lower() == t
                and int(d.get("subnet_id")) == int(subnet_id)
                and int(d.get("device_id")) == int(device_id)
                and int(d.get("channel")) == int(channel)
            )
        ]
        raw["devices"] = devices

        states = dict(raw.get("states", {}) or {})
        states.pop(self._state_key_for(t, subnet_id, device_id, channel), None)
        raw["states"] = states

        self.write_raw(raw)
        return len(devices) != before
