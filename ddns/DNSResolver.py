import logging
import aiosqlite
from ddns import config
from dnslib import DNSQuestion, DNSRecord
from dnslib import A, AAAA, CLASS, QR, QTYPE, RR,RDMAP
import random

CNAME = QTYPE.reverse["CNAME"]


class DNSResolver(object):

    logger = logging.getLogger()

    def __init__(self):
        self.peers = {}
        self.requests = {}
        self.db = f"{config.db_path}/{config.db_name}"
        self.transport = None  #连接建立时被初始化

    async def resolve(self, data, addr):
        record = DNSRecord.parse(data)
        self.logger.info(f"<<< from ({addr[0]}:{addr[1]}) qclass={CLASS.get(record.q.qclass)}, qtype={QTYPE.get(record.q.qtype)}, qname={str(record.q.qname)}")
        if record.header.qr == QR.QUERY:         # 如果是查询这台服务器
            pkg = await self.__handle_query(record, addr)
            if pkg is not None:
                self.transport.send_to(pkg, addr)
        else:                # 如果是自己发出的递归查询的回复 TODO 检查回复包是不是对的
            await self.__handle_response(data, addr)

    async def __handle_query(self, record, addr):
        records = await self.__query_db(record)
        if records:
            rr = []
            reply = record.reply()

            if len(records) == 1 and records[0].record_type == CNAME:
                rr.append(records[0].rr)
                records = await self.__query_cname(records[0].record_data)
            for r in records:
                rr.append(r.rr)

            reply.add_answer(*rr)
            self.logger.info(f">>> {addr}, {rr}")
            return reply.pack()
        else:
            await self.__forward_query(record, addr)
            return None

    async def __handle_response(self, response, peer):
        """
        本地没查到，本服务做递归DNS查询，其他服务器返回的结果
        :return:
        """
        record = DNSRecord.parse(response)
        id = record.header.id

        qname = str(record.q.qname)
        qtype = record.q.qtype
        qclass = record.q.qclass

        if id not in self.peers:
            self.logger.info(
                "Unknown Response ({0:s}): {1:s} {2:s} {3:s}".format(
                    "{0:s}:{1:d}".format(*peer),
                    CLASS.get(qclass), QTYPE.get(qtype), qname
                )
            )

            return

        addr = self.peers[id]
        request = self.requests[id]
        reply = request.reply()
        reply.add_answer(*record.rr)
        del self.peers[id]
        del self.requests[id]
        self.transport.sendto(reply.pack(), addr)
        self.logger.info(f"==Reply from {peer}")

    async def __forward_query(self, request, addr):
        """
        本服务没查到，转发查询到其他DNS服务器
        :return:
        """
        qname = str(request.q.qname)
        qtype = request.q.qtype
        qclass = request.q.qclass
        lookup = DNSRecord(q=DNSQuestion(qname, qtype, qclass))
        id = lookup.header.id
        self.peers[id] = addr
        self.requests[id] = request
        self.transport.sendto(lookup.pack(), (random.choice(config.forward_dns),53))
        self.logger.info("<<<>>> Froward")

    async def __query_cname(self, rdata):
        records = []
        async with aiosqlite.connect(self.db) as db:
            sql = """
            select id, name, ttl, record_class, record_type, record_data, last_modify, comment from {config.table_name} where record_name = ?
            """
            async with db.execute(sql, rdata) as cur:
                async for rr in cur:
                    m = RecordModel()
                    m.id = rr[0]
                    m.name = rr[1]
                    m.ttl = rr[2]
                    m.record_class = rr[3]
                    m.record_type = rr[4]
                    m.record_data = rr[5]
                    m.last_modify = rr[6]
                    m.comment = rr[7]
                    records.append(m)

        return records

    async def __query_db(self, record):
        """
        从数据库/缓存查询记录
        :param record:
        :return:
        """

        qname = str(record.q.qname)
        qclass = record.q.qclass
        qtype = record.q.qtype
        records = []
        async with aiosqlite.connect(self.db) as db:
            sql = f"""
                        select id, ttl, record_data, last_modify, comment from {config.table_name} where name = ?
                        and record_class=? and record_type=?
                    """
            async with db.execute(sql, (qname, qclass, qtype)) as cur:
                async for rr in cur:
                    m = RecordModel()
                    m.id = rr[0]
                    m.name = qname
                    m.ttl = rr[1]
                    m.record_class = qclass
                    m.record_type = qtype
                    m.record_data = rr[2]
                    m.last_modify = rr[3]
                    m.comment = rr[4]
                    records.append(m)
        return records


class RecordModel(object):
    def __init__(self):
        self.id = None
        self.name=None
        self.ttl=None
        self.record_class = None
        self.record_type = None
        self.record_data = None
        self.last_modify = None
        self.comment = None

    @property
    def rr(self):
        rdata = RDMAP[QTYPE[self.record_type]](self.record_data)
        return RR(self.name, self.record_type, self.record_class, self.ttl, rdata)
