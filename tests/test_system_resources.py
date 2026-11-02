from unittest.mock import patch

from e_hdl_buspro_mqtt.app.system_resources import Resources
from e_hdl_buspro_mqtt.app.activity_feed import ActivityFeed


def test_live_metrics_do_not_require_supervisor_or_write_history(tmp_path):
    resources = Resources(tmp_path)
    first = resources.snapshot()
    assert first["cpu"]["process_percent"] is None
    assert first["cpu"]["logical_cores"] > 0
    assert first["data_filesystem"]["total"] > 0
    assert list(tmp_path.iterdir()) == []
    now = resources.previous[0]
    with patch("e_hdl_buspro_mqtt.app.system_resources.time.monotonic", return_value=now + 2), patch("e_hdl_buspro_mqtt.app.system_resources.time.process_time", return_value=resources.previous[1] + 1):
        assert resources.snapshot()["cpu"]["process_percent"] == 50


def test_buffer_statistics_contain_no_event_data(tmp_path):
    feed = ActivityFeed(tmp_path / "feed.db")
    feed.append({"category": "command", "name": "private-device", "device_id": "hdl:1"})
    stats = feed.stats()
    assert stats["count"] == 1 and stats["bytes"] > 0
    assert stats["max_events"] == 10000 and stats["hours"] == 24
    assert "private-device" not in str(stats)


def test_linux_cpu_keys_trim_tabs_and_whitespace():
    with patch("e_hdl_buspro_mqtt.app.system_resources.Path.read_text", return_value="model name\t: CPU example\nprocessor\t: 0\n"):
        assert Resources.fields("/proc/cpuinfo")["model name"] == "CPU example"
