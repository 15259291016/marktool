import pandas as pd
import zipfile
import codecs
import json
import os
import time
import base64
import hmac
# from sqlalchemy import create_engine
from django.http import FileResponse
from django.http import JsonResponse, HttpResponse
from marktool.src.utils.mysql_handler import MySqlHandler
from marktool.src.utils.mysql_handler import config
from marktool.src.utils.logger import logger_running
from marktool.src.utils.safety import authorization
from marktool.src.utils.safety import get_remote_ip

mysql_handler = MySqlHandler()


def generate_token(username, expire=60*60*24*7):
    r'''
        @Args:
            username: str (用户给定的key，需要用户保存以便之后验证token,每次产生token时的key 都可以是同一个key)
            expire: int(最大有效时间，单位为s)
        @Return:
            state: str
    '''
    timestamp = time.time()
    ts_str = str(timestamp + expire)
    ts_byte = ts_str.encode("utf-8")
    sha1 = hmac.new((username + 'salt').encode("utf-8"),
                    ts_byte, 'sha1').hexdigest()
    token = {
        'username': username,
        'timestamp': ts_str,
        'token': sha1
    }
    b64_token = base64.urlsafe_b64encode(json.dumps(token).encode("utf-8"))
    # 转化成字符串
    return b64_token.decode("utf-8")


def certify_token(username, password, token, ip):
    r'''
        @Args:
            username: str
            token: str
        @Returns:
            boolean
    '''
    # 取数据库中这个用户
    user_info = mysql_handler.user_login_by_username(username)
    if user_info is None:
        return False
    # if password == user_info["password"]:
    if password == user_info.password:
        # 取这个用户的token
        db_user_token = user_info.token
        if db_user_token:
            db_user_token = json.loads(base64.urlsafe_b64decode(db_user_token).decode('utf-8'))['token']
        else:
            # 新用户
            db_user_token = None
        # ts_str = time.time()
        # 有账号 有密码 无数据库token 无上传token
        if db_user_token == None or token == None:
            token = generate_token(username)
            mysql_handler.write_user_token(username, token, ip)
            return {
                'username': user_info.username,
                'zh_name': user_info.zh_name,
                'token': token,
                'permission': user_info.permission
            }
        # 有账号 有密码 有数据库token
        elif db_user_token:
            mysql_handler.update_user_last_login_date(username)
            return {
                'username': user_info.username,
                'zh_name': user_info.zh_name,
                'token': user_info.token,
                'permission': user_info.permission
            }
    else:
        return False


def create_user(request):
    if request.method == 'GET':
        # ip = get_remote_ip(request)
        username = request.GET.get('username')
        password = request.GET.get('password')
        permission = int(request.GET.get('permission'))
        zh_name = request.GET.get('zh_name')

        status = mysql_handler.insert_user(
            username, password, permission, zh_name)
        if status == 1:
            return JsonResponse({
                'code': 200,
                'message': '创建成功'
            })
        else:
            return JsonResponse({
                'code': 200,
                'message': '创建失败'
            })

def update_user(request):
    if request.method == 'GET':
        # ip = get_remote_ip(request)
        username = request.GET.get('username')
        password = request.GET.get('password')
        permission = int(request.GET.get('permission'))
        zh_name = request.GET.get('zh_name')

        status = mysql_handler.update_user(
            username, password, permission, zh_name)
        if status == 1:
            return JsonResponse({
                'code': 200,
                'message': '修改成功'
            })
        else:
            return JsonResponse({
                'code': 200,
                'message': '修改失败'
            })


def get_users_info(request):
    if request.method == 'GET':
        # ip = get_remote_ip(request)
        zh_name = request.GET.get('zh_name')
        users = pd.read_sql("SELECT * FROM user", con=mysql_handler.driver)
        users['last_change_date'] = pd.to_datetime(users.last_change_date)
        if users[(users['zh_name'] == zh_name) & (users['permission'] >= 5)].shape[0] > 0:
            return JsonResponse({
                'code': 200,
                'data': users.sort_values('last_change_date').to_dict(orient='records'),
                'message': '请求成功'
            })
        else:
            return JsonResponse({
                'code': 200,
                'data': users[(users['zh_name'] == zh_name)].to_dict(orient='records'),
                'message': '请求成功'
            })


def get_user_info(request):
    if request.method == 'GET':
        # try:
        user, token = authorization(request)

        if user and token:
            username = user['username']
            timestamp = user['timestamp']
            token_ = user['token']
            user_info = mysql_handler.user_login_by_token(token)
        else:
            return JsonResponse({
                'code': 500,
                'content': '非法token',
                'message': 'login fault'
            })

        if user_info:
            # if float(timestamp) < time.time():
            #     return JsonResponse({
            #         'code': 302,
            #         'content': 'token过期',
            #         'message': 'login fault'
            #     })
            # else:

            if user_info.token == token:
                return JsonResponse({
                    'code': 200,
                    'content': {'username': user_info.username,
                                'permission': user_info.permission,
                                'zh_name': user_info.zh_name
                                },
                    'message': 'login success'
                })
            # if user_info['token'] == token:
            #     return JsonResponse({
            #         'code': 200,
            #         'content': {'username': user_info['username'],
            #                     'permission': user_info['permission'],
            #                     'zh_name': user_info['zh_name']
            #                     },
            #         'message': 'login success'
            #     })
            else:
                return JsonResponse({
                    'code': 500,
                    'content': '非法token',
                    'message': 'login fault'
                })
        else:
            return JsonResponse({
                'code': 500,
                'content': '非法token',
                'message': 'login fault'
            })
        # except Exception as e:
        #     return JsonResponse({
        #         'code': 500,
        #         'content': 'token 有问题' + str(e),
        #         'message': 'login fault'
        #     })


def login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        ip = get_remote_ip(request)
        token = request.POST.get('token')
        try:
            user, token = authorization(request)
        except Exception as e:
            logger_running.error(e)

            return JsonResponse({
                'code': 500,
                'content': 'token 有问题' + e,
                'message': 'login fault'
            })

        status = certify_token(username, password, token, ip)

        if status:
            return JsonResponse({
                'code': 200,
                'content': status,
                'message': 'login success'
            })
        else:
            return JsonResponse({
                'code': 201,
                'content': '账号或密码错误',
                'message': 'login fault'
            })
    return JsonResponse({
        'code': 201,
        'content': '账号或密码错误',
        'message': 'login fault'
    })


if __name__ == "__main__":
    pass
