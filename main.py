import requests
import time
import logging
from concurrent.futures import ThreadPoolExecutor
import json 
import time
import login
import config
import random

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 创建会话
session = requests.Session()

# 获取课程时长
def view_resource_details(token, resource_directory_id):
    timestamp = int(time.time())
    url = 'http://www.baomi.org.cn/portal/api/v2/coursePacket/viewResourceDetails'
    post_data = {
        'token': token,
        'resourceDirectoryId': resource_directory_id,
        'timestamps': timestamp
    }
    try:
        response = session.get(url, params=post_data, headers=headers)
        response.raise_for_status()  # 检查响应状态码
        data = response.json()['data']
        resource_length = data['resourceLength']
        resource_id = data['resourceID']
        display_order = data['displayOrder']
        logging.info(f"正在刷: {data['name']}")
        return resource_length, resource_id, display_order
    except requests.exceptions.RequestException as e:
        logging.error(f"获取课程时长失败: {e}")
        return None, None, None

# 传递观看时间
def save_course_package(course_id, resource_id, resource_directory_id, resource_length, study_length, study_time, display_order, token):
    url = 'http://www.baomi.org.cn/portal/api/v2/studyTime/saveCoursePackage.do'
    timestamp = int(time.time())
    post_data = {
        'courseId': course_id,
        'resourceId': resource_id,
        'resourceDirectoryId': resource_directory_id,
        'resourceLength': resource_length,
        'studyLength': study_length,
        'studyTime': study_time,
        'startTime': timestamp - int(resource_length),
        'resourceType': 1,
        'resourceLibId': 3,
        'token': token,
        'studyResourceId': display_order,
        'timestamps': timestamp
    }
    try:
        response = session.get(url, params=post_data, headers=headers)
        response.raise_for_status()  # 检查响应状态码
        message = response.json()['message']
        logging.info(message)
    except requests.exceptions.RequestException as e:
        logging.error(f"保存课程包失败: {e}")

# 自动完成考试
def save_exam_result():
    # 解析配置中的考试答案
    exam_results = json.loads(config.exam_result)
    
    # 获取期望的分数
    while True:
        try:
            target_score = int(input("满分 100分，90分以上为优秀， 60-89分为合格\n请输入期望的分数（0-100，每题4分,共25题）："))
            if 0 <= target_score <= 100 and target_score % 4 == 0:
                break
            else:
                print("\n分数必须是0-100之间的4的倍数！\n例如：92, 96, 100\n")
        except ValueError:
            print("请输入有效的数字！")
    
    # 计算需要答对的题目数量
    correct_count = target_score // 4
    
    # 随机选择要答对的题目
    all_questions = list(range(len(exam_results)))
    correct_questions = random.sample(all_questions, correct_count)
    
    # 修改答案
    for i, question in enumerate(exam_results):
        if i in correct_questions:
            # 答对的题目使用标准答案
            question['userAnswer'] = question['standardAnswer']
            question['userScoreRate'] = '100%'
        else:
            # 答错的题目根据题型选择错误答案
            if question['viewTypeId'] == 3:  # 判断题
                # 判断题只在A和B之间选择
                wrong_options = ['A', 'B']
                wrong_options.remove(question['standardAnswer'])
                question['userAnswer'] = wrong_options[0]
            else:  # 单选题
                # 单选题在A、B、C、D中选择
                wrong_options = ['A', 'B', 'C', 'D']
                wrong_options.remove(question['standardAnswer'])
                question['userAnswer'] = random.choice(wrong_options)
            question['userScoreRate'] = '0%'

        if 'parentId' not in question:
            question['parentId'] = '0'
        if 'resultFlag' not in question:
            question['resultFlag'] = 0
        if 'subCount' not in question:
            question['subCount'] = 0
    
    # 发送请求
    url = "https://www.baomi.org.cn/portal/main-api/v2/activity/exam/saveExamResultJc.do"
    payload = {
        "examId": config.exam_id,
        "examResult": json.dumps(exam_results),  # 将数组转换为JSON字符串
        "startDate": config.exam_start_date,
        "randomId": config.exam_random_id
    }
    response = requests.request("POST", url, headers=headers, json=payload)
    print(response.text)

def finish_exam(course_packet_id):
    url = f"https://www.baomi.org.cn/portal/main-api/v2/studyTime/updateCoursePackageExamInfo.do?courseId={course_packet_id}&orgId=&isExam=1&isCertificate=0&examResult=100"
    try:
        response = session.get(url, headers=headers)
        response.raise_for_status()  # 检查响应状态码
        message = response.json()['message']
        logging.info(message)
    except requests.exceptions.RequestException as e:
        logging.error(f"完成考试失败: {e}")

def process_video(course_packet_id, directory_id):
    timestamp = int(time.time())
    try:
        resource_directory_ids = session.get('http://www.baomi.org.cn/portal/api/v2/coursePacket/getCourseResourceList', params={'coursePacketId': course_packet_id, 'directoryId': directory_id, 'timestamps': timestamp}, headers=headers).json()['data']['listdata']
        for resource_info in resource_directory_ids:
            resource_directory_id = resource_info['SYS_UUID']
            directory_id = resource_info['directoryID']
            resource_length, resource_id, display_order = view_resource_details(token, resource_directory_id)
            if resource_length is not None:
                save_course_package(course_packet_id, resource_id, resource_directory_id, resource_length, 0, 180, display_order, token)
                save_course_package(course_packet_id, resource_id, resource_directory_id, resource_length, resource_length, resource_length, display_order, token)
    except requests.exceptions.RequestException as e:
        logging.error(f"处理视频失败: {e}")

# 刷课视频功能
def watch_videos():
    print("开始自动刷课视频...")
    course_packet_id = config.course_packet_id
    timestamp = int(time.time())

    try:
        directory_ids = session.get('http://www.baomi.org.cn/portal/api/v2/coursePacket/getCourseDirectoryList', params={'scale': 1, 'coursePacketId': course_packet_id, 'timestamps': timestamp}, headers=headers).json()['data']
        with ThreadPoolExecutor(max_workers=10) as executor:
            for directory in directory_ids:
                sub_directories = directory['subDirectory']
                for sub_dir in sub_directories:
                    executor.submit(process_video, course_packet_id, sub_dir['SYS_UUID'])
        print('视频观看完成!')
        # 获取并打印已获得学时
        user_info = get_user_info(token, course_packet_id)
        print(f"已获得学时: {user_info['totalGrade']}\n")
    except requests.exceptions.RequestException as e:
        logging.error(f"获取目录列表失败: {e}")

# 完成考试功能
def take_exam():
    print("开始完成考试...")
    course_packet_id = config.course_packet_id
    save_exam_result()
    finish_exam(course_packet_id)
    print("考试完成!")

# 获取用户信息
def get_user_info(token, course_packet_id):
    url = f"https://www.baomi.org.cn/portal/main-api/v2/coursePacket/getCourseUserStatistic?coursePacketId={course_packet_id}&token={token}"
    response = requests.get(url).json()
    return response['data']

if __name__ == '__main__':
    # 使用配置文件中的登录信息
    token = login.login(config.loginName, config.passWord)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Safari/537.36',
        'token': token,
        'Content-Type': 'application/json'
    }

    # 获取用户信息
    user_info = get_user_info(token, config.course_packet_id)
    
    print("\n===== 保密观自动化工具 =====")
    print(f"课程名称: {user_info['courseName']}")
    print(f"用户昵称: {user_info['loginName']}")
    print("=" * 30 + "\n")
    
    while True:
        print("请选择功能：")
        print("1. 自动刷课视频")
        print("2. 自动完成考试")
        print("3. 退出程序")
        
        choice = input("请选择操作 (1-3): ")
        
        if choice == '1':
            watch_videos()
        elif choice == '2':
            take_exam()
        elif choice == '3':
            print("程序已退出，感谢使用!")
            break
        else:
            print("无效选择，请重新输入!")
