import logging
import sys
import time
from pathlib import Path

import requests
from colorama import Fore, Style, init
from ruamel.yaml import YAML

import login
from course import CourseManager

init()
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

session = requests.Session()


def _config_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent


CONFIG_PATH = _config_dir() / "config.yaml"
ACCOUNT_FIELDS = ("loginName", "passWord", "token", "timestamp", "label", "nickName")
QR_LOGIN_NAME = "扫码登录用户"
QR_LOGIN_LABEL = "扫码登录"

DEFAULT_CONFIG_TEXT = """\
# 保密观自动化配置文件

# 课程 ID
course_packet_id: "312bc914-8e11-421b-b9bc-e900fe1a4e50"

# 多账号配置（字段：loginName 用户名 / passWord 密码 / token 登录令牌 / timestamp 保存时间 / label 备注 / nickName 昵称）
accounts:
  - loginName: "151xxxxxxxx"
    passWord: "xxxx"
    token: ""
    timestamp: 0
    label: "示例账号"
    nickName: ""
"""

_yaml = YAML()
_yaml.preserve_quotes = True
_yaml.indent(mapping=2, sequence=4, offset=2)


def _ensure_config():
    if not CONFIG_PATH.exists():
        CONFIG_PATH.write_text(DEFAULT_CONFIG_TEXT, encoding="utf-8")


def load_config():
    _ensure_config()
    with CONFIG_PATH.open("r", encoding="utf-8") as handle:
        data = _yaml.load(handle)
    return data if data is not None else {}


def save_config(data):
    with CONFIG_PATH.open("w", encoding="utf-8") as handle:
        _yaml.dump(data, handle)


def get_headers(token):
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Safari/537.36",
        "token": token,
        "authToken": token,
        "siteId": "95",
        "Content-Type": "application/json",
    }


def _normalize_account(item):
    if isinstance(item, dict):
        return {
            "loginName": item.get("loginName", ""),
            "passWord": item.get("passWord", ""),
            "token": item.get("token", "") or "",
            "timestamp": int(item.get("timestamp") or 0),
            "label": item.get("label", "") or "",
            "nickName": item.get("nickName", "") or "",
        }
    if isinstance(item, (list, tuple)):
        padded = list(item) + [""] * max(0, len(ACCOUNT_FIELDS) - len(item))
        row = dict(zip(ACCOUNT_FIELDS, padded[: len(ACCOUNT_FIELDS)]))
        row["timestamp"] = int(row["timestamp"] or 0)
        return row
    return {field: "" if field != "timestamp" else 0 for field in ACCOUNT_FIELDS}


def get_course_packet_id():
    return load_config().get("course_packet_id", "") or ""


def get_all_accounts():
    accounts = []
    for item in load_config().get("accounts") or []:
        account = _normalize_account(item)
        if account["loginName"]:
            accounts.append(account)
    return accounts


def get_account_by_name(login_name):
    for account in get_all_accounts():
        if account["loginName"] == login_name:
            return account
    return None


def write_accounts(accounts):
    data = load_config()
    data["accounts"] = [_normalize_account(account) for account in accounts]
    save_config(data)
    logging.info(f"{Fore.GREEN}账号信息已保存{Style.RESET_ALL}")


def save_course_packet_id(course_packet_id):
    course_packet_id = course_packet_id.strip()
    if not course_packet_id:
        raise ValueError("课程 ID 不能为空")
    data = load_config()
    data["course_packet_id"] = course_packet_id
    save_config(data)


def save_account(login_name, pass_word, token, label=None, nickname=None):
    accounts = get_all_accounts()
    for account in accounts:
        if account["loginName"] == login_name:
            account["passWord"] = pass_word
            account["token"] = token
            account["timestamp"] = int(time.time())
            if label is not None:
                account["label"] = label
            if nickname is not None:
                account["nickName"] = nickname
            write_accounts(accounts)
            return

    accounts.append(
        {
            "loginName": login_name,
            "passWord": pass_word,
            "token": token,
            "timestamp": int(time.time()),
            "label": label or "",
            "nickName": nickname or "",
        }
    )
    write_accounts(accounts)


def save_account_nickname(login_name, nickname):
    if not login_name or not nickname:
        return
    data = load_config()
    for item in data.get("accounts") or []:
        if isinstance(item, dict) and item.get("loginName") == login_name:
            if item.get("nickName") == nickname:
                return
            item["nickName"] = nickname
            save_config(data)
            return


def add_account(login_name, pass_word, label=""):
    accounts = get_all_accounts()
    for account in accounts:
        if account["loginName"] == login_name:
            account["passWord"] = pass_word
            account["token"] = ""
            account["timestamp"] = 0
            if label:
                account["label"] = label
            write_accounts(accounts)
            return

    accounts.append(
        {
            "loginName": login_name,
            "passWord": pass_word,
            "token": "",
            "timestamp": 0,
            "label": label or "",
            "nickName": "",
        }
    )
    write_accounts(accounts)


def delete_account(login_name):
    accounts = [account for account in get_all_accounts() if account["loginName"] != login_name]
    write_accounts(accounts)


def check_login(token):
    if not token:
        return False

    headers = get_headers(token)
    url = "https://www.baomi.org.cn/portal/main-api/checkToken.do"
    try:
        response = session.get(url, headers=headers).json()
        if response.get("result"):
            nickname = response["data"].get("nickName")
            return nickname or "未设定姓名"
    except Exception as e:
        logging.error(f"{Fore.RED}检查 token 失败: {e}{Style.RESET_ALL}")
    return False


def _is_valid_account(login_name, pass_word):
    return bool(login_name and pass_word and login_name != "xxxx" and pass_word != "xxxx")


def is_usable_account(account):
    login_name = account.get("loginName", "")
    pass_word = account.get("passWord", "")
    token = account.get("token", "")
    if not login_name:
        return False
    if token:
        return True
    return _is_valid_account(login_name, pass_word)


def get_display_accounts():
    return [account for account in get_all_accounts() if is_usable_account(account)]


def get_all_saved_accounts():
    return get_display_accounts()


def get_config_accounts():
    return [
        account
        for account in get_all_accounts()
        if _is_valid_account(account["loginName"], account["passWord"])
    ]


def login_with_saved_or_password(login_name, pass_word):
    account = get_account_by_name(login_name)
    if account and account.get("token") and check_login(account["token"]):
        print(f"{Fore.GREEN}使用已保存的 token 登录成功: {login_name}{Style.RESET_ALL}")
        pwd = pass_word or account.get("passWord", "")
        if pwd and account.get("passWord") != pwd:
            save_account(login_name, pwd, account["token"], account.get("label"))
        return login_name, pwd or account.get("passWord", ""), account["token"]

    if is_qr_account(login_name):
        raise RuntimeError("扫码账号 token 已失效，请重新扫码登录。")

    return perform_login(login_name, pass_word)


def select_saved_account():
    account_rows = []
    for account in get_all_accounts():
        login_name = account.get("loginName", "")
        token = account.get("token")
        if not login_name or not token:
            continue
        nickname = check_login(token)
        account_rows.append(
            {
                "loginName": login_name,
                "passWord": account.get("passWord", ""),
                "token": token,
                "valid": bool(nickname),
                "nickname": nickname if nickname else "已过期",
            }
        )

    if not account_rows:
        return None

    valid_rows = [row for row in account_rows if row["valid"]]
    if not valid_rows:
        print(f"{Fore.YELLOW}发现 {len(account_rows)} 个已配置账号，但 token 均已过期{Style.RESET_ALL}")
        return None

    if len(valid_rows) == 1:
        row = valid_rows[0]
        display_name = row["nickname"] if row["nickname"] != "未设定姓名" else row["loginName"]
        print(f"{Fore.YELLOW}发现可快速登录的账号: {row['loginName']} ({display_name}){Style.RESET_ALL}")
        choice = input(
            f"{Fore.CYAN}是否使用已保存的 token 登录? (直接回车使用，输入 n 跳过): {Style.RESET_ALL}"
        ).strip().lower()
        if choice == "n":
            return None
        return row["loginName"], row["passWord"], row["token"]

    print(f"{Fore.YELLOW}发现 {len(valid_rows)} 个 token 有效的账号:{Style.RESET_ALL}")
    for index, row in enumerate(valid_rows, start=1):
        display_name = row["nickname"] if row["nickname"] != "未设定姓名" else row["loginName"]
        print(f"  {index}. {row['loginName']} ({display_name})")

    choice = input(
        f"{Fore.CYAN}请选择账号编号 (直接回车或输入 n 跳过): {Style.RESET_ALL}"
    ).strip().lower()
    if choice in ("", "n"):
        return None

    try:
        index = int(choice) - 1
        if 0 <= index < len(valid_rows):
            row = valid_rows[index]
            return row["loginName"], row["passWord"], row["token"]
    except ValueError:
        pass

    print(f"{Fore.RED}无效的账号编号{Style.RESET_ALL}")
    return None


def select_config_account():
    accounts = get_config_accounts()
    if not accounts:
        return None

    if len(accounts) == 1:
        account = accounts[0]
        display_name = account["label"] or account["loginName"]
        print(f"{Fore.YELLOW}检测到 config.yaml 中已配置账号: {display_name}{Style.RESET_ALL}")
        choice = input(
            f"{Fore.CYAN}是否使用该账号登录? (直接回车使用，输入 n 跳过): {Style.RESET_ALL}"
        ).strip().lower()
        if choice == "n":
            return None
        return account["loginName"], account["passWord"]

    print(f"{Fore.YELLOW}检测到 config.yaml 中已配置 {len(accounts)} 个账号:{Style.RESET_ALL}")
    for index, account in enumerate(accounts, start=1):
        display_name = account["label"] or account["loginName"]
        print(f"  {index}. {display_name} ({account['loginName']})")

    choice = input(
        f"{Fore.CYAN}请选择账号编号 (直接回车或输入 n 跳过): {Style.RESET_ALL}"
    ).strip().lower()
    if choice in ("", "n"):
        return None

    try:
        index = int(choice) - 1
        if 0 <= index < len(accounts):
            account = accounts[index]
            return account["loginName"], account["passWord"]
    except ValueError:
        pass

    print(f"{Fore.RED}无效的账号编号{Style.RESET_ALL}")
    return None


def is_qr_account(login_name):
    return login_name == QR_LOGIN_NAME


def perform_qr_login_with_token(token):
    save_account(QR_LOGIN_NAME, "", token, QR_LOGIN_LABEL)
    print(f"{Fore.GREEN}已自动保存扫码登录凭证{Style.RESET_ALL}")
    return QR_LOGIN_NAME, "", token


def perform_qr_login():
    token = login.qr_login()
    print(f"{Fore.GREEN}扫码登录成功{Style.RESET_ALL}")
    return perform_qr_login_with_token(token)


def perform_login(login_name, pass_word, label=None):
    token = login.login(login_name, pass_word)
    print(f"{Fore.GREEN}登录成功，已获取 token{Style.RESET_ALL}")
    save_account(login_name, pass_word, token, label)
    print(f"{Fore.GREEN}已自动保存{Style.RESET_ALL}")
    return login_name, pass_word, token


def prompt_manual_login():
    login_name = input(f"{Fore.CYAN}请输入用户名: {Style.RESET_ALL}")
    pass_word = input(f"{Fore.CYAN}请输入密码: {Style.RESET_ALL}")
    return perform_login(login_name, pass_word)


def select_login_method():
    while True:
        print(f"{Fore.CYAN}请选择登录方式{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}1. 扫码登录{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}2. 账号密码登录{Style.RESET_ALL}")
        choice = input(f"{Fore.CYAN}请选择 (1/2): {Style.RESET_ALL}").strip()

        if choice == "1":
            try:
                return perform_qr_login()
            except KeyboardInterrupt:
                print(f"\n{Fore.YELLOW}已取消扫码登录{Style.RESET_ALL}")
            except Exception as e:
                print(f"{Fore.RED}扫码登录失败: {e}{Style.RESET_ALL}")
            continue

        if choice == "2":
            try:
                return prompt_manual_login()
            except Exception as e:
                print(f"{Fore.RED}登录失败: {e}{Style.RESET_ALL}")
            continue

        print(f"{Fore.RED}无效的选择，请重试{Style.RESET_ALL}")


def get_user_credentials():
    saved_creds = select_saved_account()
    if saved_creds:
        login_name, pass_word, token = saved_creds
        print(f"{Fore.GREEN}使用已保存的 token 登录成功{Style.RESET_ALL}")
        return login_name, pass_word, token

    config_creds = select_config_account()
    if config_creds:
        login_name, pass_word = config_creds
        try:
            return login_with_saved_or_password(login_name, pass_word)
        except Exception as e:
            print(f"{Fore.RED}登录失败: {e}{Style.RESET_ALL}")

    return select_login_method()


def display_course_menu():
    print(f"\n{Fore.CYAN}============ 课程管理菜单 ============{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}1. 查看课程目录{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}2. 查看课程进度{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}3. 开始学习课程{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}4. 完成课程考试{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}0. 退出程序{Style.RESET_ALL}")
    return input(f"\n{Fore.CYAN}请选择操作 (0-4): {Style.RESET_ALL}")


def handle_course_menu(course_manager, course_packet_id):
    while True:
        choice = display_course_menu()

        if choice == "0":
            print(f"\n{Fore.GREEN}感谢使用，再见！{Style.RESET_ALL}")
            break
        if choice == "1":
            course_info = course_manager.get_course_info(course_packet_id)
            if course_info and course_info.get("data"):
                print(f"\n{Fore.GREEN}当前课程: {course_info['data']['name']}{Style.RESET_ALL}")
                print(f"课程说明: {course_info['data']['note']}")

                directory = course_manager.get_course_directory(course_packet_id)
                if directory and directory.get("data"):
                    print(f"\n{Fore.CYAN}课程目录:{Style.RESET_ALL}")
                    for section in directory["data"]:
                        print(f"\n{Fore.YELLOW}{section['name']}{Style.RESET_ALL}")
                        for sub in section["subDirectory"]:
                            print(f"  - {sub['name']}")
        elif choice == "2":
            progress = course_manager.get_course_progress(course_packet_id)
            if progress and progress.get("data"):
                data = progress["data"]
                print(f"\n{Fore.CYAN}课程进度信息:{Style.RESET_ALL}")
                print(f"课程名称: {data['courseName']}")
                print(f"学习进度: {data['progressRate'] * 100:.1f}%")
                print(f"已学课程数: {data['studyResourceNum']}/{data['resourceSum']}")
                print(f"总学习时长: {data['totalStudyTime']} 秒")
                print(f"是否完成: {'是' if data['isFinish'] else '否'}")
                print(f"是否获得证书: {'是' if data['isCertificate'] else '否'}")
        elif choice == "3":
            print(f"\n{Fore.CYAN}开始自动学习课程...{Style.RESET_ALL}")
            if course_manager.study_course(course_packet_id):
                print(f"\n{Fore.GREEN}课程学习完成！{Style.RESET_ALL}")
            else:
                print(f"\n{Fore.RED}课程学习失败，请稍后重试{Style.RESET_ALL}")
        elif choice == "4":
            print(f"\n{Fore.CYAN}开始自动完成考试...{Style.RESET_ALL}")
            if course_manager.complete_exam(course_packet_id):
                print(f"\n{Fore.GREEN}考试完成！{Style.RESET_ALL}")
            else:
                print(f"\n{Fore.RED}考试完成失败，请稍后重试{Style.RESET_ALL}")
        else:
            print(f"\n{Fore.RED}无效的选择，请重试{Style.RESET_ALL}")


if __name__ == "__main__":
    print(f"{Fore.CYAN}============ 保密教育登录程序 ============{Style.RESET_ALL}")
    login_name, pass_word, token = get_user_credentials()

    nickname = check_login(token)
    if nickname:
        print(f"{Fore.GREEN}登录成功! 欢迎, {nickname}{Style.RESET_ALL}")
        course_manager = CourseManager(session, token)
        handle_course_menu(course_manager, get_course_packet_id())
    else:
        print(f"{Fore.RED}登录失败或 token 无效{Style.RESET_ALL}")
