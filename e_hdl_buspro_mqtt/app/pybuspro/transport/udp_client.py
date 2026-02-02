import asyncio
import socket
import binascii


class UDPClient:

    class UDPClientFactory(asyncio.DatagramProtocol):

        def __init__(self, buspro, data_received_callback=None):
            self.buspro = buspro
            self.transport = None
            self.data_received_callback = data_received_callback

        def connection_made(self, transport):
            self.transport = transport

        def datagram_received(self, data, address):
            try:
                # Raw RX trace (useful when telegram decoding fails or nothing appears in sniffer).
                # Enabled when buspro.log is in DEBUG (debug_telegram true in add-on options).
                if getattr(self.buspro, "logger", None) is not None and self.buspro.logger.isEnabledFor(10):
                    prefix = binascii.hexlify(bytes(data[:48])).decode("ascii") if data else ""
                    self.buspro.logger.debug("UDP RX from %s:%s len=%s hex=%s", address[0], address[1], len(data or b""), prefix)
            except Exception:
                pass
            if self.data_received_callback is not None:
                self.data_received_callback(data, address)

        def error_received(self, exc):
            self.buspro.logger.warning('Error received: %s', exc)
            pass

        def connection_lost(self, exc):
            self.buspro.logger.info('closing transport %s', exc)
            pass

    def __init__(self, buspro, gateway_address_send_receive, callback):
        self.buspro = buspro
        self._gateway_address_send, self._gateway_address_receive = gateway_address_send_receive
        self.callback = callback
        self.transport = None

    # def register_callback(self, callback):
    #     self.callback = callback

    def _data_received_callback(self, data, address):
        self.callback(data, address)

    def _create_multicast_sock(self):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.setblocking(False)
            sock.bind(self._gateway_address_receive)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 0)
            return sock
        except Exception as ex:
            self.buspro.logger.warning("Could not connect to {}: {}".format(self._gateway_address_receive, ex))

    async def _connect(self):
        try:
            udp_client_factory = \
                UDPClient.UDPClientFactory(self.buspro, data_received_callback=self._data_received_callback)

            sock = self._create_multicast_sock()
            if sock is None:
                self.buspro.logger.warning("Socket is None")
                return

            (transport, _) = await self.buspro.loop.create_datagram_endpoint(lambda: udp_client_factory, sock=sock)

            self.transport = transport
        except Exception as ex:
            self.buspro.logger.warning("Could not create endpoint to {}: {}".format(self._gateway_address_receive, ex))

    async def start(self):
        await self._connect()

    async def stop(self):
        if self.transport is not None:
            self.transport.close()

    async def send_message(self, message):
        if self.transport is not None:
            self.transport.sendto(message, self._gateway_address_send)
        else:
            self.buspro.logger.info("Could not send message. Transport is None.")
