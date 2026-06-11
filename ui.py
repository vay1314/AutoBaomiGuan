import io
import logging
import queue
import re
import threading
import time
import tkinter as tk
from contextlib import redirect_stdout
from tkinter import messagebox, ttk

import config
import main as cli
from course import CourseManager


ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


def clean_log_text(text):
    return ANSI_ESCAPE_RE.sub("", str(text))


class QueueLogHandler(logging.Handler):
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        self.log_queue.put(clean_log_text(self.format(record)))


class TextRedirector(io.StringIO):
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue

    def write(self, text):
        text = clean_log_text(text).strip()
        if text:
            self.log_queue.put(text)
        return len(text)

    def flush(self):
        return None


class AutoBaomiGuanUI:
    def __init__(self, root):
        self.root = root
        self.root.title("小工具")
        self.root.geometry("920x640")
        self.root.minsize(820, 560)

        self.log_queue = queue.Queue()
        self.accounts = []
        self.current_login_name = ""
        self.current_password = ""
        self.current_token = ""
        self.course_manager = None
        self.busy = False
        self.refreshing_account_names = False

        self._install_log_handler()
        self._build_ui()
        self.refresh_accounts()
        self._poll_log_queue()

    def _install_log_handler(self):
        handler = QueueLogHandler(self.log_queue)
        handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        logging.getLogger().addHandler(handler)

    def _build_ui(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        main_frame = ttk.Frame(self.root, padding=12)
        main_frame.grid(row=0, column=0, sticky="nsew")
        main_frame.columnconfigure(0, weight=0, minsize=300)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(0, weight=1)

        left = ttk.Frame(main_frame)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        left.columnconfigure(0, weight=1)
        left.rowconfigure(1, weight=1)

        right = ttk.Frame(main_frame)
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(2, weight=1)

        ttk.Label(left, text="缓存账号", font=("", 12, "bold")).grid(row=0, column=0, sticky="w")
        self.account_list = tk.Listbox(left, height=10, activestyle="dotbox", exportselection=False)
        self.account_list.grid(row=1, column=0, sticky="nsew", pady=(8, 8))
        self.account_list.bind("<<ListboxSelect>>", self._on_account_selected)
        self.account_list.bind("<Button-3>", self._show_account_menu)

        self.account_menu = tk.Menu(self.root, tearoff=0)
        self.account_menu.add_command(label="删除账号", command=self.delete_selected_account)

        account_buttons = ttk.Frame(left)
        account_buttons.grid(row=2, column=0, sticky="ew")
        account_buttons.columnconfigure((0, 1, 2), weight=1)
        ttk.Button(account_buttons, text="刷新", command=self.refresh_accounts).grid(
            row=0, column=0, sticky="ew", padx=(0, 6)
        )
        ttk.Button(account_buttons, text="删除账号", command=self.delete_selected_account).grid(
            row=0, column=1, sticky="ew", padx=(0, 6)
        )
        ttk.Button(account_buttons, text="使用缓存登录", command=self.login_selected_account).grid(
            row=0, column=2, sticky="ew"
        )

        add_frame = ttk.LabelFrame(left, text="添加账号", padding=10)
        add_frame.grid(row=3, column=0, sticky="ew", pady=(14, 0))
        add_frame.columnconfigure(1, weight=1)

        ttk.Label(add_frame, text="用户名").grid(row=0, column=0, sticky="w", pady=(0, 8))
        self.login_name_var = tk.StringVar()
        ttk.Entry(add_frame, textvariable=self.login_name_var).grid(
            row=0, column=1, sticky="ew", pady=(0, 8)
        )

        ttk.Label(add_frame, text="密码").grid(row=1, column=0, sticky="w", pady=(0, 8))
        self.password_var = tk.StringVar()
        ttk.Entry(add_frame, textvariable=self.password_var).grid(
            row=1, column=1, sticky="ew", pady=(0, 8)
        )

        ttk.Button(add_frame, text="添加并登录", command=self.login_new_account).grid(
            row=2, column=0, columnspan=2, sticky="ew"
        )

        status_frame = ttk.LabelFrame(right, text="当前状态", padding=10)
        status_frame.grid(row=0, column=0, sticky="ew")
        status_frame.columnconfigure(1, weight=1)

        self.status_var = tk.StringVar(value="未登录")
        self.course_var = tk.StringVar(value=config.course_packet_id)
        ttk.Label(status_frame, text="登录状态").grid(row=0, column=0, sticky="w", pady=(0, 8))
        self.status_label = tk.Label(
            status_frame,
            textvariable=self.status_var,
            anchor="w",
            padx=8,
            pady=2,
            bg="#dc2626",
            fg="white",
        )
        self.status_label.grid(row=0, column=1, sticky="w", pady=(0, 8))
        ttk.Label(status_frame, text="课程 ID").grid(row=1, column=0, sticky="w")
        ttk.Entry(status_frame, textvariable=self.course_var).grid(row=1, column=1, sticky="ew")

        action_frame = ttk.Frame(right)
        action_frame.grid(row=1, column=0, sticky="ew", pady=(12, 12))
        action_frame.columnconfigure((0, 1, 2), weight=1)
        self.query_button = ttk.Button(action_frame, text="查询课程与进度", command=self.query_course)
        self.query_button.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.study_button = ttk.Button(action_frame, text="开始刷课", command=self.study_course)
        self.study_button.grid(row=0, column=1, sticky="ew", padx=(0, 8))
        self.exam_button = ttk.Button(action_frame, text="完成考试", command=self.complete_exam)
        self.exam_button.grid(row=0, column=2, sticky="ew")

        log_frame = ttk.LabelFrame(right, text="运行日志", padding=8)
        log_frame.grid(row=2, column=0, sticky="nsew")
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        log_container = ttk.Frame(log_frame)
        log_container.grid(row=0, column=0, sticky="nsew")
        log_container.columnconfigure(0, weight=1)
        log_container.rowconfigure(0, weight=1)

        self.log_text = tk.Text(log_container, wrap="word", height=18, state="disabled")
        self.log_text.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=scrollbar.set)
        ttk.Button(log_container, text="清空日志", command=self.clear_log).place(
            relx=1.0, rely=1.0, x=-18, y=-12, anchor="se"
        )

        self._set_actions_enabled(False)

    def refresh_accounts(self):
        self.accounts = cli.get_all_saved_accounts()
        self.account_list.delete(0, tk.END)
        for account in self.accounts:
            self.account_list.insert(tk.END, self._format_account_row(account))

        if not self.accounts:
            self.account_list.insert(tk.END, "暂无缓存账号，请在下方添加")
        elif not self.account_list.curselection():
            self.account_list.selection_set(0)
        self._log(f"已加载 {len(self.accounts)} 个缓存账号")
        self._set_busy_state()
        self._refresh_account_names_async()

    def _format_account_row(self, account):
        login_name = account.get("loginName", "")
        nickname = account.get("nickName") or account.get("nickname") or account.get("label")
        saved_time = account.get("timestamp")
        date_text = ""
        if saved_time:
            date_text = time.strftime("%Y-%m-%d %H:%M", time.localtime(saved_time))

        name_text = f"{login_name} ({nickname})" if nickname else login_name
        return f"{name_text} {date_text}".strip()

    def _refresh_account_names_async(self):
        if self.refreshing_account_names or not self.accounts:
            return

        accounts_to_check = [
            account
            for account in self.accounts
            if account.get("token") and not (account.get("nickName") or account.get("nickname"))
        ]
        if not accounts_to_check:
            return

        self.refreshing_account_names = True

        def worker():
            changed = False
            store = cli._load_credentials_store()
            for account in accounts_to_check:
                login_name = account.get("loginName")
                token = account.get("token")
                nickname = cli.check_login(token)
                if login_name and nickname:
                    store.setdefault(login_name, {}).update(account)
                    store[login_name]["nickName"] = nickname
                    changed = True
            if changed:
                cli._save_credentials_store(store)
            self.root.after(0, self._finish_account_name_refresh)

        threading.Thread(target=worker, daemon=True).start()

    def _finish_account_name_refresh(self):
        self.refreshing_account_names = False
        selected = self._selected_account_index()
        self.accounts = cli.get_all_saved_accounts()
        self.account_list.delete(0, tk.END)
        for account in self.accounts:
            self.account_list.insert(tk.END, self._format_account_row(account))
        if self.accounts:
            index = selected if selected is not None and selected < len(self.accounts) else 0
            self.account_list.selection_set(index)
        self._set_busy_state()

    def _on_account_selected(self, _event=None):
        if not self.accounts:
            return
        index = self._selected_account_index()
        if index is None:
            return
        self._set_busy_state()

    def _selected_account_index(self):
        selected = self.account_list.curselection()
        if not selected:
            return None
        index = selected[0]
        if index >= len(self.accounts):
            return None
        return index

    def _show_account_menu(self, event):
        index = self.account_list.nearest(event.y)
        if 0 <= index < len(self.accounts):
            self.account_list.selection_clear(0, tk.END)
            self.account_list.selection_set(index)
            self.account_list.activate(index)
            self._on_account_selected()
            self.account_menu.tk_popup(event.x_root, event.y_root)

    def delete_selected_account(self):
        index = self._selected_account_index()
        if index is None:
            messagebox.showwarning("请选择账号", "请先选择要删除的缓存账号。")
            return

        account = self.accounts[index]
        login_name = account.get("loginName", "")
        if not login_name:
            return
        if not messagebox.askyesno("确认删除", f"确定删除缓存账号 {login_name} 吗？"):
            return

        store = cli._load_credentials_store()
        if login_name in store:
            del store[login_name]
            cli._save_credentials_store(store)

        if self.current_login_name == login_name:
            self.current_login_name = ""
            self.current_password = ""
            self.current_token = ""
            self.course_manager = None
            self._set_login_status(False)

        self._log(f"已删除缓存账号：{login_name}")
        self.refresh_accounts()

    def login_selected_account(self):
        index = self._selected_account_index()
        if index is None:
            messagebox.showwarning("请选择账号", "请先选择一个缓存账号。")
            return
        account = self.accounts[index]
        login_name = account.get("loginName", "")
        password = account.get("passWord", "")
        token = account.get("token", "")

        def work():
            if token and cli.check_login(token):
                return login_name, password, token
            if not password:
                raise RuntimeError("缓存 token 已失效，且没有保存密码，请重新输入密码。")
            return cli.login_with_saved_or_password(login_name, password)

        self._run_task("正在使用缓存账号登录...", work, self._after_login)

    def login_new_account(self):
        login_name = self.login_name_var.get().strip()
        password = self.password_var.get().strip()
        if not login_name or not password:
            messagebox.showwarning("请输入账号", "用户名和密码不能为空。")
            return

        def work():
            return cli.login_with_saved_or_password(login_name, password)

        self._run_task("正在添加账号并登录...", work, self._after_login)

    def _after_login(self, result):
        login_name, password, token = result
        self.current_login_name = login_name
        self.current_password = password
        self.current_token = token
        self.course_manager = CourseManager(cli.session, token)
        self._set_login_status(True, login_name)
        nickname = cli.check_login(token)
        if nickname:
            store = cli._load_credentials_store()
            store.setdefault(login_name, {}).update(
                {
                    "loginName": login_name,
                    "passWord": password,
                    "token": token,
                    "nickName": nickname,
                }
            )
            cli._save_credentials_store(store)
        self._set_actions_enabled(True)
        self.refresh_accounts()
        self.login_name_var.set("")
        self.password_var.set("")
        self._log("登录成功，可以查询课程或开始刷课")

    def query_course(self):
        course_packet_id = self.course_var.get().strip()
        if not course_packet_id:
            messagebox.showwarning("请输入课程 ID", "课程 ID 不能为空。")
            return

        def after_login():
            def work():
                info = self.course_manager.get_course_info(course_packet_id)
                progress = self.course_manager.get_course_progress(course_packet_id)
                return info, progress

            self._run_task("正在查询课程信息...", work, self._show_course_info)

        self._ensure_login_then(after_login)

    def _show_course_info(self, result):
        info, progress = result
        if info and info.get("data"):
            data = info["data"]
            self._log(f"课程名称：{data.get('name', '未知')}")
            note = data.get("note")
            if note:
                self._log(f"课程说明：{note}")
        else:
            self._log("课程信息查询失败")

        if progress and progress.get("data"):
            data = progress["data"]
            self._log(f"学习进度：{data.get('progressRate', 0) * 100:.1f}%")
            self._log(f"已学课程数：{data.get('studyResourceNum')}/{data.get('resourceSum')}")
            self._log(f"总学习时长：{data.get('totalStudyTime')} 秒")
            self._log(f"是否完成：{'是' if data.get('isFinish') else '否'}")
            self._log(f"是否获得证书：{'是' if data.get('isCertificate') else '否'}")
        else:
            self._log("课程进度查询失败")

    def study_course(self):
        course_packet_id = self.course_var.get().strip()
        if not course_packet_id:
            messagebox.showwarning("请输入课程 ID", "课程 ID 不能为空。")
            return
        if not messagebox.askyesno("确认刷课", "开始后会自动提交课程学习记录，是否继续？"):
            return

        def after_login():
            def work():
                redirector = TextRedirector(self.log_queue)
                with redirect_stdout(redirector):
                    return self.course_manager.study_course(course_packet_id)

            self._run_task("正在自动刷课...", work, self._after_study)

        self._ensure_login_then(after_login)

    def _after_study(self, success):
        if success:
            self._log("课程学习完成")
            messagebox.showinfo("完成", "课程学习完成。")
        else:
            self._log("课程学习失败，请查看日志")
            messagebox.showerror("失败", "课程学习失败，请查看日志。")

    def complete_exam(self):
        course_packet_id = self.course_var.get().strip()
        if not course_packet_id:
            messagebox.showwarning("请输入课程 ID", "课程 ID 不能为空。")
            return
        if not messagebox.askyesno("确认考试", "开始后会自动拉取试卷并提交答案，是否继续？"):
            return

        def after_login():
            def work():
                redirector = TextRedirector(self.log_queue)
                with redirect_stdout(redirector):
                    return self.course_manager.complete_exam(course_packet_id)

            self._run_task("正在自动完成考试...", work, self._after_exam)

        self._ensure_login_then(after_login)

    def _after_exam(self, success):
        if success:
            self._log("考试完成")
            messagebox.showinfo("完成", "考试完成。")
        else:
            self._log("考试失败，请查看日志")
            messagebox.showerror("失败", "考试失败，请查看日志。")

    def _ensure_login_then(self, callback):
        if self.course_manager:
            callback()
            return

        index = self._selected_account_index()
        if index is None:
            messagebox.showwarning("请先选择账号", "请先选择缓存账号，或添加账号并登录。")
            return

        account = self.accounts[index]
        login_name = account.get("loginName", "")
        password = account.get("passWord", "")
        token = account.get("token", "")

        def work():
            if token and cli.check_login(token):
                return login_name, password, token
            if not password:
                raise RuntimeError("缓存 token 已失效，且没有保存密码，请重新输入密码。")
            return cli.login_with_saved_or_password(login_name, password)

        def after(result):
            self._after_login(result)
            callback()

        self._run_task("正在自动登录所选账号...", work, after)

    def _require_login(self):
        if self.course_manager:
            return True
        messagebox.showwarning("请先登录", "请先选择缓存账号登录，或添加账号并登录。")
        return False

    def _run_task(self, start_message, worker, on_success=None):
        if self.busy:
            messagebox.showinfo("任务进行中", "当前已有任务正在执行，请等待完成。")
            return

        self.busy = True
        self._set_busy_state()
        self._log(start_message)

        def runner():
            try:
                result = worker()
            except Exception as exc:
                self.root.after(0, lambda: self._task_failed(exc))
                return
            self.root.after(0, lambda: self._task_finished(result, on_success))

        threading.Thread(target=runner, daemon=True).start()

    def _task_finished(self, result, on_success):
        self.busy = False
        self._set_busy_state()
        if on_success:
            on_success(result)

    def _task_failed(self, exc):
        self.busy = False
        self._set_busy_state()
        self._log(f"任务失败：{exc}")
        messagebox.showerror("任务失败", str(exc))

    def _set_busy_state(self):
        has_account = self._selected_account_index() is not None
        self._set_actions_enabled((bool(self.course_manager) or has_account) and not self.busy)

    def _set_actions_enabled(self, enabled):
        state = "normal" if enabled else "disabled"
        self.query_button.configure(state=state)
        self.study_button.configure(state=state)
        self.exam_button.configure(state=state)

    def _set_login_status(self, logged_in, login_name=""):
        if logged_in:
            self.status_var.set(f"已登录：{login_name}")
            self.status_label.configure(bg="#16a34a", fg="white")
        else:
            self.status_var.set("未登录")
            self.status_label.configure(bg="#dc2626", fg="white")

    def _log(self, message):
        self.log_queue.put(clean_log_text(message))

    def clear_log(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", tk.END)
        self.log_text.configure(state="disabled")

    def _poll_log_queue(self):
        while True:
            try:
                message = self.log_queue.get_nowait()
            except queue.Empty:
                break
            self.log_text.configure(state="normal")
            self.log_text.insert(tk.END, f"{message}\n")
            self.log_text.see(tk.END)
            self.log_text.configure(state="disabled")
        self.root.after(100, self._poll_log_queue)


def main():
    root = tk.Tk()
    app = AutoBaomiGuanUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
