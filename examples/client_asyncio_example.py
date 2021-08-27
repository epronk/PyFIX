import asyncio
from enum import Enum
import logging
import random
from pyfix.asyncio.connection import ConnectionState, MessageDirection
from pyfix.asyncio.client_connection import FIXClient
from pyfix.asyncio.engine import FIXEngine
from pyfix.message import FIXMessage


class Side(Enum):
    buy = 1
    sell = 2


class Client(FIXEngine):
    def __init__(self):
        FIXEngine.__init__(self, "client_example.store")
        self.clOrdID = 0
        self.msgGenerator = None

        # create a FIX Client using the FIX 4.4 standard
        self.client = FIXClient(self, "pyfix.FIX44", "INITIATOR", "ACCEPTOR")

        # we register some listeners since we want to know when the connection goes up or down
        self.client.addConnectionListener(self.onConnect, ConnectionState.CONNECTED)
        self.client.addConnectionListener(self.onDisconnect, ConnectionState.DISCONNECTED)

    async def start(self, host, port, loop):
        await self.client.start(host, port, loop)

    async def onConnect(self, session):
        logging.info("Established connection to %s" % (session.address(),))
        # register to receive message notifications on the session which has just been created
        session.addMessageHandler(self.onLogin, MessageDirection.INBOUND, self.client.protocol.msgtype.Logon)
        session.addMessageHandler(self.onExecutionReport, MessageDirection.INBOUND,
                                  self.client.protocol.msgtype.ExecutionReport)

    async def onDisconnect(self, session):
        logging.info("%s has disconnected" % (session.address(),))
        # we need to clean up our handlers, since this session is disconnected now
        session.removeMessageHandler(self.onLogin, MessageDirection.INBOUND, self.client.protocol.msgtype.Logon)
        session.removeMessageHandler(self.onExecutionReport, MessageDirection.INBOUND,
                                     self.client.protocol.msgtype.ExecutionReport)

    async def sendIndication(self, connectionHandler):
        self.clOrdID = self.clOrdID + 1
        codec = connectionHandler.codec
        msg = FIXMessage(codec.protocol.msgtype.IOI)
        msg.setField(codec.protocol.fixtags.Price, "2744.12")
        msg.setField(codec.protocol.fixtags.IOIQty, "5000")
        msg.setField(codec.protocol.fixtags.Symbol, "GOOG")
        msg.setField(codec.protocol.fixtags.IOIID, "424")
        msg.setField(codec.protocol.fixtags.IOIRefID, "399")
        msg.setField(codec.protocol.fixtags.IOIQty, "M")
        msg.setField(codec.protocol.fixtags.Side, "1")
        msg.setField(codec.protocol.fixtags.SecurityType, "PS")
        
        await connectionHandler.sendMsg(msg)

    async def sendOrder(self, connectionHandler):
        self.clOrdID = self.clOrdID + 1
        codec = connectionHandler.codec
        msg = FIXMessage(codec.protocol.msgtype.NewOrderSingle)
        msg.setField(codec.protocol.fixtags.Price, "%0.2f" % (random.random() * 2 + 10))
        msg.setField(codec.protocol.fixtags.OrderQty, int(random.random() * 100))
        msg.setField(codec.protocol.fixtags.Symbol, "VOD.L")
        msg.setField(codec.protocol.fixtags.SecurityID, "GB00BH4HKS39")
        msg.setField(codec.protocol.fixtags.SecurityIDSource, "4")
        msg.setField(codec.protocol.fixtags.Account, "TEST")
        msg.setField(codec.protocol.fixtags.HandlInst, "1")
        msg.setField(codec.protocol.fixtags.ExDestination, "XLON")
        msg.setField(codec.protocol.fixtags.Side, int(random.random() * 2) + 1)
        msg.setField(codec.protocol.fixtags.ClOrdID, str(self.clOrdID))
        msg.setField(codec.protocol.fixtags.Currency, "GBP")

        await connectionHandler.sendMsg(msg)
        side = Side(int(msg.getField(codec.protocol.fixtags.Side)))
        logging.debug("---> [%s] %s: %s %s %s@%s" % (
            msg.msgType.name, msg.getField(codec.protocol.fixtags.ClOrdID),
        msg.getField(codec.protocol.fixtags.Symbol), side.name, msg.getField(codec.protocol.fixtags.OrderQty),
        msg.getField(codec.protocol.fixtags.Price)))

    async def onLogin(self, connectionHandler, msg):
        logging.info("Logged in")

        #await self.sendOrder(connectionHandler)
        await self.sendIndication(connectionHandler)

    async def onExecutionReport(self, connectionHandler, msg):
        codec = connectionHandler.codec
        if codec.protocol.fixtags.ExecType in msg:
            if msg.getField(codec.protocol.fixtags.ExecType) == "0":
                side = Side(int(msg.getField(codec.protocol.fixtags.Side)))
                logging.debug("<--- [%s] %s: %s %s %s@%s" % (
                codec.protocol.msgtype.msgTypeToName(msg.getField(codec.protocol.fixtags.MsgType)),
                msg.getField(codec.protocol.fixtags.ClOrdID), msg.getField(codec.protocol.fixtags.Symbol), side.name,
                msg.getField(codec.protocol.fixtags.OrderQty), msg.getField(codec.protocol.fixtags.Price)))
            elif msg.getField(codec.protocol.fixtags.ExecType) == "4":
                reason = "Unknown" if codec.protocol.fixtags.Text not in msg else msg.getField(
                   codec.protocol.fixtags.Text)
                logging.info("Order Rejected '%s'" % (reason,))
        else:
            logging.error("Received execution report without ExecType")


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    loop = asyncio.get_event_loop()
    client = Client()
    loop.run_until_complete(client.start('192.168.0.71', 9810, loop))
    loop.run_forever()
