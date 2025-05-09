# AutoBaomiGuan
[保密观](https://www.baomi.org.cn) 自动刷课，答题脚本

> [!IMPORTANT] 
> 此脚本适用于 [2025年度全国保密教育线上培训](https://www.baomi.org.cn/bmCourseDetail/info?id=21c7d935-dd53-49d2-a95f-dc0f3e14ced7)

## 使用方法
1. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```
2. 编辑`config.py`文件，填入你的用户名、密码
3. 运行`main.py`，在菜单中选择需要的功能：
   - 选择 1: 自动刷课视频
   - 选择 2: 自动完成考试
   - 选择 3: 退出程序

## 配置说明
配置文件`config.py`包含以下设置：
- `loginName`: 登录用户名
- `passWord`: 登录密码
- `course_packet_id`: 课程ID，默认为2025年度保密教育线上培训

## 致谢
感谢 [https://github.com/NB-XX/AutoBaomiGuan](https://github.com/NB-XX/AutoBaomiGuan) 项目