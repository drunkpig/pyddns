import asyncio
import logging
from logging.config import fileConfig
from ddns.DNSResolver import DNSResolver
from ddns.UDPServer import UDPServer


def handle_exception(loop, context):
    # context["message"] will always be there; but context["exception"] may not
    msg = context.get("exception", context["message"])
    logging.error(f"Caught exception: {msg}")
    logging.error(context.get("exception"))


async def start_server(host='0.0.0.0', port=53):
    loop = asyncio.get_event_loop()
    loop.set_exception_handler(handle_exception)
    resolver = DNSResolver()
    transport, protocol = await loop.create_datagram_endpoint(
        lambda: UDPServer(resolver), local_addr=(host, port))

    return transport, protocol, resolver


if __name__ == "__main__":
    fileConfig('../logging.ini')
    logger = logging.getLogger()
    loop = asyncio.get_event_loop()
    server, udp_transports, resolver = loop.run_until_complete(start_server(host='0.0.0.0', port=53))
    logger.info("server start.")
    loop.run_forever()
