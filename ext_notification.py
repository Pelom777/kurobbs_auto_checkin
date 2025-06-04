import os

import requests
from loguru import logger
from serverchan_sdk import sc_send


def send_notification(message):
    title = "库街区自动签到任务"
    send_bark_notification(title, message)
    send_server3_notification(title, message)
    send_wecom_notification(title, message)


def send_wecom_notification(title, message):
    """企业微信推送"""
    wecom_api_url = os.getenv("WECOM_API_URL")
    wecom_to_user = os.getenv("WECOM_TO_USER")
    wecom_token = os.getenv("WECOM_TOKEN")
    logger.info(wecom_api_url and wecom_to_user and wecom_token)
    if wecom_api_url and wecom_to_user and wecom_token:
        payload = {
            "to_user": wecom_to_user,
            "msg": f"{title}\n{message}",
            "token": wecom_token
        }
        try:
            resp = requests.post(wecom_api_url, json=payload)
            logger.info(f"WeCom接口推送结果: {resp.text}")
        except Exception as e:
            logger.info(f"WeCom接口推送异常: {e}")


def send_bark_notification(title, message):
    """Send a notification via Bark."""
    bark_device_key = os.getenv("BARK_DEVICE_KEY")
    bark_server_url = os.getenv("BARK_SERVER_URL")

    if not bark_device_key or not bark_server_url:
        logger.info("Bark secrets are not set. Skipping notification.")
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
        logger.info(response)
    else:
        logger.info("ServerChan3 send key not exists.")
