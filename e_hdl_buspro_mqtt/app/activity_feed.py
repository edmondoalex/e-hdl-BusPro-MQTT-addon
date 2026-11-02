"""Bounded, durable transport buffer for the e-Face global journal (not an audit authority)."""
import json
import sqlite3
import threading
import time
import uuid
from pathlib import Path


class ActivityFeed:
    def __init__(self, path):
        self.path = Path(path)
        self.lock = threading.RLock()
        self.errors = 0
        self.ready = False

    def connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.path, timeout=3)
        db.row_factory = sqlite3.Row
        if not self.ready:
            db.execute("PRAGMA auto_vacuum=FULL")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS events(seq INTEGER PRIMARY KEY AUTOINCREMENT,event_id TEXT UNIQUE,at REAL,data TEXT);
                CREATE INDEX IF NOT EXISTS events_at ON events(at);
                CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY,value TEXT);
                CREATE TABLE IF NOT EXISTS states(device_id TEXT PRIMARY KEY,state TEXT);
            """)
            db.execute("INSERT OR IGNORE INTO meta VALUES('epoch',?)", (uuid.uuid4().hex,))
            db.commit()
            self.ready = True
        return db

    @staticmethod
    def device(item):
        return {"device_id": item.get("id") or f"{item.get('source')}:{item.get('device_id')}",
                "name": item.get("name"), "room": item.get("room_name"), "floor": item.get("floor_name"), "bus": item.get("source")}

    def append(self, event):
        safe = {key: str(event.get(key) or "")[:240] for key in (
            "category", "device_id", "name", "room", "floor", "bus", "action", "origin", "status", "before", "after")}
        safe.update(event_id=str(event.get("event_id") or uuid.uuid4()), at=time.time())
        try:
            with self.lock:
                db = self.connect()
                try:
                    with db:
                        db.execute("INSERT OR IGNORE INTO events(event_id,at,data) VALUES(?,?,?)", (safe["event_id"], safe["at"], json.dumps(safe)))
                        db.execute("DELETE FROM events WHERE at < ? OR seq <= (SELECT coalesce(max(seq),0)-10000 FROM events)", (time.time()-86400,))
                finally:
                    db.close()
        except (OSError, sqlite3.Error):
            self.errors += 1
        return safe["event_id"]

    def stats(self):
        with self.lock:
            db = self.connect()
            try:
                count = db.execute("SELECT count(*) FROM events").fetchone()[0]
            finally:
                db.close()
            return {"bytes": self.path.stat().st_size, "count": count, "max_events": 10000, "hours": 24, "errors": self.errors}

    def observe(self, devices):
        # Digital changes only. No analog temperatures, watts or periodic unchanged samples.
        samples = {}
        for item in devices:
            if item.get("device_class") not in {"light", "dimmer", "switch", "lock", "smart_lock", "opener", "cover", "shutter", "gate", "garage_door", "presence", "dry_contact"}:
                continue
            raw = item.get("state")
            state = raw
            for _ in range(3):
                if not isinstance(state, dict):
                    break
                state = state.get("STA", state.get("state", state.get("value")))
            if state is None or isinstance(state, (dict, list)) or not item.get("available") or item.get("stale"):
                continue
            device = self.device(item)
            state = str(state).casefold()[:80]
            samples[device["device_id"]] = (device, state)
        try:
            with self.lock:
                db = self.connect()
                try:
                    with db:
                        previous = dict(db.execute("SELECT device_id,state FROM states"))
                        for identifier, (device, state) in samples.items():
                            if previous.get(identifier) == state:
                                continue
                            if identifier in previous:
                                event = {**device, "category": "device", "action": "state_changed", "origin": "bus",
                                         "status": "observed", "before": previous[identifier], "after": state,
                                         "event_id": str(uuid.uuid4()), "at": time.time()}
                                db.execute("INSERT INTO events(event_id,at,data) VALUES(?,?,?)", (event["event_id"], event["at"], json.dumps(event)))
                            db.execute("INSERT OR REPLACE INTO states VALUES(?,?)", (identifier, state))
                        db.execute("DELETE FROM events WHERE at < ? OR seq <= (SELECT coalesce(max(seq),0)-10000 FROM events)", (time.time()-86400,))
                finally:
                    db.close()
        except (OSError, sqlite3.Error):
            self.errors += 1

    def read(self, after=0, limit=200, allowed_ids=()):
        with self.lock:
            db = self.connect()
            try:
                bounds = db.execute("SELECT min(seq),coalesce(max(seq),0) FROM events").fetchone()
                epoch = db.execute("SELECT value FROM meta WHERE key='epoch'").fetchone()[0]
                rows = db.execute("SELECT seq,data FROM events WHERE seq>? ORDER BY seq LIMIT ?", (max(0, after), min(500, max(1, limit)))).fetchall()
                allowed = set(allowed_ids)
                items = [dict(json.loads(row["data"]), seq=row["seq"]) for row in rows if json.loads(row["data"]).get("device_id") in allowed]
                return {"schema_version": "1.0", "epoch": epoch, "items": items,
                        "cursor": rows[-1]["seq"] if rows else max(0, after), "latest": bounds[1],
                        "gap": bool(after and bounds[0] and after < bounds[0]-1), "errors": self.errors}
            finally:
                db.close()
