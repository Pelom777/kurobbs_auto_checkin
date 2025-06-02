import os

import requests
from loguru import logger
from serverchan_sdk import sc_send

class WeComMessenger:
    def __init__(self, wecom_corpid, wecom_secret, wecom_agentid, wecom_to_user):
        self.wecom_corpid = wecom_corpid
        self.wecom_secret = wecom_secret
        self.wecom_agentid = wecom_agentid
        self.wecom_to_user = wecom_to_user
        self.token = self._refresh_token()

    def _refresh_token(self):
        token_url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={self.wecom_corpid}&corpsecret={self.wecom_secret}"
        resp = requests.get(token_url).json()
        if resp.get("errcode") == 0:
            return resp["access_token"]
        logger.debug(f"WeCom Token获取失败: {resp.get('errmsg')}")
        return None

    def send_message(self, content, msg_type="text"):
        if not self.token:
            logger.debug("WeCom token 不存在，跳过微信推送。")
            return
        url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={self.token}"
        payload = {
            "touser": self.wecom_to_user,
            "msgtype": msg_type,
            "agentid": self.wecom_agentid,
            msg_type: {"content": content},
        }
        response = requests.post(url, json=payload).json()
        if response.get("errcode") == 42001:  # token过期
            self.token = self._refresh_token()
            return self.send_message(content, msg_type)
        logger.debug(f"WeCom推送结果: {response}")
        return response


def send_notification(message):
    title = "库街区自动签到任务"
    send_bark_notification(title, message)
    send_server3_notification(title, message)
    send_wecom_notification(title, message)


def send_wecom_notification(title, message):
    """企业微信推送"""
    wecom_corpid = os.getenv("WECOM_CORPID")
    wecom_secret = os.getenv("WECOM_SECRET")
    wecom_agentid = os.getenv("WECOM_AGENTID")
    wecom_to_user = os.getenv("WECOM_TO_USER", "@all")
    if wecom_corpid and wecom_secret and wecom_agentid:
        try:
            messenger = WeComMessenger(wecom_corpid, wecom_secret, wecom_agentid, wecom_to_user)
            messenger.send_message(f"{title}\n{message}", "text")
        except Exception as e:
            logger.debug(f"WeCom消息推送异常: {e}")


def send_bark_notification(title, message):
    """Send a notification via Bark."""
    bark_device_key = os.getenv("BARK_DEVICE_KEY")
    bark_server_url = os.getenv("BARK_SERVER_URL")

    if not bark_device_key or not bark_server_url:
        logger.debug("Bark secrets are not set. Skipping notification.")
        return

    # 构造 Bark API URL
    url = f"{bark_server_url}/{bark_device_key}/{title}/{message}"
    try:
        requests.get(url)
    except Exception:
        pass


def send_server3_notification(title, message):
    server3_send_key = os.getenv("SERVER3_SEND_KEY")
    if server3_send_key:
        response = sc_send(server3_send_key, title, message, {"tags": "Github Action|库街区"})
        logger.debug(response)
    else:
        logger.debug("ServerChan3 send key not exists.")
