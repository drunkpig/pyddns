import logging
import asyncio
import sqlite3
from logging.config import fileConfig
from ddns import config
from ddns.DNSResolver import DNSResolver
from ddns.UDPServer import UDPServer


async def start_server(host='0.0.0.0', port=53):
    loop = asyncio.get_event_loop()
    resolver = DNSResolver()
    transport, protocol = await loop.create_datagram_endpoint(
        lambda: UDPServer(resolver), local_addr=(host, port))

    return transport, protocol, resolver


def __init_db(dbpath, dbname, table_name):

    db = f"{dbpath}/{dbname}"
    print(f"use db {db}")
    conn = sqlite3.connect(db)
    cur = conn.cursor()
    sql = f"""
        create table  if not exists  {table_name}(
        id INTEGER  PRIMARY KEY autoincrement,
        name VARCHAR(255),
        ttl INTEGER,
        record_class VARCHAR(255),
        record_type VARCHAR(255),
        record_data VARCHAR(255),
        last_modify VARCHAR(255),
        comment VARCHAR(512)
        )
    """
    cur.execute(sql)
    conn.commit()
    cur.close()
    conn.close()


if __name__=="__main__":
    fileConfig('../logging.ini')
    logger = logging.getLogger()
    __init_db(config.db_path, config.db_name, config.table_name)
    loop = asyncio.get_event_loop()
    server, udp_transports, resolver = loop.run_until_complete(start_server(host='0.0.0.0', port=53))
    logger.info("server start.")
    loop.run_forever()
