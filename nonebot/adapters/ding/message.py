import re

import httpx

from nonebot.log import logger
from nonebot.config import Config
from nonebot.message import handle_event
from nonebot.typing import overrides, Driver, WebSocket, NoReturn
from nonebot.typing import Any, Dict, Union, Tuple, Iterable, Optional
from nonebot.adapters import BaseBot, BaseEvent, BaseMessage, BaseMessageSegment
from nonebot.exception import NetworkError, ActionFailed, RequestDenied, ApiNotAvailable
from .utils import log


class MessageSegment(BaseMessageSegment):
    """
    CQHTTP 协议 MessageSegment 适配。具体方法参考协议消息段类型或源码。
    """

    @overrides(BaseMessageSegment)
    def __init__(self, type: str, msg: Dict[str, Any]) -> None:
        data = {
            "msgtype": type,
        }
        if msg:
            data.update(msg)
        super().__init__(type=type, data=data)

    @overrides(BaseMessageSegment)
    def __str__(self):
        msg_type = self.data["msgtype"]
        content = self.data.get(msg_type, "")
        return str(content)

    @overrides(BaseMessageSegment)
    def __add__(self, other) -> "Message":
        return Message(self) + other

    def at(self, mobileNumber):
        self.data.setdefault("at", {})
        self.data["at"].setdefault("atMobiles", [])
        self.data["at"]["atMobiles"].append(mobileNumber)

    def atAll(self, value):
        self.data.setdefault("at", {})
        self.data["at"]["isAtAll"] = value

    @staticmethod
    def text(text: str) -> "MessageSegment":
        return MessageSegment("text", {"text": {"content": text}})

    @staticmethod
    def markdown(title: str, text: str) -> "MessageSegment":
        return MessageSegment("markdown", {
            "markdown": {
                "title": title,
                "text": text,
            },
        })

    @staticmethod
    def actionCardSingleBtn(title: str, text: str, btnTitle: str,
                            btnUrl) -> "MessageSegment":
        return MessageSegment(
            "actionCard", {
                "actionCard": {
                    "title": title,
                    "text": text,
                    "singleTitle": btnTitle,
                    "singleURL": btnUrl
                }
            })

    @staticmethod
    def actionCardSingleMultiBtns(
        title: str,
        text: str,
        btns: list = [],
        hideAvatar: bool = False,
        btnOrientation: str = '1',
    ) -> "MessageSegment":
        """
        :参数:

            * ``btnOrientation``: 0：按钮竖直排列 1：按钮横向排列

            * ``btns``: [{ "title": title, "actionURL": actionURL }, ...]
        """
        return MessageSegment(
            "actionCard", {
                "actionCard": {
                    "title": title,
                    "text": text,
                    "hideAvatar": "1" if hideAvatar else "0",
                    "btnOrientation": btnOrientation,
                    "btns": btns
                }
            })

    @staticmethod
    def feedCard(links: list = [],) -> "MessageSegment":
        """
        :参数:

            * ``links``: [{ "title": xxx, "messageURL": xxx, "picURL": xxx }, ...]
        """
        return MessageSegment("feedCard", {"feedCard": {"links": links}})

    @staticmethod
    def empty() -> "MessageSegment":
        "不想回复消息到群里"
        return MessageSegment("empty")


class Message(BaseMessage):
    """
    钉钉 协议 Message 适配。
    """

    @staticmethod
    @overrides(BaseMessage)
    def _construct(msg: str) -> Iterable[MessageSegment]:
        yield MessageSegment("text", {"text": msg})
