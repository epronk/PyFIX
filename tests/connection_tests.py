import time
import asyncio
from threading import Thread
import unittest
from pyfix.asyncio.engine import FIXEngine
from pyfix.asyncio.client_connection import FIXClient
from pyfix.asyncio.server_connection import FIXServer
from pyfix.asyncio.connection import ConnectionState
from pyfix.message import MessageDirection

#from pyfix.asyncio.engine import FIXEngine
import logging

class System(object):

    def start(self):
        print('system.start')
        #self.loop = asyncio.new_event_loop()
        self.loop = asyncio.get_event_loop()
        self.thread = Thread(target=self.event_loop, args=(self.loop,))
        self.thread.start()

    def stop(self):
        print('system.stop')

        # Stop loop:
        self.loop.stop()

        # Find all running tasks:
        #pending = asyncio.all_tasks()

        # Run loop until tasks done:
        #self.loop.run_until_complete(asyncio.gather(*pending))

    def event_loop(self, arg):
        #asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

class Server(FIXEngine):
    def __init__(self):
        FIXEngine.__init__(self, "server_example.store")
        # create a FIX Server using the FIX 4.4 standard
        self.server = FIXServer(self, "pyfix.FIX44")

        # we register some listeners since we want to know when the connection goes up or down
        self.server.addConnectionListener(self.onConnect, ConnectionState.CONNECTED)
        self.server.addConnectionListener(self.onDisconnect, ConnectionState.DISCONNECTED)

    async def start(self, host, port, loop):
        await self.server.start(host, port, loop)

    async def stop(self):
        await self.server.stop()

    def validateSession(self, targetCompId, senderCompId):
        logging.info("Received login request for %s / %s" % (senderCompId, targetCompId))
        return True

    async def onConnect(self, session):
        logging.info("Accepted new connection from %s" % (session.address(),))
        # register to receive message notifications on the session which has just been created
        session.addMessageHandler(self.onLogin, MessageDirection.OUTBOUND, self.server.protocol.msgtype.Logon)
        #session.addMessageHandler(self.onNewOrder, MessageDirection.INBOUND,
        #                          self.server.protocol.msgtype.NewOrderSingle)

    async def onDisconnect(self, session):
        logging.info("%s has disconnected" % (session.address(),))
        # we need to clean up our handlers, since this session is disconnected now
        session.removeMessageHandler(self.onLogin, MessageDirection.OUTBOUND, self.server.protocol.msgtype.Logon)
        #session.removeMessageHandler(self.onNewOrder, MessageDirection.INBOUND,
        #                             self.server.protocol.msgtype.NewOrderSingle)

    async def onLogin(self, connectionHandler, msg):
        print('onLogin', msg)
        #codec = connectionHandler.codec
        #logging.info("[" + msg[codec.protocol.fixtags.SenderCompID] + "] <---- " + codec.protocol.msgtype.msgTypeToName(
        #    msg[codec.protocol.fixtags.MsgType]))

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

    def addConnectionFuture(self, fut):
        self.client.addConnectionFuture(fut)

    async def start(self, host, port, loop):
        await self.client.start(host, port, loop)

    async def onConnect(self, session):
        print('onConnect')
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
        msg.setField(codec.protocol.fixtags.Price, "%0.2f" % (random.random() * 2 + 10))
        msg.setField(codec.protocol.fixtags.IOIID, "babe")
        
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
        logging.info("Client Logged in")

        #await self.sendOrder(connectionHandler)
        #await self.sendIndication(connectionHandler)

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

def wait_routine(fut):
    loop = asyncio.get_event_loop() # fixme
    loop.run_until_complete(fut)

def wait(fut):
    loop = asyncio.get_event_loop() # fixme
    loop.run_until_complete(fut)
    return fut.result()
            
class ConnectionTests(unittest.TestCase):

    async def start_services(self):
        self.client = Client()
        loop = asyncio.get_event_loop() # fixme
        self.connected = loop.create_future()
        self.client.addConnectionFuture(self.connected)
        self.server = Server()
        await self.server.start('0.0.0.0', 9898, loop)
        await self.client.start('localhost', 9898, loop)
        
    async def stop_services(self):
        print('stop services')
        #await self.server.stop()

    def setUp(self):
        self.system = System()
        #self.system.start()
        future = self.start_services() # asyncio.run_coroutine_threadsafe(self.start_services(), self.system.loop)
        wait_routine(future)
        #result = future.result()

    def tearDown(self):
        print('tearDown 1')
        #future = asyncio.run_coroutine_threadsafe(self.stop_services(), self.system.loop)
        #result = future.result()
        print('tearDown 2')
        #self.system.loop.call_soon_threadsafe(self.system.loop.stop)
        #self.system.loop.call_soon_threadsafe(self.system.stop)
        print('tearDown done')

    def test1(self):
        connection = wait(self.connected)
        print('connection', connection)
        print(dir(connection))
        print('test done')
        pass

    def _test2(self):
        pass


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()

    
