from typing import Literal, Union
from nonebot.adapters import BaseEvent
from nonebot.typing import Optional, overrides

from .utils import log
from .message import Message


class Event(BaseEvent):
    """
    钉钉 协议 Event 适配。继承属性参考 `BaseEvent <./#class-baseevent>`_ 。
    """

    def __init__(self, raw_event: dict):
        # 目前钉钉机器人只能接收到 text 类型的消息
        self.msg_type = raw_event.get("msgtype")
        if not self.msg_type:
            log("ERROR", "message has no msgtype")
        else:
            raw_event["message"] = Message(raw_event[self.msg_type]['content'])

        super().__init__(raw_event)

    @property
    @overrides(BaseEvent)
    def id(self) -> Optional[str]:
        """
        - 类型: ``Optional[str]``
        - 说明: 消息 ID
        """
        return self._raw_event.get("msgId")

    @property
    @overrides(BaseEvent)
    def name(self) -> str:
        """
        - 类型: ``str``
        - 说明: 事件名称，由类型与 ``.`` 组合而成
        """
        n = self.type + "." + self.detail_type
        if self.sub_type:
            n += "." + self.sub_type
        return n

    @property
    @overrides(BaseEvent)
    def self_id(self) -> str:
        """
        - 类型: ``str``
        - 说明: 机器人自身 ID
        """
        return str(self._raw_event["chatbotUserId"])

    @property
    @overrides(BaseEvent)
    def time(self) -> int:
        """
        - 类型: ``int``
        - 说明: 消息的时间戳，单位 s
        """
        # 单位 ms
        return int(self._raw_event["createAt"] / 1000)

    @property
    @overrides(BaseEvent)
    def type(self) -> str:
        """
        - 类型: ``str``
        - 说明: 事件类型
        """
        return "message"

    @type.setter
    @overrides(BaseEvent)
    def type(self, value) -> None:
        pass

    @property
    @overrides(BaseEvent)
    def detail_type(
            self
    ) -> Union[Literal["friend"], Literal["group"], Literal["other"]]:
        """
        - 类型: ``str``
        - 说明: 事件详细类型
        """
        conversation_type = self._raw_event["conversationType"]
        if conversation_type == '1':
            # 私聊
            return "friend"
        elif conversation_type == '2':
            # 群聊
            return "group"
        return "other"

    @detail_type.setter
    @overrides(BaseEvent)
    def detail_type(self, value) -> None:
        if value == "friend":
            self._raw_event["conversationType"] = '1'
        if value == "group":
            self._raw_event["conversationType"] = '2'

    @property
    @overrides(BaseEvent)
    def sub_type(self) -> Optional[str]:
        """
        - 类型: ``Optional[str]``
        - 说明: 事件子类型
        """
        return ""

    @sub_type.setter
    @overrides(BaseEvent)
    def sub_type(self, value) -> None:
        pass

    @property
    @overrides(BaseEvent)
    def user_id(self) -> Optional[str]:
        """
        - 类型: ``Optional[str]``
        - 说明: 发送者 ID
        """
        return self._raw_event.get("senderId")

    @user_id.setter
    @overrides(BaseEvent)
    def user_id(self, value) -> None:
        self._raw_event["senderId"] = value

    @property
    @overrides(BaseEvent)
    def group_id(self) -> Optional[str]:
        """
        - 类型: ``Optional[str]``
        - 说明: 事件主体群 ID
        """
        return self._raw_event.get("conversationId")

    @group_id.setter
    @overrides(BaseEvent)
    def group_id(self, value) -> None:
        self._raw_event["conversationId"] = value

    @property
    def group_title(self) -> Optional[str]:
        """
        - 类型: ``Optional[str]``
        - 说明: 群聊时才有的会话标题。
        """
        return self._raw_event.get("conversationTitle")

    @group_title.setter
    def group_title(self, value) -> None:
        self._raw_event["conversationTitle"] = value

    @property
    @overrides(BaseEvent)
    def to_me(self) -> Optional[bool]:
        """
        - 类型: ``Optional[bool]``
        - 说明: 消息是否与机器人相关
        """
        return self.detail_type == 'friend' or self._raw_event.get(
            "isInAtList", False)

    @to_me.setter
    @overrides(BaseEvent)
    def to_me(self, value) -> None:
        self._raw_event["isInAtList"] = value

    @property
    @overrides(BaseEvent)
    def message(self) -> Optional["Message"]:
        """
        - 类型: ``Optional[Message]``
        - 说明: 消息内容
        """
        return self._raw_event.get("message")

    @message.setter
    @overrides(BaseEvent)
    def message(self, value) -> None:
        self._raw_event["message"] = value

    @property
    @overrides(BaseEvent)
    def reply(self) -> None:
        """
        - 类型: ``None``
        - 说明: 回复消息详情
        """
        raise ValueError("暂不支持 reply")

    @property
    @overrides(BaseEvent)
    def raw_message(self) -> Optional[str]:
        """
        - 类型: ``Optional[str]``
        - 说明: 原始消息
        """
        return self._raw_event.get(self.msg_type, {})['content']

    @raw_message.setter
    @overrides(BaseEvent)
    def raw_message(self, value) -> None:
        self._raw_event[self.msg_type]['content'] = value

    @property
    @overrides(BaseEvent)
    def plain_text(self) -> Optional[str]:
        """
        - 类型: ``Optional[str]``
        - 说明: 纯文本消息内容
        """
        return self.message and self.message.extract_plain_text()

    @property
    @overrides(BaseEvent)
    def sender(self) -> Optional[dict]:
        """
        - 类型: ``Optional[dict]``
        - 说明: 消息发送者信息
        """
        result = {
            # 加密的发送者ID。
            "senderId": self._raw_event.get("senderId"),
            # 发送者昵称。
            "senderNick": self._raw_event.get("senderNick"),
            # 企业内部群有的发送者当前群的企业 corpId。
            "senderCorpId": self._raw_event.get("senderCorpId"),
            # 企业内部群有的发送者在企业内的 userId。
            "senderStaffId": self._raw_event.get("senderStaffId"),
        }
        return result

    @sender.setter
    @overrides(BaseEvent)
    def sender(self, value) -> None:

        def set_wrapper(name):
            if value.get(name):
                self._raw_event[name] = value.get(name)

        set_wrapper("senderId")
        set_wrapper("senderNick")
        set_wrapper("senderCorpId")
        set_wrapper("senderStaffId")
