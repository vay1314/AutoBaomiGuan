# AutoBaomiGuan

[保密观](https://www.baomi.org.cn) 自动刷课、答题脚本。

> [!IMPORTANT]
> 此脚本适用于 [2026 年度全国保密教育线上培训](https://www.baomi.org.cn/bmCourseDetail/info?id=312bc914-8e11-421b-b9bc-e900fe1a4e50)

## 功能

- 多账号登录，token 按账号分别缓存
- 查看课程目录与学习进度
- 自动完成视频课程学习
- 自动拉取试卷并提交答案（满分）

## 使用方法

1. 安装依赖：

   ```bash
   pip install -r requirements.txt
   ```

2. 编辑 `config.py`，配置课程 ID 与账号（也可留空，运行时手动输入）。

3. 运行程序：

   ```bash
   python main.py
   ```

4. 按提示登录后，在课程管理菜单中选择功能：

   | 选项 | 功能 |
   |------|------|
   | 1 | 查看课程目录 |
   | 2 | 查看课程进度 |
   | 3 | 开始学习课程（自动刷课） |
   | 4 | 完成课程考试（自动答题） |
   | 0 | 退出程序 |

## Windows UI 工具

Windows 下也可以使用图形界面运行：

```bash
python ui.py
```

或直接下载构建的AutoBaomiGuanUI.exe

界面截图：

![Windows UI](ScreenShot/ScreenShot.png)

## 登录说明

启动时按以下优先级尝试登录：

1. **已保存凭证**（`credentials.json`）  
   若存在有效 token，可直接回车使用；多个账号时输入编号选择；输入 `n` 跳过。

2. **config.py 中的账号**  
   优先使用该账号已缓存的 token；若 token 过期则用 config 中的密码重新登录。

3. **手动输入**  
   交互输入用户名和密码，登录成功后自动写入 `credentials.json`。

## 配置说明

`config.py` 主要字段：

| 字段 | 说明 |
|------|------|
| `course_packet_id` | 课程 ID，默认 2026 年度培训 |
| `accounts` | 多账号列表（推荐） |
| `CREDENTIALS_FILE` | 凭证缓存文件路径，默认 `credentials.json` |

多账号示例：

```python
accounts = [
    {"loginName": "13800138000", "passWord": "your_password", "label": "默认账号"},
    {"loginName": "13900139000", "passWord": "your_password", "label": "同事账号"},
]
```

- `label` 为可选备注，便于启动时识别账号。
- 账号密码也可不写入 config，留空后在运行时手动输入。

## 项目结构

```
├── config.py          # 配置文件
├── login.py           # 登录与 RSA 加密
├── course.py          # 课程与考试逻辑
├── main.py            # 程序入口
├── ui.py              # Windows 图形界面入口
├── ScreenShot/        # 界面截图
└── requirements.txt   # Python 依赖
```

## 致谢

感谢 [NB-XX/AutoBaomiGuan](https://github.com/NB-XX/AutoBaomiGuan) 项目。
