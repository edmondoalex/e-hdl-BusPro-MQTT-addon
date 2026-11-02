from email.message import Message
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from e_hdl_buspro_mqtt.app import event_register_proxy as proxy


def client(root_path=""):
    app = FastAPI(root_path=root_path)
    app.include_router(proxy.router)
    return TestClient(app)


def result(status=200, content_type="application/json", payload=b'{}', **headers):
    head = Message()
    head["Content-Type"] = content_type
    for key, value in headers.items():
        head[key] = value
    return status, head, payload


@pytest.mark.parametrize("path,method", [
    ("api/control/light/1", "POST"), ("api/user/devices/x/command", "POST"),
    ("api/auth/users", "GET"), ("api/installer/login", "POST"),
    ("api/user/events", "POST"), ("health", "GET"), ("http://example.com", "GET"),
])
def test_not_a_general_proxy(path, method):
    with patch.object(proxy, "fetch") as fetch:
        assert client().request(method, "/event-register/" + path).status_code == 404
        fetch.assert_not_called()


def test_read_forwards_only_real_eface_cookie_not_hub_authority():
    with patch.object(proxy, "fetch", return_value=result(401)) as fetch:
        response = client().get("/event-register/api/user/events?category=command", headers={
            "Authorization": "Bearer hub-only", "X-Ingress-Path": "/admin", "X-User": "admin",
            "Cookie": "econtrol_register_session=signed-eface; other=private"})
        assert response.status_code == 401
        assert fetch.call_args.args[3] == {"Accept": "*/*", "Accept-Encoding": "identity", "Cookie": "eface_user=signed-eface"}
        assert fetch.call_args.args[2] == "category=command"
        assert "Set-Cookie" not in response.headers


def test_login_cookie_is_scoped_and_ingress_redirect_is_preserved():
    c = client("/ingress/test")
    with patch.object(proxy, "fetch", return_value=result(303, Location="login?next=events")):
        response = c.get("/event-register/events", follow_redirects=False)
        assert response.headers["location"] == "/ingress/test/event-register/login?next=events"
    with patch.object(proxy, "fetch", return_value=result(**{"Set-Cookie": "eface_user=signed; Path=/; HttpOnly; Max-Age=3600"})):
        response = c.post("/event-register/api/auth/login", json={"username": "demo", "password": "example"})
        cookie = response.headers["set-cookie"]
        assert "econtrol_register_session=signed" in cookie
        assert "Path=/ingress/test/event-register/" in cookie
        assert "HttpOnly" in cookie and "SameSite=strict" in cookie
        assert "password" not in response.text


def test_cross_site_writes_and_oversize_are_blocked():
    with patch.object(proxy, "fetch") as fetch:
        c = client()
        assert c.post("/event-register/api/auth/login", json={}, headers={"Origin": "https://foreign.test"}).status_code == 403
        assert c.post("/event-register/api/auth/login", data="name=x").status_code == 415
        assert c.post("/event-register/api/auth/login", content=b"x" * 8193, headers={"Content-Type": "application/json"}).status_code == 413
        fetch.assert_not_called()


def test_retention_preserves_eface_permission_and_external_redirect_blocked():
    with patch.object(proxy, "fetch", return_value=result(403)):
        assert client().put("/event-register/api/admin/events/retention", json={"days": 30}).status_code == 403
    with patch.object(proxy, "fetch", return_value=result(303, Location="https://foreign.test/login")):
        assert client().get("/event-register/events").status_code == 502


def test_offline_no_error_details_and_back_link_to_hub():
    with patch.object(proxy, "fetch", side_effect=OSError("private details")):
        response = client().get("/event-register/events")
        assert response.status_code == 503
        assert "private details" not in response.text
        assert "eFace" in response.text
    with patch.object(proxy, "fetch", return_value=result(content_type="text/html", payload=b'<a href="tools">Back</a>')):
        response = client("/ingress/test").get("/event-register/events")
        assert 'href="/ingress/test/index.html#event_register"' in response.text
        assert 'target="_top"' in response.text


def test_hub_user_port_does_not_expose_register_proxy(tmp_path, monkeypatch):
    from e_hdl_buspro_mqtt.app.main import create_app
    monkeypatch.setenv("BUSPRO_STATE", str(tmp_path / "state.json"))
    monkeypatch.setenv("ECONTROL_ORGANIZATION", str(tmp_path / "organization.json"))
    with patch.object(proxy, "fetch") as fetch:
        c = TestClient(create_app(), base_url="http://testserver:8124")
        assert c.get("/event-register/api/user/events").status_code == 404
        fetch.assert_not_called()
