import pickle
from pyfix.message import FIXMessage, FIXContext, FIXMessageSimple
from pyfix.protocol import LoadProtocol

__author__ = 'tom'

import unittest


class FIXMessageTests(unittest.TestCase):
    def setUp(self):
        self.protocol = LoadProtocol("pyfix.FIX44")

    def testMsgConstruction2(self):
        msg = FIXMessage(self.protocol.msgtype.NewOrderMultileg)

    def testMsgConstruction(self):
        msg = FIXMessage("AB")
        msg.setField("45", "dgd")
        msg.setField("32", "aaaa")
        msg.setField("323", "bbbb")

        rptgrp1 = FIXContext()
        rptgrp1.setField("611", "aaa")
        rptgrp1.setField("612", "bbb")
        rptgrp1.setField("613", "ccc")

        msg.addRepeatingGroup("444", rptgrp1, 0)

        rptgrp2 = FIXContext()
        rptgrp2.setField("611", "zzz")
        rptgrp2.setField("612", "yyy")
        rptgrp2.setField("613", "xxx")
        msg.addRepeatingGroup("444", rptgrp2, 1)

        self.assertEqual("45=dgd|32=aaaa|323=bbbb|444=2=>[611=aaa|612=bbb|613=ccc, 611=zzz|612=yyy|613=xxx]", str(msg))

        msg.removeRepeatingGroupByIndex("444", 1)
        self.assertEqual("45=dgd|32=aaaa|323=bbbb|444=1=>[611=aaa|612=bbb|613=ccc]", str(msg))

        msg.addRepeatingGroup("444", rptgrp2, 1)

        rptgrp3 = FIXContext()
        rptgrp3.setField("611", "ggg")
        rptgrp3.setField("612", "hhh")
        rptgrp3.setField("613", "jjj")
        rptgrp2.addRepeatingGroup("445", rptgrp3, 0)
        self.assertEqual("45=dgd|32=aaaa|323=bbbb|444=2=>[611=aaa|612=bbb|613=ccc, 611=zzz|612=yyy|613=xxx|445=1=>[611=ggg|612=hhh|613=jjj]]", str(msg))

        grp = msg.getRepeatingGroupByTag("444", "612", "yyy")
        self.assertEqual("611=zzz|612=yyy|613=xxx|445=1=>[611=ggg|612=hhh|613=jjj]", str(grp))

    def testPickle(self):
        msg = FIXMessage("AB")
        msg.setField("45", "dgd")
        msg.setField("32", "aaaa")
        msg.setField("323", "bbbb")

        rptgrp1 = FIXContext()
        rptgrp1.setField("611", "aaa")
        rptgrp1.setField("612", "bbb")
        rptgrp1.setField("613", "ccc")

        msg.addRepeatingGroup("444", rptgrp1, 0)

        str = pickle.dumps(msg)

        msg2 = pickle.loads(str)
        self.assertEqual(msg, msg2)

class FIXMessageSimpleTests(unittest.TestCase):
    def testMsgConstruction(self):
        rawmsg = b'8=FIX.4.4\x019=817\x0135=J\x0134=953\x0149=FIX_ALAUDIT\x0156=BFUT_ALAUDIT\x0143=N\x0152=20150615-09:21:42.459\x0170=00000002664ASLO1001\x01626=2\x0171=0\x0160=20150615-10:21:42\x01857=1\x0173=1\x0111=00000006321ORLO1\x0138=100.0\x01800=100.0\x01124=1\x0132=100.0\x0117=00000009758TRLO1\x0131=484.50\x0154=2\x0153=100.0\x0155=FTI\x01207=XEUE\x01454=1\x01455=EOM5\x01456=A\x01200=201506\x01541=20150619\x01461=FXXXXX\x016=484.50\x0174=2\x0175=20150615\x0178=2\x0179=TEST123\x01467=00000014901CALO1001\x0180=33.0\x01366=484.50\x0181=0\x01153=484.50\x0179=TEST124\x01467=00000014903CALO1001\x0180=67.0\x01366=484.50\x0181=0\x01153=484.50\x01453=3\x01448=TEST1\x01447=D\x01452=3\x01802=2\x01523=12345\x01803=3\x01523=TEST1\x01803=19\x01448=TEST1WA\x01447=D\x01452=38\x01802=4\x01523=Test1 Wait\x01803=10\x01523= \x01803=26\x01523=\x01803=3\x01523=TestWaCRF2\x01803=28\x01448=hagap\x01447=D\x01452=11\x01802=2\x01523=GB\x01803=25\x01523=BarCapFutures.FETService\x01803=24\x0110=033\x01'
        msg = FIXMessageSimple(rawmsg)
        msg.msgType

if __name__ == '__main__':
    unittest.main()
