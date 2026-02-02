from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from typing import Any, Callable

import paho.mqtt.client as mqtt


@dataclass(frozen=True)
class MqttStatus:
    connected: bool
    last_error: str | None


class MqttClient:
    def __init__(self, *, host: str, port: int, username: str, password: str, client_id: str):
        self._host = host
        self._port = port
        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id)
        if username:
            self._client.username_pw_set(username, password)

        self._lock = threading.Lock()
        self._connected = False
        self._last_error: str | None = None
        self._subscriptions: dict[str, int] = {}

        self._on_message_user: Callable[[str, str], None] | None = None
        self._on_connect_user: Callable[[], None] | None = None

        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message

    def _on_connect(self, client, userdata, flags, reason_code, properties=None):
        subs: list[tuple[str, int]]
        on_connect_user: Callable[[], None] | None
        with self._lock:
            self._connected = True
            self._last_error = None
            subs = list(self._subscriptions.items())
            on_connect_user = self._on_connect_user
        for topic, qos in subs:
            try:
                client.subscribe(topic, qos=qos)
            except Exception:
                # Keep MQTT thread alive; status will surface disconnects.
                pass
        if on_connect_user is not None:
            try:
                on_connect_user()
            except Exception:
                # Keep MQTT thread alive
                pass

    def _on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties=None):
        with self._lock:
            self._connected = False
            if getattr(reason_code, "value", reason_code) != 0:
                self._last_error = f"disconnect reason_code={reason_code}"

    def _on_message(self, client, userdata, msg):
        handler = self._on_message_user
        if handler is None:
            return
        try:
            payload = msg.payload.decode("utf-8", errors="replace")
        except Exception:
            payload = ""
        try:
            handler(str(msg.topic), payload)
        except Exception:
            # Keep MQTT thread alive
            pass

    def set_message_handler(self, handler: Callable[[str, str], None] | None) -> None:
        self._on_message_user = handler

    def set_connect_handler(self, handler: Callable[[], None] | None) -> None:
        self._on_connect_user = handler

    def connect(self) -> None:
        try:
            # Auto-reconnect and re-subscribe is handled via on_connect.
            self._client.reconnect_delay_set(min_delay=1, max_delay=30)
            self._client.connect_async(self._host, self._port, keepalive=30)
            self._client.loop_start()
        except Exception as e:
            with self._lock:
                self._connected = False
                self._last_error = str(e)

    def disconnect(self) -> None:
        try:
            self._client.loop_stop()
            self._client.disconnect()
        finally:
            with self._lock:
                self._connected = False

    def status(self) -> MqttStatus:
        with self._lock:
            return MqttStatus(connected=self._connected, last_error=self._last_error)

    def publish(self, topic: str, payload: Any, *, retain: bool = False, qos: int = 0) -> None:
        if isinstance(payload, (dict, list)):
            data = json.dumps(payload, ensure_ascii=False)
        else:
            data = str(payload)
        self._client.publish(topic, data, qos=qos, retain=retain)

    def subscribe(self, topic: str, *, qos: int = 0) -> None:
        with self._lock:
            self._subscriptions[topic] = qos
            connected = self._connected
        if connected:
            self._client.subscribe(topic, qos=qos)
