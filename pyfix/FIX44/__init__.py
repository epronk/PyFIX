from fixorchestra.orchestration import *

__author__ = 'tom'

beginstring = 'FIX.4.4'

import enum

class StrEnum(str, enum.Enum):
    def __str__(self):
        return str(self.value)


orchestration = Orchestration('fix_repository_4_4.xml')

fixtags = enum.IntEnum('Tags', {tag.name : tag_number for tag_number, tag in orchestration.fields_by_tag.items()})
msgtype = StrEnum('MsgType', {message.name : message.msg_type for message in orchestration.messages.values()})
