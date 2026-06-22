import base64
import json
import logging
import time

import requests
from colorama import Fore, Style
from Crypto.Cipher import PKCS1_v1_5
from Crypto.PublicKey import RSA

QR_TOKEN_URL = "https://www.baomi.org.cn/portal/main-api/v2/spc/getQrToken.do"
QR_CHECK_URL = "https://www.baomi.org.cn/portal/api/v2/spc/checkQrToken.do"


def rsa_encrypt_pkcs1v15(data: str, public_key: str) -> str:
    if not public_key.strip().startswith("-----BEGIN"):
        public_key = f"""-----BEGIN PUBLIC KEY-----
{public_key.strip()}
-----END PUBLIC KEY-----"""

    try:
        key = RSA.import_key(public_key)
        cipher = PKCS1_v1_5.new(key)
        encrypted_bytes = cipher.encrypt(data.encode())
        return base64.b64encode(encrypted_bytes).decode()
    except (ValueError, IndexError, TypeError) as e:
        raise ValueError("无效的公钥格式") from e


def encrypt(data):
    try:
        key_url = "https://www.baomi.org.cn/portal/main-api/getPublishKey.do"
        response = requests.get(key_url)
        if response.status_code != 200:
            logging.error(f"{Fore.RED}获取公钥失败，状态码: {response.status_code}{Style.RESET_ALL}")
            return None

        public_key = response.json()["data"]
        return rsa_encrypt_pkcs1v15(data, public_key)
    except Exception as e:
        logging.error(f"{Fore.RED}加密过程出错: {e}{Style.RESET_ALL}")
        raise Exception(f"加密数据失败: {e}") from e


def parse_qr_token(qr_payload: str) -> str:
    try:
        payload = json.loads(qr_payload)
        qr_token = payload["params"]["qrToken"]
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        raise ValueError("二维码内容缺少 qrToken") from e

    if not qr_token:
        raise ValueError("二维码内容缺少 qrToken")

    return qr_token


def get_qr_code():
    response = requests.post(QR_TOKEN_URL, headers={"siteId": "95"})
    if response.status_code != 200:
        raise Exception(f"获取二维码失败，状态码: {response.status_code}")

    response_data = response.json()
    try:
        qr_content = response_data["data"]["data"]
    except (KeyError, TypeError) as e:
        raise ValueError("二维码接口返回格式异常") from e

    return qr_content, parse_qr_token(qr_content)


def check_qr_login(qr_token: str) -> int:
    response = requests.post(QR_CHECK_URL, params={"qrToken": qr_token})
    if response.status_code != 200:
        raise Exception(f"检查二维码登录状态失败，状态码: {response.status_code}")

    response_data = response.json()
    try:
        return int(response_data["data"]["data"])
    except (KeyError, TypeError, ValueError) as e:
        raise ValueError("二维码登录状态接口返回格式异常") from e


def print_terminal_qr(qr_content: str) -> None:
    try:
        import qrcode
    except ImportError as e:
        raise RuntimeError("缺少 qrcode 依赖，请运行 pip install -r requirements.txt") from e

    qr = qrcode.QRCode(border=2)
    qr.add_data(qr_content)
    qr.make(fit=True)
    qr.print_ascii(invert=True)


def make_qr_image(qr_content: str):
    try:
        import qrcode
    except ImportError as e:
        raise RuntimeError("缺少 qrcode 依赖，请运行 pip install -r requirements.txt") from e

    qr = qrcode.QRCode(border=2, box_size=6)
    qr.add_data(qr_content)
    qr.make(fit=True)
    return qr.make_image(fill_color="black", back_color="white")


def qr_login(poll_interval: int = 3, cancelled=None) -> str:
    qr_content, qr_token = get_qr_code()
    print(f"{Fore.CYAN}请使用保密观 APP 扫描下方二维码登录{Style.RESET_ALL}")
    print_terminal_qr(qr_content)

    while True:
        if cancelled and cancelled():
            raise KeyboardInterrupt("已取消扫码登录")

        try:
            status = check_qr_login(qr_token)
        except Exception as e:
            logging.error(f"{Fore.RED}检查二维码登录状态失败: {e}{Style.RESET_ALL}")
            time.sleep(poll_interval)
            continue

        if status == 1:
            print(f"{Fore.GREEN}扫码登录成功{Style.RESET_ALL}")
            return qr_token

        if status == -1:
            print(f"{Fore.YELLOW}二维码已失效，正在刷新...{Style.RESET_ALL}")
            qr_content, qr_token = get_qr_code()
            print_terminal_qr(qr_content)
            continue

        time.sleep(poll_interval)


def login(loginName, passWord):
    try:
        login_url = "https://www.baomi.org.cn/portal/main-api/loginInNew.do"
        payload = {
            "loginName": encrypt(loginName),
            "passWord": encrypt(passWord),
            "deviceId": 1711,
            "deviceOs": "pc",
            "lon": 40,
            "lat": 30,
            "siteId": "95",
            "sinopec": "false",
        }

        headers = {
            "Content-Type": "application/json",
            "siteId": "95",
        }
        response = requests.post(login_url, json=payload, headers=headers)
        if response.status_code != 200:
            logging.error(f"{Fore.RED}登录请求失败，状态码: {response.status_code}{Style.RESET_ALL}")
            raise Exception(f"登录请求失败，状态码: {response.status_code}")

        response_data = response.json()
        if "token" not in response_data:
            error_msg = response_data.get("message", "未知错误")
            logging.error(f"{Fore.RED}登录失败: {error_msg}{Style.RESET_ALL}")
            raise Exception(f"登录失败: {error_msg}")

        return response_data["token"]
    except Exception as e:
        logging.error(f"{Fore.RED}登录过程出错: {e}{Style.RESET_ALL}")
        raise
