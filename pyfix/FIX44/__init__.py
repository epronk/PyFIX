from fixorchestra.orchestration import *
from pyfix.message import FIXMessage

__author__ = 'tom'

beginstring = 'FIX.4.4'

import enum

class StrEnum(str, enum.Enum):
    def __str__(self):
        return str(self.value)


orchestration = Orchestration('fix_repository_4_4.xml')

fixtags = enum.IntEnum('Tags', {tag.name : tag_number for tag_number, tag in orchestration.fields_by_tag.items()})
msgtype = StrEnum('MsgType', {message.name : message.msg_type for message in orchestration.messages.values()})
sessionMessageTypes = [message.msg_type for message in orchestration.messages.values() if message.category == 'Session']

class Messages(object):

    @staticmethod
    def logon():
        msg = FIXMessage(msgtype.Logon)
        msg.setField(fixtags.EncryptMethod, 0)
        msg.setField(fixtags.HeartBtInt, 30)
        return msg

    @staticmethod
    def logout():
        msg = FIXMessage(msgtype.Logout)
        return msg

    @staticmethod
    def heartbeat():
        msg = FIXMessage(msgtype.Heartbeat)
        return msg

    @staticmethod
    def test_request():
        msg = FIXMessage(msgtype.TeestRequest)
        return msg

    @staticmethod
    def sequence_reset(respondingTo, isGapFill):
        msg = FIXMessage(msgtype.SequenceReset)
        msg.setField(fixtags.GapFillFlag, 'Y' if isGapFill else 'N')
        msg.setField(fixtags.MsgSeqNum, respondingTo[fixtags.BeginSeqNo])
        return msg

    @staticmethod
    def resend_request(beginSeqNo, endSeqNo = '0'):
        msg = FIXMessage(msgtype.ResendRequest)
        msg.setField(fixtags.BeginSeqNo, str(beginSeqNo))
        msg.setField(fixtags.EndSeqNo, str(endSeqNo))
        return msg

messages = Messages()
