import os
import sys
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
from zoneinfo import ZoneInfo

import requests
from loguru import logger
from pydantic import BaseModel, Field

from ext_notification import send_notification


class Response(BaseModel):
    code: int = Field(..., alias="code", description="返回值")
    msg: str = Field(..., alias="msg", description="提示信息")
    success: Optional[bool] = Field(None, alias="success", description="token有时才有")
    data: Optional[Any] = Field(None, alias="data", description="请求成功才有")


class KurobbsClientException(Exception):
    """Custom exception for Kurobbs client errors."""
    pass


class KurobbsClient:
    FIND_ROLE_LIST_API_URL = "https://api.kurobbs.com/user/role/findRoleList"
    SIGN_URL = "https://api.kurobbs.com/encourage/signIn/v2"
    USER_SIGN_URL = "https://api.kurobbs.com/user/signIn"

    def __init__(self, token: str):
        self.token = token
        self.result: Dict[str, str] = {}
        self.exceptions: List[Exception] = []

    def get_headers(self) -> Dict[str, str]:
        """Get the headers required for API requests."""
        return {
            "osversion": "h5",
            "devcode": "2fba3859fe9bfe9099f2696b8648c2c6",
            "countrycode": "CN",
            "ip": "10.0.2.233",
            "model": "2211133C",
            "source": "h5",
            "lang": "zh-Hans",
            "version": "1.0.9",
            "versioncode": "1090",
            "token": self.token,
            "content-type": "application/x-www-form-urlencoded; charset=utf-8",
            "accept-encoding": "gzip",
            "user-agent": "okhttp/3.10.0",
        }

    def make_request(self, url: str, data: Dict[str, Any]) -> Response:
        """Make a POST request to the specified URL with the given data."""
        headers = self.get_headers()
        response = requests.post(url, headers=headers, data=data)
        response.raise_for_status()
        res = Response.model_validate_json(response.content)
        logger.debug(res.model_dump_json(indent=2, exclude={"data"}))
        return res

    def validate_response(self, response: Response, action: str) -> Response:
        """Validate API response and raise a clear exception if the request failed."""
        if response.success is False or (response.success is None and response.code != 0):
            raise KurobbsClientException(f"{action}, {response.msg or '未知错误'}")
        return response

    def get_user_game_list(self, game_id: int) -> List[Dict[str, Any]]:
        """Get the list of games for the user."""
        data = {"gameId": game_id}
        res = self.make_request(self.FIND_ROLE_LIST_API_URL, data)
        self.validate_response(res, "获取游戏角色列表")
        if not isinstance(res.data, list) or not res.data:
            raise KurobbsClientException(
                "未获取到游戏角色列表，可能 token 已过期或无可用角色。"
            )
        return res.data

    def checkin(self) -> Response:
        """Perform the check-in operation."""
        user_game_list = self.get_user_game_list(3)

        # 获取北京时间（UTC+8）
        beijing_tz = ZoneInfo('Asia/Shanghai')
        beijing_time = datetime.now(beijing_tz)
        data = {
            "gameId": user_game_list[0].get("gameId", 2),
            "serverId": user_game_list[0].get("serverId", None),
            "roleId": user_game_list[0].get("roleId", 0),
            "userId": user_game_list[0].get("userId", 0),
            "reqMonth": f"{beijing_time.month:02d}",
        }
        return self.make_request(self.SIGN_URL, data)

    def sign_in(self) -> Response:
        """Perform the sign-in operation."""
        return self.make_request(self.USER_SIGN_URL, {"gameId": 2})

    def _process_sign_action(
            self,
            action_name: str,
            action_method: Callable[[], Response],
            success_message: str,
            failure_message: str,
    ):
        """
        Handle the common logic for sign-in actions.

        :param action_name: The name of the action (used to store the result).
        :param action_method: The method to call for the sign-in action.
        :param success_message: The message to log on success.
        :param failure_message: The message to log on failure.
        """
        resp = action_method()
        logger.debug(resp)
        self.validate_response(resp, failure_message)
        self.result[action_name] = success_message

    def start(self):
        """Start the sign-in process."""
        self._process_sign_action(
            action_name="checkin",
            action_method=self.checkin,
            success_message="签到奖励签到成功",
            failure_message="签到奖励签到失败",
        )

        self._process_sign_action(
            action_name="sign_in",
            action_method=self.sign_in,
            success_message="社区签到成功",
            failure_message="社区签到失败",
        )

        self._log()

    @property
    def msg(self):
        return ", ".join(self.result.values()) + "!"

    def _log(self):
        """Log the results and raise exceptions if any."""
        if msg := self.msg:
            logger.info(msg)
        if self.exceptions:
            raise KurobbsClientException("; ".join(map(str, self.exceptions)))


def configure_logger(debug: bool = False):
    """Configure the logger based on the debug mode."""
    logger.remove()  # Remove default logger configuration
    log_level = "DEBUG" if debug else "INFO"
    logger.add(sys.stdout, level=log_level)


def main():
    """Main function to handle command-line arguments and start the sign-in process."""
    token = os.getenv("TOKEN")
    if not token:
        message = "TOKEN 环境变量未设置，无法签到。"
        logger.error(message)
        send_notification(message)
        sys.exit(1)

    debug = os.getenv("DEBUG", "false").lower() in ("1", "true", "yes")
    configure_logger(debug=debug)

    try:
        kurobbs = KurobbsClient(token)
        kurobbs.start()
    except KurobbsClientException as e:
        logger.error(str(e), exc_info=False)
        send_notification(str(e))
        sys.exit(1)
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        send_notification(f"An unexpected error occurred: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
