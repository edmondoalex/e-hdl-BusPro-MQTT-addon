from .udp_client import UDPClient
import asyncio
import time

from ..helpers.telegram_helper import TelegramHelper
# from ..devices.control import Control


class NetworkInterface:
    def __init__(self, buspro, gateway_address_send_receive):
        self.buspro = buspro
        self.gateway_address_send_receive = gateway_address_send_receive
        self.udp_client = None
        self.callback = None
        self._send_lock = asyncio.Lock()
        self._last_send_mono: float = 0.0
        self._init_udp_client()
        try:
            send_addr, _recv_addr = gateway_address_send_receive
            gw_host = send_addr[0] if isinstance(send_addr, tuple) and len(send_addr) >= 1 else None
        except Exception:
            gw_host = None
        self._th = TelegramHelper(gateway_host=gw_host)
        try:
            self.buspro.logger.info("TelegramHelper local_ip=%s", getattr(self._th, "local_ip", "?"))
        except Exception:
            pass

    def _init_udp_client(self):
        self.udp_client = UDPClient(self.buspro, self.gateway_address_send_receive, self._udp_request_received)

    def _udp_request_received(self, data, address):
        if self.callback is not None:
            telegram = self._th.build_telegram_from_udp_data(data, address)
            self.callback(telegram)

    async def _send_message(self, message):
        await self.udp_client.send_message(message)

    """
    public methods
    """
    def register_callback(self, callback):
        self.callback = callback

    async def start(self):
        await self.udp_client.start()

    async def stop(self):
        if self.udp_client is not None:
            await self.udp_client.stop()
            self.udp_client = None

    async def send_telegram(self, telegram):
        message = self._th.build_send_buffer(telegram)

        gateway_address_send, _ = self.gateway_address_send_receive
        self.buspro.logger.debug(self._th.build_telegram_from_udp_data(message, gateway_address_send))

        # Optional global pacing: protects BUS/gateway from bursts (startup reads, polling, sliders, scenes).
        try:
            min_interval_s = float(max(0.0, getattr(self.buspro, "_min_send_interval_s", 0.0) or 0.0))
        except Exception:
            min_interval_s = 0.0
        if min_interval_s > 0:
            async with self._send_lock:
                now = time.monotonic()
                wait_s = (self._last_send_mono + min_interval_s) - now
                if wait_s > 0:
                    await asyncio.sleep(wait_s)
                self._last_send_mono = time.monotonic()
                await self.udp_client.send_message(message)
            return

        await self.udp_client.send_message(message)
