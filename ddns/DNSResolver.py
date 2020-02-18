import logging
import sqlite3
from ddns import config
from dnslib import DNSQuestion, DNSRecord
from dnslib import A, AAAA, CLASS, QR, QTYPE, RR

CNAME = QTYPE.reverse["CNAME"]


class DNSResolver(object):

    logger = logging.getLogger()

    async def resolve(self, data, addr):
        record = DNSRecord.parse(data)
        self.logger.info(f"Request from ({addr[0]}:{addr[1]}) qclass={CLASS.get(record.q.qclass)}, qtype={QTYPE.get(record.q.qtype)}, qname={str(record.q.qname)}")
        if record.header.qr == QR.QUERY:
            await self.__handle_query(record)
        else:
            pass

    async def __handle_query(self, record):
        qname = str(record.q.qname)
        qtype = record.q.qtype
        qclass = record.q.qclass

        records = self.__query_db(record)
        if records:
            rr = []
            reply = record.reply()

            if len(records) == 1 and records[0].rtype == CNAME:
                rr.append(records[0].rr)
                #records = Record.objects.filter(rname=records[0].rdata)

            for record in records:
                rr.append(record.rr)

            reply.add_answer(*rr)
        else:
            #返回空
            pass


    async def handle_responser(self):
        pass

    def __query_db(self, record):
        """
        从数据库/缓存查询记录
        :param record:
        :return:
        """
        qname = str(record.q.qname)
        qtype = record.q.qtype
        qclass = record.q.qclass
        query_id = str((qname, qtype, qclass))
        conn = sqlite3.connect(self.db)
        cur = conn.cursor()
        sql = f"""
                    select record_value, ttl from {config.table_name} where query_id = ?
                """
        cur.execute(sql, query_id)
        val = cur.fetchall()
        cur.close()
        conn.close()
        return val


