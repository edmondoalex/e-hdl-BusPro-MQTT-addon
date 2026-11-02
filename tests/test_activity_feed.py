import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("activity_feed", Path(__file__).parents[1] / "e_hdl_buspro_mqtt/app/activity_feed.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
ActivityFeed = module.ActivityFeed


def device(state):
    return {"id": "hdl:1", "name": "Luce", "source": "hdl", "device_class": "light", "available": True, "state": {"state": state}}


def test_baseline_state_change_restart_and_no_repeated_samples(tmp_path):
    path = tmp_path / "feed.db"
    feed = ActivityFeed(path)
    feed.observe([device("off")])
    assert feed.read(allowed_ids=["hdl:1"])["items"] == []
    feed.observe([device("on")])
    feed.observe([device("on")])
    feed = ActivityFeed(path)
    feed.observe([device("on")])
    rows = feed.read(allowed_ids=["hdl:1"])["items"]
    assert len(rows) == 1
    assert rows[0]["before"] == "off" and rows[0]["after"] == "on"


def test_scoped_feed_advances_cursor_for_hidden_devices_and_excludes_secrets(tmp_path):
    feed = ActivityFeed(tmp_path / "feed.db")
    feed.append({"category": "command", "device_id": "hidden", "pin": "1234", "value": "1234"})
    feed.append({"category": "command", "device_id": "visible", "actor": "untrusted"})
    page = feed.read(0, 1, ["visible"])
    assert page["items"] == [] and page["cursor"] == 1
    row = feed.read(page["cursor"], allowed_ids=["visible"])["items"][0]
    assert "actor" not in row and "pin" not in row and "value" not in row


def test_epoch_persistent_and_old_rows_pruned(tmp_path):
    path = tmp_path / "feed.db"
    feed = ActivityFeed(path)
    epoch = feed.read()["epoch"]
    feed.append({"device_id": "hdl:1"})
    db = feed.connect()
    db.execute("UPDATE events SET at=1")
    db.commit()
    db.close()
    feed.observe([])
    assert ActivityFeed(path).read()["epoch"] == epoch
    assert feed.read(allowed_ids=["hdl:1"])["items"] == []


def test_native_state_formats_and_no_analog_samples(tmp_path):
    feed = ActivityFeed(tmp_path / "feed.db")
    feed.observe([{**device("off"), "state": {"STA": "OFF", "LEV": 0}}])
    feed.observe([{**device("on"), "state": {"STA": "ON", "LEV": 40}}])
    feed.observe([{**device("on"), "state": {"STA": "ON", "LEV": 60}}])
    feed.observe([{**device("off"), "state": {"value": {"state": "OFF"}}}])
    assert len(feed.read(allowed_ids=["hdl:1"])["items"]) == 2
