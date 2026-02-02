import asyncio
import datetime
import logging

from .control import _CoverControl, _ReadCoverStatus
from .device import Device
from ..helpers.enums import CoverStatus, OperateCode
try:
    from homeassistant.const import STATE_CLOSING, STATE_OPENING
except Exception:
    STATE_CLOSING = "closing"
    STATE_OPENING = "opening"

_LOGGER = logging.getLogger(__name__)

# Global pacing for cover telegrams (especially STOP) to avoid UDP flooding when many covers move together.
# This complements the gateway scheduler: delayed STOPs are sent from inside the Cover class and would
# otherwise fire in parallel for multiple devices.
_SEND_LOCK: asyncio.Lock | None = None
_LAST_SEND_MONO: float = 0.0
_MIN_SEND_INTERVAL_S: float = 0.18

class Cover(Device):
    """BusPro Cover device con interpolazione basata sulla posizione di partenza."""

    # Stati "pending": comando inviato ma movimento non ancora confermato dal bus.
    _PENDING_OPENING = "pending_opening"
    _PENDING_CLOSING = "pending_closing"

    def __init__(
        self,
        buspro,
        device_address: tuple[int, int],
        channel_number: int,
        name: str = "",
        opening_time: int = 20,
        opening_time_up: int | None = None,
        opening_time_down: int | None = None,
        delay_read_current_state_seconds: int = 0,
    ):
        super().__init__(buspro, device_address, name)
        self._channel = channel_number

        # Stato interno
        self._status = CoverStatus.CLOSE
        self._command = None
        self._start_position = 0       # posizione all’inizio del movimento
        self._requested_position = 0   # destinazione
        self._position = 0             # ultima posizione confermata

        # Parametri temporali (secondi per 0↔100%)
        base = int(opening_time or 20)
        self._opening_time_up = int(opening_time_up) if opening_time_up is not None else base
        self._opening_time_down = int(opening_time_down) if opening_time_down is not None else base
        self._state_changetime = opening_time       # durata attuale del movimento
        self._start_time: datetime.datetime | None = None
        self._pending: dict | None = None
        self._pending_fallback_task: asyncio.Task | None = None
        self._pending_start_task: asyncio.Task | None = None
        self._pending_probe_task: asyncio.Task | None = None

        # Delay (seconds) between command ACK and starting the interpolation.
        # Some motors start moving 1-3s after ACK; without this, UI/STOP become out of sync.
        self._start_delay_s: float = 0.0

        # Task di stop schedulato (da poter cancellare)
        self._stop_task: asyncio.Task | None = None
        self._status_poll_task: asyncio.Task | None = None
        self._motion_tick_task: asyncio.Task | None = None
        self._last_stop_seen: datetime.datetime | None = None

        # Callback telegrammi
        self.register_telegram_received_cb(self._telegram_received_cb)

        # Lettura status iniziale (se supportato)
        self._call_read_current_status_of_channels(run_from_init=True)

    def _cancel_status_poll(self) -> None:
        if self._status_poll_task and not self._status_poll_task.done():
            self._status_poll_task.cancel()
        self._status_poll_task = None

    def _cancel_motion_tick(self) -> None:
        if self._motion_tick_task and not self._motion_tick_task.done():
            self._motion_tick_task.cancel()
        self._motion_tick_task = None

    def _cancel_pending_fallback(self) -> None:
        if self._pending_fallback_task and not self._pending_fallback_task.done():
            self._pending_fallback_task.cancel()
        self._pending_fallback_task = None

    def _cancel_pending_start(self) -> None:
        if self._pending_start_task and not self._pending_start_task.done():
            self._pending_start_task.cancel()
        self._pending_start_task = None

    def _cancel_pending_probe(self) -> None:
        if self._pending_probe_task and not self._pending_probe_task.done():
            self._pending_probe_task.cancel()
        self._pending_probe_task = None

    def _set_pending(self, *, direction: str, requested: int, full_time: float, start_pos: int) -> None:
        issued_at = datetime.datetime.now()
        self._pending = {
            "direction": direction,  # "OPEN" | "CLOSE"
            "requested": int(requested),
            "full_time": float(full_time),
            "start_pos": int(start_pos),
            "started_by_timeout": False,
            "issued_at": issued_at,
        }

    def _start_motion_from_pending_delayed(
        self,
        *,
        now: datetime.datetime,
        start_pos: int | None = None,
        respect_start_delay: bool = True,
    ) -> None:
        if not self._pending:
            return

        # Avoid scheduling multiple delayed starts for the same pending command.
        if self._pending_start_task and not self._pending_start_task.done():
            return

        direction = str(self._pending.get("direction") or "")
        requested = int(self._pending.get("requested") or 0)
        full_time = float(self._pending.get("full_time") or 20.0)
        if start_pos is None:
            start_pos = int(self._pending.get("start_pos") or 0)

        issued_at = self._pending.get("issued_at")
        if not isinstance(issued_at, datetime.datetime):
            issued_at = now

        delay_cfg = 0.0
        try:
            delay_cfg = float(getattr(self, "_start_delay_s", 0.0) or 0.0)
        except Exception:
            delay_cfg = 0.0

        try:
            elapsed = (now - issued_at).total_seconds()
        except Exception:
            elapsed = 0.0
        remaining = max(0.0, delay_cfg - float(elapsed)) if respect_start_delay else 0.0

        def _begin(start_now: datetime.datetime) -> None:
            if not self._pending:
                return
            if self._pending.get("issued_at") != issued_at:
                return

            self._start_position = int(start_pos)
            self._requested_position = int(max(0, min(requested, 100)))
            self._start_time = start_now

            if direction == "OPEN":
                self._status = STATE_OPENING
                self._command = CoverStatus.OPEN
            else:
                self._status = STATE_CLOSING
                self._command = CoverStatus.CLOSE

            self._state_changetime = abs(self._requested_position - self._start_position) / 100 * float(full_time or 20.0)
            self._ensure_status_poll()
            self._ensure_motion_tick()

            if self._stop_task and not self._stop_task.done():
                self._stop_task.cancel()
            self._stop_task = asyncio.create_task(self._delayed_stop(float(self._state_changetime)))

            self._pending = None
            self._cancel_pending_fallback()
            self._cancel_pending_start()
            self._cancel_pending_probe()

        if remaining > 0.01:
            async def _delayed_begin() -> None:
                try:
                    await asyncio.sleep(remaining)
                except asyncio.CancelledError:
                    return
                _begin(datetime.datetime.now())

            try:
                self._pending_start_task = asyncio.create_task(_delayed_begin())
            except Exception:
                self._pending_start_task = None
                _begin(datetime.datetime.now())
        else:
            _begin(now)

    def _start_motion_from_pending(self, *, now: datetime.datetime, start_pos: int | None = None) -> None:
        if not self._pending:
            return
        self._start_motion_from_pending_delayed(now=now, start_pos=start_pos)
        return
        direction = str(self._pending.get("direction") or "")
        requested = int(self._pending.get("requested") or 0)
        full_time = float(self._pending.get("full_time") or 20.0)
        if start_pos is None:
            start_pos = int(self._pending.get("start_pos") or 0)

        self._start_position = int(start_pos)
        self._requested_position = int(max(0, min(requested, 100)))
        # Non usare `issued_at` come start_time: su alcuni impianti il motore parte con 1-3s di ritardo.
        # Se contiamo da subito, la UI va fuori sincrono e crede di essere a 0/100 quando non lo e'.
        self._start_time = now

        if direction == "OPEN":
            self._status = STATE_OPENING
            self._command = CoverStatus.OPEN
        else:
            self._status = STATE_CLOSING
            self._command = CoverStatus.CLOSE

        self._state_changetime = abs(self._requested_position - self._start_position) / 100 * float(full_time or 20.0)
        self._ensure_status_poll()
        self._ensure_motion_tick()

        # Per i comandi di posizione (anche OPEN/CLOSE), scheduliamo lo STOP in base al tempo calcolato.
        # Se la conferma del bus arriva in ritardo, sottraiamo il tempo già trascorso dall'invio comando.
        if self._stop_task and not self._stop_task.done():
            self._stop_task.cancel()
        self._stop_task = asyncio.create_task(self._delayed_stop(float(self._state_changetime)))

    def _ensure_status_poll(self) -> None:
        if self._status_poll_task and not self._status_poll_task.done():
            return
        try:
            loop = self._buspro.loop
            self._status_poll_task = loop.create_task(self._status_poll_loop())
        except Exception:
            self._status_poll_task = None

    def _ensure_motion_tick(self) -> None:
        if self._motion_tick_task and not self._motion_tick_task.done():
            return
        try:
            loop = self._buspro.loop
            self._motion_tick_task = loop.create_task(self._motion_tick_loop())
        except Exception:
            self._motion_tick_task = None

    async def _motion_tick_loop(self) -> None:
        # Aggiorna la posizione stimata in realtime anche se il bus non manda eventi continui.
        try:
            while self._status in (STATE_OPENING, STATE_CLOSING):
                self._call_device_updated()
                await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            return

    async def _status_poll_loop(self) -> None:
        # Richiede periodicamente lo status mentre la cover e' in movimento,
        # cosi' uno STOP da parete (HDL) viene intercettato in modo affidabile.
        try:
            deadline = datetime.datetime.now() + datetime.timedelta(seconds=max(int(self._opening_time_up or 20), int(self._opening_time_down or 20)) + 15)
            while self._status in (STATE_OPENING, STATE_CLOSING) and datetime.datetime.now() < deadline:
                # Evita di “intasare” il bus vicino allo stop programmato: su alcuni impianti troppi poll
                # ritardano la ricezione/gestione dei comandi (STOP) e la cover “avanza” oltre la %.
                try:
                    if self._start_time and self._state_changetime and self._state_changetime > 0:
                        elapsed = (datetime.datetime.now() - self._start_time).total_seconds()
                        remaining = float(self._state_changetime) - float(elapsed)
                        if remaining <= 2.8:
                            await asyncio.sleep(0.35)
                            continue
                except Exception:
                    pass
                try:
                    await self.read_status()
                except Exception as e:
                    _LOGGER.debug("cover read_status poll failed: %s", e)
                await asyncio.sleep(2.0)
        except asyncio.CancelledError:
            return

    def _telegram_received_cb(self, telegram):
        """Aggiorna stato se arriva un response di cover."""
        if telegram.operate_code in (
            OperateCode.CurtainSwitchControl,
            OperateCode.CurtainSwitchControlResponse,
            OperateCode.CurtainSwitchStatusResponse,
        ):
            op = telegram.operate_code
            if not telegram.payload:
                self._call_device_updated()
                return

            # payload usually: [channel, status]
            try:
                ch = int(telegram.payload[0])
            except Exception:
                ch = None
            if ch is not None and ch != self._channel:
                return

            status_val = None
            if len(telegram.payload) >= 2:
                try:
                    status_val = int(telegram.payload[1])
                except Exception:
                    status_val = None

            def _freeze_now() -> None:
                if self._stop_task and not self._stop_task.done():
                    self._stop_task.cancel()
                self._cancel_status_poll()
                self._cancel_motion_tick()
                self._cancel_pending_fallback()
                self._cancel_pending_start()
                self._cancel_pending_probe()
                self._pending = None
                now = datetime.datetime.now()
                self._last_stop_seen = now
                if self._start_time and self._state_changetime > 0:
                    elapsed = (now - self._start_time).total_seconds()
                    frac = min(elapsed / self._state_changetime, 1.0)
                    diff = self._requested_position - self._start_position
                    self._position = int(self._start_position + diff * frac)
                self._status = CoverStatus.STOP
                self._command = CoverStatus.STOP

            _LOGGER.debug(
                "cover telegram op=%s ch=%s payload=%s status_val=%s prev_status=%s pos=%s",
                op,
                ch,
                getattr(telegram, "payload", None),
                status_val,
                self._status,
                self.current_cover_position,
            )

            # Nota: su alcuni impianti il CurtainSwitchStatusResponse può riportare l'ultima direzione (1/2)
            # anche quando la cover è già ferma. Per evitare "ripartenze fantasma" dell'interpolazione:
            # - solo i ControlResponse (comandi) avviano un movimento
            # - i StatusResponse servono soprattutto per STOP/aggiornamenti mentre si è già in movimento

            if op in (OperateCode.CurtainSwitchControl, OperateCode.CurtainSwitchControlResponse):
                # 0=STOP, 1=OPEN, 2=CLOSE (CoverStatus enum values)
                if status_val == CoverStatus.OPEN.value:
                    now = datetime.datetime.now()
                    if self._pending and str(self._pending.get("direction")) == "OPEN":
                        # Questo e' solo ACK del comando: il movimento reale puo' partire piu' tardi.
                        # Aspetta un StatusResponse (1/2) oppure il fallback timer prima di far partire l'interpolazione.
                        self._call_device_updated()
                        return
                    else:
                        # Movimento iniziato dall'esterno: interpola verso endstop senza schedulare STOP.
                        if self._status == STATE_OPENING:
                            self._call_device_updated()
                            return
                        self._start_position = self.current_cover_position or self._position
                        self._requested_position = 100
                        self._start_time = now
                        self._status = STATE_OPENING
                        self._command = CoverStatus.OPEN
                        self._state_changetime = abs(self._requested_position - self._start_position) / 100 * float(self._opening_time_up or 20)
                        self._ensure_status_poll()
                        self._ensure_motion_tick()
                elif status_val == CoverStatus.CLOSE.value:
                    now = datetime.datetime.now()
                    if self._pending and str(self._pending.get("direction")) == "CLOSE":
                        self._call_device_updated()
                        return
                    else:
                        if self._status == STATE_CLOSING:
                            self._call_device_updated()
                            return
                        self._start_position = self.current_cover_position or self._position
                        self._requested_position = 0
                        self._start_time = now
                        self._status = STATE_CLOSING
                        self._command = CoverStatus.CLOSE
                        self._state_changetime = abs(self._requested_position - self._start_position) / 100 * float(self._opening_time_down or 20)
                        self._ensure_status_poll()
                        self._ensure_motion_tick()
                elif status_val == CoverStatus.STOP.value:
                    _freeze_now()
                elif status_val is None and self._status in (STATE_OPENING, STATE_CLOSING):
                    _freeze_now()
                elif status_val is not None:
                    _LOGGER.debug("cover control unexpected status_val=%s", status_val)
                    if self._status in (STATE_OPENING, STATE_CLOSING):
                        _freeze_now()

            else:
                # StatusResponse:
                if status_val == CoverStatus.STOP.value:
                    # 0 = STOP (o "non in movimento"). Se stiamo interpolando, fermiamoci subito.
                    if self._status in (STATE_OPENING, STATE_CLOSING):
                        _freeze_now()
                elif status_val == CoverStatus.OPEN.value:
                    now = datetime.datetime.now()
                    if self._pending and str(self._pending.get("direction")) == "OPEN":
                        # Movimento realmente iniziato: conferma bus => avvia subito (ignora start_delay).
                        self._start_motion_from_pending_delayed(
                            now=now,
                            start_pos=int(self._pending.get("start_pos") or 0),
                            respect_start_delay=False,
                        )
                    else:
                        # Movimento iniziato dall'esterno (HDL): avvia interpolazione verso 100 senza STOP schedulato.
                        # Evita "ripartenze fantasma" se siamo già al finecorsa.
                        try:
                            if int(self.current_cover_position or self._position) >= 100:
                                self._call_device_updated()
                                return
                        except Exception:
                            pass
                        if self._status != STATE_OPENING:
                            self._start_position = self.current_cover_position or self._position
                            self._requested_position = 100
                            self._start_time = now
                            self._status = STATE_OPENING
                            self._command = CoverStatus.OPEN
                            self._state_changetime = abs(self._requested_position - self._start_position) / 100 * float(self._opening_time_up or 20)
                            self._ensure_status_poll()
                            self._ensure_motion_tick()
                elif status_val == CoverStatus.CLOSE.value:
                    now = datetime.datetime.now()
                    if self._pending and str(self._pending.get("direction")) == "CLOSE":
                        self._start_motion_from_pending_delayed(
                            now=now,
                            start_pos=int(self._pending.get("start_pos") or 0),
                            respect_start_delay=False,
                        )
                    else:
                        try:
                            if int(self.current_cover_position or self._position) <= 0:
                                self._call_device_updated()
                                return
                        except Exception:
                            pass
                        if self._status != STATE_CLOSING:
                            self._start_position = self.current_cover_position or self._position
                            self._requested_position = 0
                            self._start_time = now
                            self._status = STATE_CLOSING
                            self._command = CoverStatus.CLOSE
                            self._state_changetime = abs(self._requested_position - self._start_position) / 100 * float(self._opening_time_down or 20)
                            self._ensure_status_poll()
                            self._ensure_motion_tick()
                elif status_val is None and self._status in (STATE_OPENING, STATE_CLOSING):
                    _freeze_now()
                # Non avviare movimenti da StatusResponse (evita ripartenze fantasma).
                elif status_val is not None and status_val not in (
                    CoverStatus.STOP.value,
                    CoverStatus.OPEN.value,
                    CoverStatus.CLOSE.value,
                ):
                    _LOGGER.debug("cover status unexpected status_val=%s -> freeze", status_val)
                    if self._status in (STATE_OPENING, STATE_CLOSING):
                        _freeze_now()

            self._call_device_updated()

    async def set_open(self):
        await self.set_position(100)

    async def set_close(self):
        await self.set_position(0)

    async def set_stop(self):
        """Ferma immediatamente e calcola la posizione corrente."""
        # cancella eventuale stop programmato
        if self._stop_task and not self._stop_task.done():
            self._stop_task.cancel()
        self._cancel_status_poll()
        self._cancel_motion_tick()
        self._cancel_pending_fallback()
        self._cancel_pending_start()
        self._cancel_pending_probe()
        self._pending = None

        now = datetime.datetime.now()
        # aggiorno posizione a base di quello che è trascorso finora
        if self._start_time and self._state_changetime > 0:
            elapsed = (now - self._start_time).total_seconds()
            frac = min(elapsed / self._state_changetime, 1.0)
            diff = self._requested_position - self._start_position
            self._position = int(self._start_position + diff * frac)

        # invio STOP
        self._command = CoverStatus.STOP
        self._status = CoverStatus.STOP
        await self._send_command()
        self._call_device_updated()

    async def set_position(self, position: int):
        """
        Porta la tapparella a `position`%:
        - legge la posizione corrente
        - sceglie OPEN o CLOSE
        - schedula un STOP dopo il tempo effettivo di movimento
        """
        # cancella qualsiasi stop pianificato
        if self._stop_task and not self._stop_task.done():
            self._stop_task.cancel()
        self._cancel_pending_fallback()
        self._cancel_pending_start()
        self._cancel_pending_probe()

        # calcola posizione di partenza (usa current_cover_position)
        self._start_position = self.current_cover_position or self._position
        self._requested_position = max(0, min(position, 100))

        # stabilisco direzione e durata
        if self._requested_position > self._start_position:
            self._command = CoverStatus.OPEN
            full_time = float(self._opening_time_up or 20)
            pending_dir = "OPEN"
        else:
            self._command = CoverStatus.CLOSE
            full_time = float(self._opening_time_down or 20)
            pending_dir = "CLOSE"

        self._state_changetime = abs(self._requested_position - self._start_position) / 100 * full_time

        # invio comando
        await self._send_command()
        self._call_device_updated()

        # Non far partire subito il conteggio: aspetta conferma OPENING/CLOSING dal bus (o fallback timeout).
        self._status = CoverStatus.STOP
        self._set_pending(direction=pending_dir, requested=self._requested_position, full_time=full_time, start_pos=int(self._start_position))

        async def _probe_pending_start() -> None:
            pending_ref = self._pending
            if not pending_ref:
                return
            issued_at = pending_ref.get("issued_at")
            for delay in (0.35, 0.9, 1.8):
                try:
                    await asyncio.sleep(delay)
                except asyncio.CancelledError:
                    return
                if not self._pending or self._pending is not pending_ref:
                    return
                if issued_at and self._pending.get("issued_at") != issued_at:
                    return
                try:
                    await self.read_status()
                except Exception:
                    pass

        async def _fallback_start() -> None:
            try:
                # Il movimento reale puÇý partire in ritardo (1-3s). Se facciamo partire il conteggio troppo presto,
                # la UI diventa fuori sincrono e "blocca" i comandi (crede di essere a 0/100 quando non lo Çù).
                wait_s = 1.2 + max(0.0, float(getattr(self, "_start_delay_s", 0.0) or 0.0))
                wait_s = max(1.0, min(6.0, wait_s))
                await asyncio.sleep(wait_s)
            except asyncio.CancelledError:
                return
            if not self._pending:
                return
            # Se non e' arrivata conferma, inizia comunque per non bloccare la UI (ma marcando started_by_timeout).
            try:
                self._pending["started_by_timeout"] = True
            except Exception:
                pass
            self._start_motion_from_pending(now=datetime.datetime.now(), start_pos=int(self._pending.get("start_pos") or 0))

        try:
            self._pending_probe_task = asyncio.create_task(_probe_pending_start())
            self._pending_fallback_task = asyncio.create_task(_fallback_start())
        except Exception:
            self._pending_probe_task = None
            self._pending_fallback_task = None

    async def _delayed_stop(self, delay_seconds: float | None = None):
        """Attende `delay_seconds` (default `state_changetime`), poi invia STOP e conferma stato finale."""
        try:
            delay = float(self._state_changetime) if delay_seconds is None else max(0.0, float(delay_seconds))
            await asyncio.sleep(delay)
        except asyncio.CancelledError:
            return

        now = datetime.datetime.now()
        pos_est = int(self._requested_position)
        try:
            if self._start_time and self._state_changetime and self._state_changetime > 0:
                elapsed = (now - self._start_time).total_seconds()
                frac = min(max(elapsed / float(self._state_changetime), 0.0), 1.0)
                diff = int(self._requested_position) - int(self._start_position)
                pos_est = int(round(int(self._start_position) + diff * frac))
        except Exception:
            pos_est = int(self._requested_position)

        # invio STOP
        self._command = CoverStatus.STOP
        await self._send_command()
        # Alcuni impianti ignorano un singolo STOP: ripeti una seconda volta.
        try:
            await asyncio.sleep(0.15)
            await self._send_command()
        except Exception:
            pass
        self._cancel_status_poll()
        self._cancel_motion_tick()
        self._cancel_pending_fallback()
        self._cancel_pending_start()
        self._cancel_pending_probe()
        self._pending = None

        # imposto posizione e stato finale
        # Non forzare a `requested_position`: se il motore è partito in ritardo, altrimenti la UI "mente".
        # Se siamo molto vicini alla richiesta, facciamo snap per evitare oscillazioni.
        try:
            if abs(int(pos_est) - int(self._requested_position)) <= 2:
                pos_est = int(self._requested_position)
        except Exception:
            pass
        self._position = int(max(0, min(100, pos_est)))
        self._status = (
            CoverStatus.OPEN if self._position == 100 else
            CoverStatus.CLOSE if self._position == 0 else
            CoverStatus.STOP
        )
        self._call_device_updated()
        # Best-effort: una lettura di stato dopo lo STOP riduce i casi "stuck" quando ci sono molte cover in parallelo.
        try:
            await asyncio.sleep(0.4)
            await self.read_status()
        except Exception:
            pass

    async def read_status(self):
        """Richiede lo status al gateway (se supportato)."""
        global _SEND_LOCK, _LAST_SEND_MONO
        if _SEND_LOCK is None:
            _SEND_LOCK = asyncio.Lock()
        rfhs = _ReadCoverStatus(self._buspro)
        rfhs.subnet_id, rfhs.device_id = self._device_address
        rfhs.channel_number = self._channel
        async with _SEND_LOCK:
            try:
                now = asyncio.get_running_loop().time()
            except Exception:
                now = datetime.datetime.now().timestamp()
            wait = max(0.0, float(_MIN_SEND_INTERVAL_S) - max(0.0, float(now) - float(_LAST_SEND_MONO)))
            if wait > 0:
                try:
                    await asyncio.sleep(wait)
                except asyncio.CancelledError:
                    raise
            await rfhs.send()
            try:
                _LAST_SEND_MONO = asyncio.get_running_loop().time()
            except Exception:
                _LAST_SEND_MONO = datetime.datetime.now().timestamp()

    def _call_read_current_status_of_channels(self, run_from_init=False):
        """Programma una lettura di status iniziale dopo qualche secondo."""
        async def _read():
            if run_from_init:
                await asyncio.sleep(5)
            await self.read_status()
        asyncio.ensure_future(_read(), loop=self._buspro.loop)

    @property
    def is_closed(self) -> bool:
        return self.current_cover_position == 0

    @property
    def is_opening(self) -> bool:
        return self._status == STATE_OPENING

    @property
    def is_closing(self) -> bool:
        return self._status == STATE_CLOSING

    @property
    def current_cover_position(self) -> int | None:
        """
        Se in movimento, restituisce l’interpolazione
        tra `_start_position` e `_requested_position`.
        Altrimenti ritorna `_position`.
        """
        if self._status in (STATE_OPENING, STATE_CLOSING) and self._start_time:
            elapsed = (datetime.datetime.now() - self._start_time).total_seconds()
            if 0 < self._state_changetime and elapsed < self._state_changetime:
                diff = self._requested_position - self._start_position
                pct = self._start_position + diff * (elapsed / self._state_changetime)
                return int(pct)
            if 0 < self._state_changetime and elapsed >= self._state_changetime:
                return int(self._requested_position)
        return self._position

    @property
    def device_identifier(self) -> str:
        return f"{self._device_address}-{self._channel}"

    async def _send_command(self):
        """Costruisce e invia il telegram di comando tramite _CoverControl."""
        global _SEND_LOCK, _LAST_SEND_MONO
        if _SEND_LOCK is None:
            _SEND_LOCK = asyncio.Lock()
        # Serialize and pace telegrams to reduce loss under load (e.g. 8-12 covers moving together).
        async with _SEND_LOCK:
            try:
                now = asyncio.get_running_loop().time()
            except Exception:
                now = datetime.datetime.now().timestamp()
            wait = max(0.0, float(_MIN_SEND_INTERVAL_S) - max(0.0, float(now) - float(_LAST_SEND_MONO)))
            if wait > 0:
                try:
                    await asyncio.sleep(wait)
                except asyncio.CancelledError:
                    raise
            scc = _CoverControl(self._buspro)
            scc.subnet_id, scc.device_id = self._device_address
            scc.channel_number = self._channel
            scc.channel_status = self._command
            await scc.send()
            try:
                _LAST_SEND_MONO = asyncio.get_running_loop().time()
            except Exception:
                _LAST_SEND_MONO = datetime.datetime.now().timestamp()
