import logging
from dnslib import DNSQuestion, DNSRecord
from dnslib import A, AAAA, CLASS, QR, QTYPE, RR


class DNSResolver(object):

    logger = logging.getLogger()

    async def handle_data(self, data, addr):
        self.logger.info("handle_data(%s, %s)", data, addr)
        record = DNSRecord.parse(data)
        if record.header.qr == QR.QUERY:
            await self.handle_query(record)
        else:
            pass

    async def handle_query(self, record):
        qname = str(record.q.qname)
        qtype = record.q.qtype
        qclass = record.q.qclass


    async def handle_other(self):
        pass

    def __query_db(self, record):
        """
        从数据库/缓存查询记录
        :param record:
        :return:
        """
        pass
