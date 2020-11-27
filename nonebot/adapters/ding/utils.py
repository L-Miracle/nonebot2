import asyncio
import base64
import hashlib
import hmac
import sys

from nonebot.exception import (ActionFailed, NetworkError)
from nonebot.log import logger
from nonebot.typing import (Any, Dict, NoReturn, Optional, Union)


def log(level: str, message: str):
    """
    :说明:

      用于打印 钉钉 日志。

    :参数:

      * ``level: str``: 日志等级
      * ``message: str``: 日志信息
    """
    return logger.opt(colors=True).log(level, "<m>DING</m> | " + message)


def check_legal(timestamp, remote_sign, driver):
    """
    1. timestamp 与系统当前时间戳如果相差1小时以上，则认为是非法的请求。

    2. sign 与开发者自己计算的结果不一致，则认为是非法的请求。

    必须当timestamp和sign同时验证通过，才能认为是来自钉钉的合法请求。
    """
    app_secret = driver.config.secret  # 机器人的 appSecret
    app_secret_enc = app_secret.encode('utf-8')
    string_to_sign = '{}\n{}'.format(timestamp, app_secret)
    string_to_sign_enc = string_to_sign.encode('utf-8')
    hmac_code = hmac.new(app_secret_enc,
                         string_to_sign_enc,
                         digestmod=hashlib.sha256).digest()
    sign = base64.b64encode(hmac_code).decode('utf-8')
    return remote_sign == sign


def _handle_api_result(
        result: Optional[Dict[str, Any]]) -> Union[Any, NoReturn]:
    """
    :说明:

      处理 API 请求返回值。

    :参数:

      * ``result: Optional[Dict[str, Any]]``: API 返回数据

    :返回:

        - ``Any``: API 调用返回数据

    :异常:

        - ``ActionFailed``: API 调用失败
    """
    if isinstance(result, dict):
        if result.get("status") == "failed":
            raise ActionFailed(retcode=result.get("retcode"))
        return result.get("data")
