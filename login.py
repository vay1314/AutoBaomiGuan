import requests
import rsa
import base64
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5

def encrypt(data):
    # 获取公钥
    key_url = 'https://www.baomi.org.cn/portal/main-api/getPublishKey.do'
    response = requests.get(key_url)
    public_key = response.json()['data']
    
    # 将Base64编码的公钥转换为PEM格式
    pem_key = "-----BEGIN PUBLIC KEY-----\n"
    # 每64个字符添加一个换行符
    for i in range(0, len(public_key), 64):
        pem_key += public_key[i:i+64] + "\n"
    pem_key += "-----END PUBLIC KEY-----"
    
    # 将PEM格式的公钥转换为RSA对象
    key = RSA.import_key(pem_key)
    # 创建加密器
    cipher = PKCS1_v1_5.new(key)
    # 加密数据
    encrypted_data = cipher.encrypt(data.encode())
    # 将加密后的数据转换为base64字符串
    return base64.b64encode(encrypted_data).decode()

def login(loginName, passWord):
    login_url = "https://www.baomi.org.cn/portal/main-api/loginInNew.do"
    payload = {
        "loginName": encrypt(loginName),
        "passWord": encrypt(passWord),
        "deviceId": 1711,
        "deviceOs": "pc",
        "lon": 40,
        "lat": 30,
        "siteId": "95",
        "sinopec": 'false'
    }

    response = requests.post(login_url, json=payload)
    token = response.json()['token']
    return token