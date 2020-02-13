import asyncio
from asyncio import DatagramProtocol
import logging
from ddns.DNSResolver import DNSResolver


class UDPServer(DatagramProtocol):
    """
    UDP dns server
    """
    logger = logging.getLogger()

    def __init__(self, resolver:DNSResolver):
        self.resolver = resolver
        self.transport = None
        self.logger.debug("udp dns server created!")

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        asyncio.create_task(self.resolver.handle_data(data, addr))

    def error_received(self, exc):
        self.logger.error(exc)

