from __future__ import annotations

import asyncio
import logging
import ipaddress
from dataclasses import dataclass
from typing import Any, Callable

from .pybuspro.buspro import Buspro
from .pybuspro.devices.cover import Cover as BPCover
from .pybuspro.devices.control import _CoverControl
from .pybuspro.devices.light import Light as BPLight
from .pybuspro.helpers.enums import CoverStatus

_LOGGER = logging.getLogger("buspro_gateway")


@dataclass(frozen=True)
class LightKey:
    subnet_id: int
    device_id: int
    channel: int

    @property
    def addr(self) -> str:
        return f"{self.subnet_id}.{self.device_id}.{self.channel}"


@dataclass
class LightState:
    is_on: bool
    brightness: int | None  # 0-255


@dataclass(frozen=True)
class CoverKey:
    subnet_id: int
    device_id: int
    channel: int

    @property
    def addr(self) -> str:
        return f"{self.subnet_id}.{self.device_id}.{self.channel}"


@dataclass
class CoverState:
    state: str  # OPEN/CLOSED/OPENING/CLOSING/STOP
    position: int | None  # 0-100


class BusproGateway:
    def __init__(
        self,
        *,
        host: str,
        port: int,
        loop: asyncio.AbstractEventLoop,
        light_cmd_interval_s: float = 0.12,
        udp_send_interval_s: float = 0.0,
    ):
        self._host = host
        self._port = port
        self._loop = loop

        send_addr = (host, port)
        recv_addr = ("", port)
        self._buspro = Buspro((send_addr, recv_addr), loop_=loop)
        # Optional global pacing for all outgoing UDP telegrams (covers, lights, reads, etc.).
        try:
            setattr(self._buspro, "_min_send_interval_s", float(max(0.0, udp_send_interval_s)))
        except Exception:
            pass
        self._buspro.register_telegram_received_all_messages_cb(self._on_any_telegram)
        self._telegram_listeners: list[Callable[[Any], None]] = []

        self._started = False
        self._last_error: str | None = None
        self._last_rx: tuple[str, int] | None = None
        self._default_gateway_ip: str | None = self._read_default_gateway()

        self._devices: dict[tuple[int, int, int], BPLight] = {}
        self._states: dict[tuple[int, int, int], LightState] = {}
        self._state_listeners: list[Callable[[LightKey, LightState], None]] = []

        self._covers: dict[tuple[int, int, int], BPCover] = {}
        self._cover_states: dict[tuple[int, int, int], CoverState] = {}
        self._cover_listeners: list[Callable[[CoverKey, CoverState], None]] = []

        # Light command scheduler: coalesce + pace UDP telegrams to avoid flooding (e.g. dimmer slider).
        self._light_cmd_lock = asyncio.Lock()
        self._light_cmd_event = asyncio.Event()
        self._light_cmd_jobs: dict[tuple[int, int, int], dict[str, Any]] = {}
        self._light_cmd_keys: list[tuple[int, int, int]] = []
        self._light_cmd_inflight: set[tuple[int, int, int]] = set()
        self._light_cmd_worker: asyncio.Task | None = None
        self._light_cmd_interval_s: float = float(max(0.0, light_cmd_interval_s))

        # Cover command scheduler: pace UDP telegrams to avoid flooding when controlling many covers together.
        self._cover_cmd_lock = asyncio.Lock()
        self._cover_cmd_event = asyncio.Event()
        self._cover_cmd_jobs: dict[tuple[int, int, int], dict[str, Any]] = {}
        self._cover_cmd_keys: list[tuple[int, int, int]] = []
        self._cover_cmd_inflight: set[tuple[int, int, int]] = set()
        self._cover_cmd_worker: asyncio.Task | None = None
        self._cover_cmd_interval_s: float = 0.18

    @staticmethod
    def _read_default_gateway() -> str | None:
        # Best-effort: inside containers, NATed UDP sources often appear as the default gateway IP.
        try:
            with open("/proc/net/route", "r", encoding="utf-8") as f:
                for line in f.readlines()[1:]:
                    parts = line.strip().split()
                    if len(parts) < 3:
                        continue
                    dest_hex = parts[1]
                    gw_hex = parts[2]
                    if dest_hex != "00000000":
                        continue
                    gw_int = int(gw_hex, 16)
                    ip = ".".join(str((gw_int >> (8 * i)) & 0xFF) for i in range(4))
                    return ip
        except Exception:
            return None
        return None

    @property
    def host(self) -> str:
        return self._host

    @property
    def port(self) -> int:
        return self._port

    @property
    def started(self) -> bool:
        return self._started

    @property
    def last_error(self) -> str | None:
        return self._last_error

    @property
    def last_rx(self) -> tuple[str, int] | None:
        return self._last_rx

    def send_target(self) -> tuple[str, int]:
        try:
            ni = getattr(self._buspro, "network_interface", None)
            uc = getattr(ni, "udp_client", None)
            send = getattr(uc, "_gateway_address_send", None)
            if isinstance(send, tuple) and len(send) == 2:
                return send[0], int(send[1])
        except Exception:
            pass
        return self._host, int(self._port)

    def transport_ready(self) -> bool:
        try:
            ni = getattr(self._buspro, "network_interface", None)
            uc = getattr(ni, "udp_client", None)
            tr = getattr(uc, "transport", None)
            return tr is not None
        except Exception:
            return False

    def _on_any_telegram(self, telegram: Any) -> None:
        try:
            addr = getattr(telegram, "udp_address", None)
            if not addr:
                return
            host, port = addr[0], int(addr[1])
            self._last_rx = (str(host), port)
            self._auto_set_send_target_from_rx()
        except Exception:
            pass

        for cb in list(self._telegram_listeners):
            try:
                cb(telegram)
            except Exception:
                _LOGGER.exception("Telegram listener failed")

    def add_telegram_listener(self, cb: Callable[[Any], None]) -> None:
        self._telegram_listeners.append(cb)

    def _auto_set_send_target_from_rx(self) -> None:
        # If we are receiving from a gateway address, it's usually the correct TX target too.
        if not self._last_rx:
            return
        host, _rx_port = self._last_rx
        # In bridged Docker networks, the source IP may be NATed to the container default gateway
        # (e.g. 172.x). In that case, don't override the configured gateway host.
        if self._default_gateway_ip and host == self._default_gateway_ip:
            return
        try:
            # If RX host is not a valid IP, ignore it.
            ipaddress.ip_address(host)
        except Exception:
            return
        try:
            ni = getattr(self._buspro, "network_interface", None)
            uc = getattr(ni, "udp_client", None)
            if ni is None or uc is None:
                return
            # Keep RX bind on configured port. For TX, trust the RX host but keep the configured port
            # (some gateways send from ephemeral source ports).
            ni.gateway_address_send_receive = ((host, int(self._port)), ("", int(self._port)))
            setattr(uc, "_gateway_address_send", (host, int(self._port)))
        except Exception:
            pass

    def add_state_listener(self, cb: Callable[[LightKey, LightState], None]) -> None:
        self._state_listeners.append(cb)

    def _emit(self, key: LightKey, st: LightState) -> None:
        for cb in list(self._state_listeners):
            try:
                cb(key, st)
            except Exception:
                _LOGGER.exception("State listener failed")

    def add_cover_listener(self, cb: Callable[[CoverKey, CoverState], None]) -> None:
        self._cover_listeners.append(cb)

    def _emit_cover(self, key: CoverKey, st: CoverState) -> None:
        for cb in list(self._cover_listeners):
            try:
                cb(key, st)
            except Exception:
                _LOGGER.exception("Cover listener failed")

    async def start(self) -> None:
        if self._started:
            return
        try:
            await self._buspro.start(state_updater=False)
            self._started = True
            if self._light_cmd_worker is None or self._light_cmd_worker.done():
                self._light_cmd_worker = self._loop.create_task(self._light_command_worker())
            if self._cover_cmd_worker is None or self._cover_cmd_worker.done():
                self._cover_cmd_worker = self._loop.create_task(self._cover_command_worker())
            if not self.transport_ready():
                self._last_error = "UDP transport not ready (bind failed?)"
                _LOGGER.warning(self._last_error)
            _LOGGER.info("BusPro started %s:%s", self._host, self._port)
        except Exception as e:
            self._last_error = str(e)
            _LOGGER.exception("BusPro start failed")
            raise

    async def stop(self) -> None:
        if not self._started:
            return
        try:
            if self._light_cmd_worker and not self._light_cmd_worker.done():
                self._light_cmd_worker.cancel()
            self._light_cmd_worker = None
            self._light_cmd_jobs.clear()
            self._light_cmd_keys.clear()
            self._light_cmd_inflight.clear()
            self._light_cmd_event.clear()
            if self._cover_cmd_worker and not self._cover_cmd_worker.done():
                self._cover_cmd_worker.cancel()
            self._cover_cmd_worker = None
            self._cover_cmd_jobs.clear()
            self._cover_cmd_keys.clear()
            self._cover_cmd_inflight.clear()
            self._cover_cmd_event.clear()
            await self._buspro.stop()
        finally:
            self._started = False
            _LOGGER.info("BusPro stopped")

    async def _light_command_worker(self) -> None:
        try:
            while True:
                await self._light_cmd_event.wait()
                while True:
                    async with self._light_cmd_lock:
                        if not self._light_cmd_jobs:
                            break
                        if not self._light_cmd_keys:
                            self._light_cmd_keys = list(self._light_cmd_jobs.keys())
                        key = self._light_cmd_keys.pop(0)
                        job = self._light_cmd_jobs.get(key)
                        if job is None:
                            continue
                        if key in self._light_cmd_inflight:
                            self._light_cmd_keys.append(key)
                            continue

                        self._light_cmd_inflight.add(key)
                        self._light_cmd_jobs.pop(key, None)
                    try:
                        fut: asyncio.Future = job["future"]
                        coro_factory = job["coro_factory"]
                        await coro_factory()
                        if not fut.done():
                            fut.set_result(True)
                    except Exception as e:
                        fut = job.get("future")
                        if fut is not None and not fut.done():
                            fut.set_exception(e)
                    finally:
                        async with self._light_cmd_lock:
                            self._light_cmd_inflight.discard(key)

                    if self._light_cmd_interval_s > 0:
                        await asyncio.sleep(self._light_cmd_interval_s)

                self._light_cmd_event.clear()
        except asyncio.CancelledError:
            return

    async def _enqueue_light_job(
        self,
        key: tuple[int, int, int],
        *,
        kind: str,
        coro_factory: Callable[[], Any],
        priority: int = 0,
    ) -> None:
        async with self._light_cmd_lock:
            prev = self._light_cmd_jobs.get(key)
            if prev is not None:
                try:
                    pf = prev.get("future")
                    if pf is not None and not pf.done():
                        pf.set_exception(RuntimeError("superseded"))
                except Exception:
                    pass

            fut: asyncio.Future = self._loop.create_future()
            self._light_cmd_jobs[key] = {"kind": kind, "priority": int(priority), "coro_factory": coro_factory, "future": fut}

            try:
                if key in self._light_cmd_keys:
                    self._light_cmd_keys.remove(key)
            except Exception:
                pass

            # Higher priority goes earlier; otherwise append for round-robin fairness.
            if int(priority) > 0:
                self._light_cmd_keys.insert(0, key)
            else:
                self._light_cmd_keys.append(key)

            self._light_cmd_event.set()

        try:
            await fut
        except RuntimeError as e:
            if "superseded" in str(e).lower():
                return
            raise

    async def _cover_command_worker(self) -> None:
        try:
            while True:
                await self._cover_cmd_event.wait()
                # Process until queue drained.
                while True:
                    async with self._cover_cmd_lock:
                        if not self._cover_cmd_jobs:
                            break
                        # Round-robin on keys that have pending jobs.
                        if not self._cover_cmd_keys:
                            self._cover_cmd_keys = list(self._cover_cmd_jobs.keys())
                        key = self._cover_cmd_keys.pop(0)
                        job = self._cover_cmd_jobs.get(key)
                        if job is None:
                            continue
                        if key in self._cover_cmd_inflight:
                            # Still executing: rotate and continue.
                            self._cover_cmd_keys.append(key)
                            continue

                        self._cover_cmd_inflight.add(key)
                        self._cover_cmd_jobs.pop(key, None)
                    try:
                        fut: asyncio.Future = job["future"]
                        coro_factory = job["coro_factory"]
                        await coro_factory()
                        if not fut.done():
                            fut.set_result(True)
                    except Exception as e:
                        fut = job.get("future")
                        if fut is not None and not fut.done():
                            fut.set_exception(e)
                    finally:
                        async with self._cover_cmd_lock:
                            self._cover_cmd_inflight.discard(key)

                    # Small delay between telegrams to avoid UDP flood.
                    await asyncio.sleep(self._cover_cmd_interval_s)

                self._cover_cmd_event.clear()
        except asyncio.CancelledError:
            return

    async def _enqueue_cover_job(self, key: tuple[int, int, int], *, kind: str, coro_factory: Callable[[], Any]) -> None:
        async with self._cover_cmd_lock:
            # Coalesce: keep only latest pending command per cover (especially slider SET_POSITION).
            prev = self._cover_cmd_jobs.get(key)
            if prev is not None:
                try:
                    pf = prev.get("future")
                    if pf is not None and not pf.done():
                        pf.set_exception(RuntimeError("superseded"))
                except Exception:
                    pass

            fut: asyncio.Future = self._loop.create_future()
            self._cover_cmd_jobs[key] = {"kind": kind, "coro_factory": coro_factory, "future": fut}

            # STOP should preempt: move key to front.
            try:
                if key in self._cover_cmd_keys:
                    self._cover_cmd_keys.remove(key)
            except Exception:
                pass
            if str(kind).upper() == "STOP":
                self._cover_cmd_keys.insert(0, key)
            else:
                self._cover_cmd_keys.append(key)

            self._cover_cmd_event.set()
        try:
            await fut
        except RuntimeError as e:
            # Superseded by a newer queued command for the same cover: treat as OK for callers.
            if "superseded" in str(e).lower():
                return
            raise

    def ensure_light(self, *, subnet_id: int, device_id: int, channel: int, name: str) -> BPLight:
        key = (subnet_id, device_id, channel)
        dev = self._devices.get(key)
        if dev is not None:
            return dev

        dev = BPLight(self._buspro, (subnet_id, device_id), channel, name)

        async def _updated(_device: Any) -> None:
            try:
                is_on = bool(dev.is_on)
                br255 = int(max(0, min(100, float(dev.current_brightness))) * 255 / 100)
                st = LightState(is_on=is_on, brightness=br255)
                self._states[key] = st
                self._emit(LightKey(subnet_id, device_id, channel), st)
            except Exception:
                _LOGGER.exception("Failed to map light state for %s", key)

        dev.register_device_updated_cb(_updated)

        self._devices[key] = dev
        return dev

    def ensure_cover(
        self,
        *,
        subnet_id: int,
        device_id: int,
        channel: int,
        name: str,
        opening_time: int = 20,
        opening_time_up: int | None = None,
        opening_time_down: int | None = None,
        start_delay_s: float | None = None,
    ) -> BPCover:
        key = (subnet_id, device_id, channel)
        dev = self._covers.get(key)
        if dev is not None:
            try:
                # Aggiorna i tempi solo se vengono passati esplicitamente.
                # Alcuni metodi chiamano ensure_cover con opening_time=20 come default; non deve sovrascrivere
                # le calibrazioni salvate (opening_time_up/down).
                if opening_time_up is not None:
                    setattr(dev, "_opening_time_up", int(opening_time_up))
                if opening_time_down is not None:
                    setattr(dev, "_opening_time_down", int(opening_time_down))
                if start_delay_s is not None:
                    setattr(dev, "_start_delay_s", float(start_delay_s))
            except Exception:
                pass
            return dev

        base = int(opening_time or 20)
        dev = BPCover(
            self._buspro,
            (subnet_id, device_id),
            channel,
            name=name,
            opening_time=base,
            opening_time_up=int(opening_time_up) if opening_time_up is not None else base,
            opening_time_down=int(opening_time_down) if opening_time_down is not None else base,
        )
        try:
            if start_delay_s is not None:
                setattr(dev, "_start_delay_s", float(start_delay_s))
        except Exception:
            pass

        async def _updated(_device: Any) -> None:
            try:
                pos = dev.current_cover_position
                pos_i = int(pos) if pos is not None else None
                state = "STOP"
                if getattr(dev, "is_opening", False):
                    state = "OPENING"
                elif getattr(dev, "is_closing", False):
                    state = "CLOSING"
                elif pos_i == 0:
                    state = "CLOSED"
                elif pos_i == 100:
                    state = "OPEN"
                st = CoverState(state=state, position=pos_i)
                self._cover_states[key] = st
                self._emit_cover(CoverKey(subnet_id, device_id, channel), st)
            except Exception:
                _LOGGER.exception("Failed to map cover state for %s", key)

        dev.register_device_updated_cb(_updated)
        self._covers[key] = dev
        return dev

    async def read_light_status(self, *, subnet_id: int, device_id: int, channel: int) -> None:
        dev = self.ensure_light(subnet_id=subnet_id, device_id=device_id, channel=channel, name="")
        try:
            self._auto_set_send_target_from_rx()
            await dev.read_status()
        except Exception as e:
            self._last_error = str(e)
            _LOGGER.warning("read_status failed: %s", e)

    async def read_cover_status(self, *, subnet_id: int, device_id: int, channel: int) -> None:
        dev = self.ensure_cover(subnet_id=subnet_id, device_id=device_id, channel=channel, name="", opening_time=20)
        try:
            self._auto_set_send_target_from_rx()
            await dev.read_status()
        except Exception as e:
            self._last_error = str(e)
            _LOGGER.warning("cover read_status failed: %s", e)

    async def set_light(
        self,
        *,
        subnet_id: int,
        device_id: int,
        channel: int,
        on: bool,
        brightness255: int | None,
    ) -> None:
        key = (subnet_id, device_id, channel)

        async def _do() -> None:
            dev = self.ensure_light(subnet_id=subnet_id, device_id=device_id, channel=channel, name="")
            self._auto_set_send_target_from_rx()
            if on:
                if brightness255 is None:
                    await dev.set_brightness(100, 0)
                else:
                    b = int(max(0, min(255, brightness255)))
                    pct = int(round(b * 100 / 255))
                    if b > 0:
                        pct = max(1, pct)
                    await dev.set_brightness(pct, 0)
            else:
                await dev.set_off(0)

        try:
            prio = 1 if brightness255 is None else 0
            await self._enqueue_light_job(key, kind="SET", coro_factory=_do, priority=prio)
        except Exception as e:
            self._last_error = str(e)
            _LOGGER.exception("set_light failed")
            raise

    async def cover_open(self, *, subnet_id: int, device_id: int, channel: int) -> None:
        key = (subnet_id, device_id, channel)
        async def _do() -> None:
            dev = self.ensure_cover(subnet_id=subnet_id, device_id=device_id, channel=channel, name="", opening_time=20)
            self._auto_set_send_target_from_rx()
            await dev.set_open()
        await self._enqueue_cover_job(key, kind="OPEN", coro_factory=_do)

    async def cover_open_raw(self, *, subnet_id: int, device_id: int, channel: int) -> None:
        # Raw OPEN without auto-stop scheduling (used for calibration)
        key = (subnet_id, device_id, channel)
        async def _do() -> None:
            self.ensure_cover(subnet_id=subnet_id, device_id=device_id, channel=channel, name="", opening_time=20)
            self._auto_set_send_target_from_rx()
            scc = _CoverControl(self._buspro)
            scc.subnet_id, scc.device_id = (subnet_id, device_id)
            scc.channel_number = channel
            scc.channel_status = CoverStatus.OPEN
            await scc.send()
        await self._enqueue_cover_job(key, kind="OPEN_RAW", coro_factory=_do)

    async def cover_close(self, *, subnet_id: int, device_id: int, channel: int) -> None:
        key = (subnet_id, device_id, channel)
        async def _do() -> None:
            dev = self.ensure_cover(subnet_id=subnet_id, device_id=device_id, channel=channel, name="", opening_time=20)
            self._auto_set_send_target_from_rx()
            await dev.set_close()
        await self._enqueue_cover_job(key, kind="CLOSE", coro_factory=_do)

    async def cover_close_raw(self, *, subnet_id: int, device_id: int, channel: int) -> None:
        # Raw CLOSE without auto-stop scheduling (used for calibration)
        key = (subnet_id, device_id, channel)
        async def _do() -> None:
            self.ensure_cover(subnet_id=subnet_id, device_id=device_id, channel=channel, name="", opening_time=20)
            self._auto_set_send_target_from_rx()
            scc = _CoverControl(self._buspro)
            scc.subnet_id, scc.device_id = (subnet_id, device_id)
            scc.channel_number = channel
            scc.channel_status = CoverStatus.CLOSE
            await scc.send()
        await self._enqueue_cover_job(key, kind="CLOSE_RAW", coro_factory=_do)

    async def cover_stop(self, *, subnet_id: int, device_id: int, channel: int) -> None:
        key = (subnet_id, device_id, channel)
        async def _do() -> None:
            dev = self.ensure_cover(subnet_id=subnet_id, device_id=device_id, channel=channel, name="", opening_time=20)
            self._auto_set_send_target_from_rx()
            # Some installations ignore a single STOP telegram (especially if the movement was started externally).
            # Send STOP twice, then request status.
            await dev.set_stop()
            try:
                await asyncio.sleep(0.15)
                scc = _CoverControl(self._buspro)
                scc.subnet_id, scc.device_id = (subnet_id, device_id)
                scc.channel_number = channel
                scc.channel_status = CoverStatus.STOP
                await scc.send()
            except Exception:
                pass
            try:
                await dev.read_status()
            except Exception:
                pass
        await self._enqueue_cover_job(key, kind="STOP", coro_factory=_do)

    async def cover_set_position(self, *, subnet_id: int, device_id: int, channel: int, position: int) -> None:
        key = (subnet_id, device_id, channel)
        pos = int(position)
        async def _do() -> None:
            dev = self.ensure_cover(subnet_id=subnet_id, device_id=device_id, channel=channel, name="", opening_time=20)
            self._auto_set_send_target_from_rx()
            await dev.set_position(pos)
        await self._enqueue_cover_job(key, kind="SET_POSITION", coro_factory=_do)
