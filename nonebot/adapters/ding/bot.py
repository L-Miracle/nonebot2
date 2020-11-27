import re

import httpx

from nonebot.log import logger
from nonebot.config import Config
from nonebot.message import handle_event
from nonebot.typing import overrides, Driver, WebSocket, NoReturn
from nonebot.typing import Any, Dict, Union, Tuple, Iterable, Optional
from nonebot.adapters import BaseBot, BaseEvent, BaseMessage, BaseMessageSegment
from nonebot.exception import ApiError, NetworkError, ActionFailed, RequestDenied, ApiNotAvailable
from .utils import check_legal, log
from .event import Event
from .message import Message, MessageSegment


class Bot(BaseBot):
    """
    钉钉 协议 Bot 适配。继承属性参考 `BaseBot <./#class-basebot>`_ 。
    """

    def __init__(self,
                 driver: Driver,
                 connection_type: str,
                 config: Config,
                 self_id: str,
                 *,
                 websocket: Optional[WebSocket] = None):

        super().__init__(driver,
                         connection_type,
                         config,
                         self_id,
                         websocket=websocket)

    @property
    @overrides(BaseBot)
    def type(self) -> str:
        """
        - 返回: ``"cqhttp"``
        """
        return "ding"

    @classmethod
    @overrides(BaseBot)
    async def check_permission(cls, driver: Driver, connection_type: str,
                               headers: dict,
                               body: Optional[dict]) -> Union[str, NoReturn]:
        """
        :说明:
          钉钉协议鉴权。参考 `鉴权 <https://ding-doc.dingtalk.com/doc#/serverapi2/elzz1p>`_
        """
        timestamp = headers.get("timestamp")
        sign = headers.get("sign")
        log("DEBUG", "headers: {}".format(headers))
        log("DEBUG", "body: {}".format(body))

        # 检查 timestamp
        if not timestamp:
            log("WARNING", "Missing `timestamp` Header")
            raise RequestDenied(400, "Missing `timestamp` Header")
        # 检查 sign
        if not sign:
            log("WARNING", "Missing `sign` Header")
            raise RequestDenied(400, "Missing `sign` Header")
        # 校验 sign 和 timestamp，判断是否是来自钉钉的合法请求
        if not check_legal(timestamp, sign, driver):
            log("WARNING", "Signature Header is invalid")
            raise RequestDenied(403, "Signature is invalid")
        # 检查连接方式
        if connection_type not in ["http"]:
            log("WARNING", "Unsupported connection type")
            raise RequestDenied(405, "Unsupported connection type")

        access_token = driver.config.access_token
        if access_token and access_token != access_token:
            log(
                "WARNING", "Authorization Header is invalid"
                if access_token else "Missing Authorization Header")
            raise RequestDenied(
                403, "Authorization Header is invalid"
                if access_token else "Missing Authorization Header")
        return body.get("chatbotUserId")

    @overrides(BaseBot)
    async def handle_message(self, message: dict):
        """
        :说明:

          调用 `_check_reply <#async-check-reply-bot-event>`_, `_check_at_me <#check-at-me-bot-event>`_, `_check_nickname <#check-nickname-bot-event>`_ 处理事件并转换为 `Event <#class-event>`_
        """
        if not message:
            return
        log("DEBUG", "message: {}".format(message))

        try:
            event = Event(message)
            await handle_event(self, event)
        except Exception as e:
            logger.opt(colors=True, exception=e).error(
                f"<r><bg #f8bbd0>Failed to handle event. Raw: {message}</bg #f8bbd0></r>"
            )
        return

    @overrides(BaseBot)
    async def call_api(self, api: str, **data) -> Union[Any, NoReturn]:
        """
        :说明:

          调用 CQHTTP 协议 API

        :参数:

          * ``api: str``: API 名称
          * ``**data: Any``: API 参数

        :返回:

          - ``Any``: API 调用返回数据

        :异常:

          - ``NetworkError``: 网络错误
          - ``ActionFailed``: API 调用失败
        """
        if "self_id" in data:
            self_id = data.pop("self_id")
            if self_id:
                bot = self.driver.bots[str(self_id)]
                return await bot.call_api(api, **data)

        log("DEBUG", f"Calling API <y>{api}</y>")

        if self.connection_type == "http" and api == "post_webhook":
            target = data.get("sessionWebhook")
            if not target:
                raise ApiNotAvailable

            headers = {}

            try:
                async with httpx.AsyncClient(headers=headers) as client:
                    response = await client.post(
                        target,
                        params={"access_token": self.config.access_token},
                        json=data["message"].data,
                        timeout=self.config.api_timeout)

                if 200 <= response.status_code < 300:
                    result = response.json()
                    if isinstance(result, dict):
                        if result.get("errcode") != 0:
                            raise ApiError(errcode=result.get("errcode"),
                                           errmsg=result.get("errmsg"))
                        return result
                raise NetworkError(f"HTTP request received unexpected "
                                   f"status code: {response.status_code}")
            except httpx.InvalidURL:
                raise NetworkError("API root url invalid")
            except httpx.HTTPError:
                raise NetworkError("HTTP request failed")

    @overrides(BaseBot)
    async def send(self,
                   event: "Event",
                   message: Union[str, "MessageSegment"],
                   at_sender: bool = False,
                   **kwargs) -> Union[Any, NoReturn]:
        """
        :说明:

          根据 ``event``  向触发事件的主体发送消息。

        :参数:

          * ``event: Event``: Event 对象
          * ``message: Union[str, MessageSegment]``: 要发送的消息
          * ``at_sender: bool``: 是否 @ 事件主体
          * ``**kwargs``: 覆盖默认参数

        :返回:

          - ``Any``: API 调用返回数据

        :异常:

          - ``ValueError``: 缺少 ``user_id``, ``group_id``
          - ``NetworkError``: 网络错误
          - ``ActionFailed``: API 调用失败
        """
        msg = message if isinstance(
            message, MessageSegment) else MessageSegment.text(message)

        at_sender = at_sender and bool(event.user_id)

        params = {"sessionWebhook": event.raw_event.get("sessionWebhook")}

        params.update(kwargs)

        if at_sender and event.detail_type != "friend":
            params["message"] = MessageSegment.at(params["user_id"]) + \
                MessageSegment.text(" ") + msg
        else:
            params["message"] = msg
        return await self.call_api("post_webhook", **params)
