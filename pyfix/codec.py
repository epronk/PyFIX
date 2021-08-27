from datetime import datetime, timezone
import logging
from pyfix.message import FIXMessage, FIXContext
from fixorchestra.orchestration import Orchestration, MessageField, Component, Group
from more_itertools import peekable
import pyfix.clock
from pyfix.message import FIXMessageSimple

class DictBuilder(object):
    def insert(self, obj, value):
        obj.append(value)

    def createNode(self):
        return []

    def insertList(self, output, tag):
        node = []
        output.append(node)
        return node

    def insertNode(self, output, tag, t):
        node = []
        output.append({tag: node})
        return node


class Parser(object):
    def __init__(self, dictionary, builder):
        self.dictionary = dictionary
        self.builder = builder
        self.output = builder.createNode()
        self.header_tags = tuple(x.field_id for x in dictionary.orchestration.components["1024"].references)

    def parse(self, it):
        message = self.parseHeader(it)
        try:
            self.parseMessage(it, message, self.output)
        except StopIteration as e:
            pass

    def parseHeader(self, it):
        tag, value = it.peek()
        while tag in self.header_tags:
            if tag == 35:
                message = self.dictionary.orchestration.messages_by_msg_type[value]
            tag, value = next(it)
            self.builder.insert(self.output, (tag, value))
            tag, value = it.peek()
        return message

    def parseMessage(self, it, message, output):
        index = self.dictionary.tag_index[message.id]
        while True:
            tag, value = it.peek()
            entity = index.get(tag)
            if entity is None:
                pass
            elif entity is message:
                pass
            elif isinstance(entity, Component):
                self.parseComponent(it, entity, self.output)
            else:
                self.parseGroup(it, entity, self.output)
                continue
            tag, value = next(it)
            self.builder.insert(self.output, (tag, value))

    def parseComponent(self, it, message, output):
        index = self.dictionary.tag_index[message.id]
        while True:
            tag, value = it.peek()
            entity = index.get(tag)
            if entity is None:
                return
            elif entity is message:
                pass
            elif isinstance(entity, Component):
                self.parse_component(it, entity, self.output)
            else:
                self.parseGroup(it, entity, self.output)
                continue
            self.builder.insert(self.output, (tag, value))
            next(it)

    def parseGroup(self, it, group, output):
        index = self.dictionary.tag_index[group.id]
        tag, value = next(it)
        node = self.builder.insertNode(output, tag, (tag, value))
        tag, value = it.peek()
        first = tag
        while True:
            while True:
                entity = index.get(tag)
                if entity is group:
                    if tag == first:
                        ol = self.builder.insertList(node, tag)
                    self.builder.insert(ol, (tag, value))
                    next(it)
                    tag, value = it.peek()
                elif isinstance(entity, Group):
                    self.parseGroup(it, entity, ol)
                    tag, value = it.peek()
                    break
                else:
                    break
            if tag != first:
                break


class Dictionary:
    def __init__(self, orchestration):
        self.orchestration = orchestration
        self.tag_index = {}
        self.buildIndex()

    def buildIndex(self):
        for k, v in self.orchestration.messages.items():
            message = self.orchestration.messages_by_msg_type[v.msg_type]
            references = iter(message.references)
            next(references)  # skip header
            self.references_to_fields(references, 0, (message,))

    def references_to_fields(self, references, depth, context):
        result = {}
        for reference in references:
            if reference.field_id:
                adding = (MessageField(self.orchestration.fields_by_tag[reference.field_id], reference.presence, depth), context)
                result[reference.field_id] = context[-1]
            elif reference.group_id:
                group = self.orchestration.groups[reference.group_id]
                adding = self.references_to_fields(group.references, depth, context + (group,))
                first = next(iter(adding))
                result[first] = adding[first]
            elif reference.component_id:
                component = self.orchestration.components[reference.component_id]
                adding = self.references_to_fields(component.references, depth, context + (component,))
                result.update(adding)
        self.tag_index.setdefault(context[-1].id, result)
        return result


class Writer:

    def __init__(self):
        self.txt = ''

    def write(self, msg):
        self.txt = '|'.join(self.get_item(item) for item in msg)

    def get_item(self, msg):
        if isinstance(msg, tuple):
            return str(msg[0]) + '=' + msg[1]
        elif isinstance(msg, dict):
            txt = ''
            for k, v in msg.items():
                txt += str(k) + '=' + str(len(v)) + '=>'
                txt += '['
                txt += ', '.join(['|'.join(self.get_item(y) for y in x) for x in v])
                txt += ']'

            return txt


class EncodingError(Exception):
    pass


class DecodingError(Exception):
    pass


class RepeatingGroupContext(FIXContext):
    def __init__(self, tag, repeatingGroupTags, parent):
        self.tag = tag
        self.repeatingGroupTags = repeatingGroupTags
        self.parent = parent
        FIXContext.__init__(self)


class Codec(object):
    def __init__(self, protocol):
        self.protocol = protocol
        self.SOH = '\x01'

    @staticmethod
    def current_datetime():
        return pyfix.clock.clock().strftime("%Y%m%d-%H:%M:%S.%f")[:-3]

    def _addTag(self, body, t, msg):
        if msg.isRepeatingGroup(t):
            count, groups = msg.getRepeatingGroup(t)
            body.append("%s=%s" % (t, count))
            for group in groups:
                for tag in group.tags:
                    self._addTag(body, tag, group)
        else:
            body.append("%s=%s" % (t, msg[t]))

    def encode(self, msg, session):
        # Create body
        body = []

        msgType = msg.msgType

        body.append("%s=%s" % (int(self.protocol.fixtags.SenderCompID), session.senderCompId))
        body.append("%s=%s" % (int(self.protocol.fixtags.TargetCompID), session.targetCompId))

        seqNo = 0
        if msgType == self.protocol.msgtype.SequenceReset:
            if self.protocol.fixtags.GapFillFlag in msg and msg[self.protocol.fixtags.GapFillFlag] == "Y":
                # in this case the sequence number should already be on the message
                try:
                    seqNo = msg[int(self.protocol.fixtags.MsgSeqNum)]
                except KeyError:
                    raise EncodingError("SequenceReset with GapFill='Y' must have the MsgSeqNum already populated")
            else:
                msg[self.protocol.fixtags.NewSeqNo] = session.allocateSndSeqNo()
                seqNo = msg[int(self.protocol.fixtags.MsgSeqNum)]
        else:
            # if we have the PossDupFlag set, we need to send the message with the same seqNo
            if self.protocol.fixtags.PossDupFlag in msg and msg[self.protocol.fixtags.PossDupFlag] == "Y":
                try:
                    seqNo = msg[int(self.protocol.fixtags.MsgSeqNum)]
                except KeyError:
                    raise EncodingError("Failed to encode message with PossDupFlay=Y but no previous MsgSeqNum")
            else:
                seqNo = session.allocateSndSeqNo()

        body.append("%s=%s" % (int(self.protocol.fixtags.MsgSeqNum), seqNo))
        body.append("%s=%s" % (int(self.protocol.fixtags.SendingTime), self.current_datetime()))

        for t in msg.tags:
            self._addTag(body, t, msg)

        # Enable easy change when debugging
        SEP = self.SOH

        body = self.SOH.join(body) + self.SOH

        # Create header
        header = []
        msgType = "%s=%s" % (int(self.protocol.fixtags.MsgType), str(msgType))
        header.append("%s=%s" % (int(self.protocol.fixtags.BeginString), self.protocol.beginstring))
        header.append("%s=%i" % (int(self.protocol.fixtags.BodyLength), len(body) + len(msgType) + 1))
        header.append(msgType)

        fixmsg = self.SOH.join(header) + self.SOH + body

        cksum = sum([ord(i) for i in list(fixmsg)]) % 256
        fixmsg = fixmsg + "%s=%0.3i" % (int(self.protocol.fixtags.CheckSum), cksum)

        return fixmsg + SEP

    def decode2(self, rawmsg):
        #print('raw1', rawmsg)
        SOH = '\x01'
        rawmsg = rawmsg.decode('utf-8')

        s = rawmsg.find(SOH)
        if s == -1:
            return None, 0
        s2 = rawmsg.find(SOH, s + 1)
        tag, value =rawmsg[s + 1 :s2].split('=')
        length = int(value) + s2 + 8
        decodedMsg = FIXMessageSimple(rawmsg[:length])
        #print('raw2', rawmsg[:length])
        return decodedMsg, length
    
    def decode(self, rawmsg):
        rawmsg = rawmsg.decode('utf-8')
        tup = [(int(k), v) for k, v in tuple((x.split('=')) for x in rawmsg[:-1].split(self.SOH))]
        builder = DictBuilder()
        theIndex = Dictionary(Orchestration('fix_repository_4_4.xml'))
        p = Parser(theIndex, builder)
        it = peekable(tup)
        p.parse(it)
        writer = Writer()
        writer.write(p.output)
        return writer.txt, None
