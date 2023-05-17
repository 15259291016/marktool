import itertools
import time

import pandas as pd
import numpy as np
import zipfile
import codecs
import json
import re
import os
import glob
from datetime import datetime
from sqlalchemy import create_engine
from django.http import FileResponse
from django.http import JsonResponse, HttpResponse
from marktool.src.utils.mysql_handler import MySqlHandler
from marktool.src.utils.mysql_handler import config
from marktool.src.utils.logger import logger_running
from marktool.src.utils.safety import get_remote_ip
from marktool.src.utils.safety import authorization

mysql_handler = MySqlHandler()


def zip_files(files='./tmp/*.marktool'):
    zip = zipfile.ZipFile('./tmp/download.zip', 'w', zipfile.ZIP_DEFLATED)
    for file in glob.glob(files):
        logger_running.info(file)
        zip.write(file)
    zip.close()
    logger_running.info('数据压缩成功')


def response_data(data, marked='', category=[], code=200, message='success'):
    ret = {
        'code': code,
        'message': message,
        'data': data,
        # 已标注category统计
        'marked': marked,
        # 当前句子上一次标注category
        'category': category
    }
    return json.dumps(ret, ensure_ascii=False)


def dialogs2cqas(df):
    # df = pd.read_csv(input_path).fillna('')
    # print(df.shape)
    for mode in ['general', 'special', 'delete']:
        result = []
        if mode == 'general':
            df_ = df[df['label'] == '通用FAQ']
        elif mode == 'special':
            df_ = df[df['label'] == '个性FAQ']
        else:
            df_ = df[df['label'] == '删除FAQ']
        # print(df_.shape)
        ID = df_.uuid.tolist()
        context = df_.context.tolist()
        question = df_.question.tolist()
        answer = df_.answer.tolist()
        for id_, context, question, answer in zip(ID, context, question, answer):
            result.append('C' + str(id_) + '@@##$$：' + context + '\n')
            result.append('Q' + str(id_) + '@@##$$：' + question + '\n')
            result.append('A' + str(id_) + '@@##$$：' + answer + '\n')
            result.append('\n')
        if result:
            result.pop()

        codecs.open(r'./tmp/{}.marktool'.format(mode), 'w',
                    encoding='utf-8').writelines(result)
    return result

# 所有标注情况


def query_list(request):
    if request.method == 'GET':
        ip = get_remote_ip(request)

        pagesize = int(request.GET.get('pagesize'))
        currpage = int(request.GET.get('currpage'))
        # mclasseng = request.GET.get('mclasseng')
        df = mysql_handler.query_list(pagesize, currpage, ip)
        # logger_running.info('查询成功')
        # 合并结果
        return JsonResponse({
            'code': 200,
            'data': df.to_dict(orient='records'),
            'message': '请求成功'
        })


def return_file():
    response = FileResponse(open('./tmp/download.zip', 'rb'))
    response['Content-Type'] = 'application/octet-stream'
    response['Content-Disposition'] = 'attachment;filename="download.zip"'
    return response


def gen_filename(filename):
    if filename.count(',') > 1:
        pass
    else:
        return filename[1: -1]

# 下载单份文件


def download_cqa(filename):
    try:
        sql = 'select * from marktool where file in (%s)' % (filename)
        df = pd.read_sql(sql, mysql_handler.driver)
        dialogs2cqas(df)
        zip_files()
    except Exception as e:
        logger_running.error('download_file: '+str(e))
        return JsonResponse({'code': 500, 'content': '数据库查询出错', 'message': 'mysql error'})


def download_twotuples(filename):
    try:
        sql = 'select * from two_tuples where file in (%s)' % (filename)
        df = pd.read_sql(sql, mysql_handler.driver)

        if len(filename.split(',')) == 1:
            filename = filename[1:-1].split('.')[0]
            df[['uuid', 'sentence', 'label', 'ner', 'tuple']].to_excel(
                './tmp/{}.xlsx'.format(filename), index=False, engine='xlsxwriter')
            zip_files(files='./tmp/{}.xlsx'.format(filename))
            os.remove('./tmp/{}.xlsx'.format(filename))
        else:
            filename = 'select_data'
            df[['uuid', 'sentence', 'label', 'ner', 'tuple']].to_csv(
                './tmp/{}.csv'.format(filename), index=False)
            zip_files(files='./tmp/{}.csv'.format(filename))
            os.remove('./tmp/{}.csv'.format(filename))
    except Exception as e:
        logger_running.error('download_file: '+str(e) + ' sql: ' + sql)
        return JsonResponse({'code': 500, 'content': '数据库查询出错', 'message': 'mysql error'})


def download_classification(filename):
    try:
        if len(filename.split(',')) == 1:
            sql = 'select * from classification where file in (%s)' % (filename)
            df = pd.read_sql(sql, mysql_handler.driver)
            filename = filename[1:-1].split('.')[0]
            author = filename.split('_')[1]
            df["author"] = author
            df["filename"] = filename
            df[['uuid', 'sentence', 'label', 'author', 'filename']].to_excel(
                './tmp/{}.xlsx'.format(filename), index=False, engine='xlsxwriter')
            time.sleep(0.5)
            zip_files(files='./tmp/{}.xlsx'.format(filename))
            time.sleep(0.5)
            os.remove('./tmp/{}.xlsx'.format(filename))
        else:
            # 变量名字
            filename_ = 'select_data'
            for index in filename.split(','):
                sql = 'select * from classification where file in (%s)' % (index)
                author = index.split('_')[1]
                df = pd.read_sql(sql, mysql_handler.driver)
                df["author"] = author
                df["filename"] = index
                if not os.path.exists('./tmp/{}.csv'.format(filename_)):
                    df[['uuid', 'sentence', 'label', 'author', 'filename']].to_csv('./tmp/{}.csv'.format(filename_), mode='a',
                          index=False, index_label=False)
                else:
                    df[['uuid', 'sentence', 'label', 'author', 'filename']].to_csv('./tmp/{}.csv'.format(filename_), mode='a', header=False,
                                                                       index=False, index_label=False)
            zip_files(files='./tmp/{}.csv'.format(filename_))
            os.remove('./tmp/{}.csv'.format(filename_))
    except Exception as e:
        logger_running.error('download_file: '+str(e) + ' sql: ' + sql)
        return JsonResponse({'code': 500, 'content': '数据库查询出错', 'message': 'mysql error'})


def download_graph(filename):
    try:
        # 下载结果
        sql = 'select dialog_id, entity_value_relationship, file from entity_relationship where file in (%s)' % (
            filename)
        result = pd.read_sql(sql, mysql_handler.driver)
        # 下载对话
        sql = 'select dialog_id, sentence_id, role, sentence, entity, file from graph where file in (%s)' % (
            filename)
        dialog = pd.read_sql(sql, mysql_handler.driver)
        filename = filename[1:-1]
        result.to_excel('./tmp/{}.xlsx'.format(filename.split('.')
                                               [0] + 'result'), index=False, engine='xlsxwriter')
        dialog.to_excel('./tmp/{}.xlsx'.format(filename.split('.')
                                               [0] + 'dialog'), index=False, engine='xlsxwriter')
        zip_files(files='./tmp/*.xlsx')
        os.remove('./tmp/{}'.format(filename.split('.')[0] + 'result.xlsx'))
        os.remove('./tmp/{}'.format(filename.split('.')[0] + 'dialog.xlsx'))
    except Exception as e:
        logger_running.error('download_file: '+str(e))
        return JsonResponse({'code': 500, 'content': '数据库查询出错', 'message': 'mysql error'})


def download_session(filename):
    try:
        sql = 'select * from session where file in (%s)' % (filename)
        filename = filename[1:-1]
        df = pd.read_sql(sql, mysql_handler.driver)
        df.to_excel('./tmp/{}.xlsx'.format(filename.split('.')
                                           [0]), index=False, engine='xlsxwriter')
        zip_files(files='./tmp/*.xlsx')
        os.remove('./tmp/{}'.format(filename.split('.')[0] + '.xlsx'))
    except Exception as e:
        logger_running.error('download_file: '+str(e))
        return JsonResponse({'code': 500, 'content': '数据库查询出错', 'message': 'mysql error'})


def download_file(request):
    if request.method == 'GET':
        ip = get_remote_ip(request)
        filename = request.GET.get('file')
        filename = str(filename.split(','))[1:-1]

        # _, token = authorization(request)
        # user = mysql_handler.user_login_by_token(token)

        logger_running.info(
            'Downloading file: {}, ip: {}'.format(filename, ip))

        if 'marktool' in filename:
            download_cqa(filename)
        elif 'multiclassification' in filename:
            download_multiclassification(filename)           # 为什么要把这个放前面，因为 classification in multiclassification
        elif 'intention' in filename or 'action' in filename or 'classification' in filename:
            download_classification(filename)
        elif 'graph' in filename:
            download_graph(filename)
        elif 'session' in filename:
            download_session(filename)
        elif 'twotuples' in filename:
            download_twotuples(filename)
        return return_file()


# 批量下载文件
def download_files_(request):
    if request.method == 'POST':
        ip = get_remote_ip(request)
        files = request.POST.get('files_')
        files = str(files.split(','))[1:-1]
        # str: file1,file2,...,filen
        # print(str(files.split(','))[1:-1])
        _, token = authorization(request)
        user = mysql_handler.user_login_by_token(token)

        logger_running.info('Downloading files: {}, ip: {}, name: {}'.format(
            files, ip, user.zh_name))

        # 查询文件和总容量
        if 'marktool' in files:
            download_cqa(files)
        elif 'multiclassification' in files:
            download_multiclassification(files)
        elif 'classification' in files or 'action' in files:
            download_classification(files)
        elif 'graph' in files:
            download_graph(files)
        elif 'twotuples' in files:
            download_twotuples(files)

        return JsonResponse({
            'code': 200,
            'data': '',
            'message': 'general files success'
        })

def QualityDownload(request):
    if request.method == 'POST':
        ip = get_remote_ip(request)
        files = request.POST.get('files_')
        files = str(files.split(','))[1:-1]
        _, token = authorization(request)
        user = mysql_handler.user_login_by_token(token)

        logger_running.info('Downloading files: {}, ip: {}, name: {}'.format(
            files, ip, user.zh_name))

        # 查询文件和总容量
        if 'marktool' in files:
            download_cqa(files)
        elif 'multiclassification' in files:
            quality_download_multiclassification(files)
        elif 'classification' in files or 'action' in files:
            quality_download_classification(files)
        elif 'graph' in files:
            download_graph(files)
        elif 'twotuples' in files:
            download_twotuples(files)

        return JsonResponse({
            'code': 200,
            'data': '',
            'message': 'general files success'
        })


def download_multiclassification(filename):
    try:
        if len(filename.split(',')) == 1:
            sql = 'select * from multiclassification where file in (%s)' % (filename)
            df = pd.read_sql(sql, mysql_handler.driver)
            filename = filename[1:-1].split('.')[0]
            author = filename.split('_')[1]
            df["author"] = author
            df["filename"] = filename
            df[['uuid', 'sentence', 'label', 'author', 'filename']].to_excel(
                './tmp/{}.xlsx'.format(filename), index=False, engine='xlsxwriter')
            time.sleep(0.5)
            zip_files(files='./tmp/{}.xlsx'.format(filename))
            time.sleep(0.5)
            os.remove('./tmp/{}.xlsx'.format(filename))
        else:
            # 变量名字
            filename_ = 'select_data'
            for index in filename.split(','):
                sql = 'select * from multiclassification where file in (%s)' % (index)
                author = index.split('_')[1]
                df = pd.read_sql(sql, mysql_handler.driver)
                df["author"] = author
                df["filename"] = index
                if not os.path.exists('./tmp/{}.csv'.format(filename_)):
                    df[['uuid', 'sentence', 'label', 'author', 'filename']].to_csv('./tmp/{}.csv'.format(filename_), mode='a',
                          index=False, index_label=False)
                else:
                    df[['uuid', 'sentence', 'label', 'author', 'filename']].to_csv('./tmp/{}.csv'.format(filename_), mode='a', header=False,
                                                                       index=False, index_label=False)
            zip_files(files='./tmp/{}.csv'.format(filename_))
            os.remove('./tmp/{}.csv'.format(filename_))
    except Exception as e:
        logger_running.error('download_file: '+str(e) + ' sql: ' + sql)
        return JsonResponse({'code': 500, 'content': '数据库查询出错', 'message': 'mysql error'})



def quality_download_multiclassification(filename):

    try:
        if len(filename.split(',')) == 1:
            sql = 'select * from multiclassification where file in (%s)' % (filename)
            df = pd.read_sql(sql, mysql_handler.driver)
            filename = filename[1:-1].split('.')[0]
            author = filename.split('_')[1]
            df["author"] = author
            df["filename"] = filename
            total_num = df.shape[0]
            least_check_num = int(total_num * 0.002)
            data = df.sample(frac=1)
            df = pd.DataFrame(columns=list(data))
            for label in data.label.unique():
                tmp = data[data.label == label]
                check_num = max(int(tmp.shape[0] * 0.1), least_check_num)
                df = pd.concat([df, tmp.head(check_num-1)])
            df[['uuid', 'sentence', 'label', 'author', 'filename']].to_excel('./tmp/{}.xlsx'.format(filename), index=False, engine='xlsxwriter')
            time.sleep(0.5)
            zip_files(files='./tmp/{}.xlsx'.format(filename))
            time.sleep(0.5)
            os.remove('./tmp/{}.xlsx'.format(filename))
        else:
            # 变量名字
            filename_ = 'select_data'
            for index in filename.split(','):
                sql = 'select * from multiclassification where file in (%s)' % (index)
                author = index.split('_')[1]
                df = pd.read_sql(sql, mysql_handler.driver)
                df["author"] = author
                df["filename"] = index
                total_num = df.shape[0]
                least_check_num = int(total_num * 0.002)
                data = df.sample(frac=1)
                df = pd.DataFrame(columns=list(data))
                for label in data.label.unique():
                    tmp = data[data.label == label]
                    check_num = max(int(tmp.shape[0] * 0.1), least_check_num)
                    df = pd.concat([df, tmp.head(check_num-1)])
                if not os.path.exists('./tmp/{}.csv'.format(filename_)):
                    df[['uuid', 'sentence', 'label', 'author', 'filename']].to_csv('./tmp/{}.csv'.format(filename_), mode='a',
                          index=False, index_label=False)
                else:
                    df[['uuid', 'sentence', 'label', 'author', 'filename']].to_csv('./tmp/{}.csv'.format(filename_), mode='a', header=False,
                                                                       index=False, index_label=False)
            zip_files(files='./tmp/{}.csv'.format(filename_))
            os.remove('./tmp/{}.csv'.format(filename_))
    except Exception as e:
        logger_running.error('download_file: '+str(e) + ' sql: ' + sql)
        return JsonResponse({'code': 500, 'content': '数据库查询出错', 'message': 'mysql error'})


def quality_download_classification(filename):
    try:
        if len(filename.split(',')) == 1:
            sql = 'select * from classification where file in (%s)' % (filename)
            df = pd.read_sql(sql, mysql_handler.driver)
            filename = filename[1:-1].split('.')[0]
            author = filename.split('_')[1]
            df["author"] = author
            df["filename"] = filename
            total_num = df.shape[0]
            least_check_num = int(total_num * 0.002)
            data = df.sample(frac=1)
            df = pd.DataFrame(columns=list(data))
            for label in data.label.unique():
                tmp = data[data.label == label]
                check_num = max(int(tmp.shape[0] * 0.1), least_check_num)
                df = pd.concat([df, tmp.head(check_num-1)])
            df[['uuid', 'sentence', 'label', 'author', 'filename']].to_excel('./tmp/{}.xlsx'.format(filename), index=False, engine='xlsxwriter')
            time.sleep(0.5)
            zip_files(files='./tmp/{}.xlsx'.format(filename))
            time.sleep(0.5)
            os.remove('./tmp/{}.xlsx'.format(filename))
        else:
            # 变量名字
            filename_ = 'select_data'
            for index in filename.split(','):
                sql = 'select * from classification where file in (%s)' % (index)
                author = index.split('_')[1]
                df = pd.read_sql(sql, mysql_handler.driver)
                df["author"] = author
                df["filename"] = index
                total_num = df.shape[0]
                least_check_num = int(total_num * 0.002)
                data = df.sample(frac=1)
                df = pd.DataFrame(columns=list(data))
                for label in data.label.unique():
                    tmp = data[data.label == label]
                    check_num = max(int(tmp.shape[0] * 0.1), least_check_num)
                    df = pd.concat([df, tmp.head(check_num-1)])
                if not os.path.exists('./tmp/{}.csv'.format(filename_)):
                    df[['uuid', 'sentence', 'label', 'author', 'filename']].to_csv('./tmp/{}.csv'.format(filename_), mode='a',
                          index=False, index_label=False)
                else:
                    df[['uuid', 'sentence', 'label', 'author', 'filename']].to_csv('./tmp/{}.csv'.format(filename_), mode='a', header=False,
                                                                       index=False, index_label=False)
            zip_files(files='./tmp/{}.csv'.format(filename_))
            os.remove('./tmp/{}.csv'.format(filename_))
    except Exception as e:
        logger_running.error('download_file: '+str(e) + ' sql: ' + sql)
        return JsonResponse({'code': 500, 'content': '数据库查询出错', 'message': 'mysql error'})

def download_files(request):
    if request.method == 'GET':
        return return_file()

# 删除文件


def delete_file(request):
    if request.method == 'POST':
        ip = get_remote_ip(request)
        _, token = authorization(request)
        user = mysql_handler.user_login_by_token(token)
        # 没token
        if token == None or user.token != token and user.permission != 2:
            return JsonResponse({'code': 500, 'content': '没有删除权限', 'message': 'delete file error'})
        # {'username': 'niuzc', 'timestamp': '1587723886.1659753', 'token': '3f9bc06c24e46b766397b58bb90b3595a7d5bd52'}

        file = request.POST.get('file')

        try:
            num = mysql_handler.delete_file(file)
            if num > 0:
                logger_running.info('删除 {} 成功, ip: {}, name: {}'.format(
                    file, ip, user.zh_name))

                return JsonResponse({
                    'code': 200,
                    'content': '删除 {} 成功'.format(file),
                    'message': 'delete success'})
        except Exception as e:
            logger_running.error('delete_file: '+str(e))
            return JsonResponse({'code': 500, 'content': '删除文件出错', 'message': 'delete file error'})
        return JsonResponse({'code': 500, 'content': '删除文件出错', 'message': 'delete file error'})


def filename_search(request):
    if request.method == 'GET':
        ip = get_remote_ip(request)
        _, token = authorization(request)
        user = mysql_handler.user_login_by_token(token)

        filename = request.GET.get('filename')
        server = request.GET.get('server')
        df = mysql_handler.filename_search(filename, server)

        if user:
            # logger_running.info('filename:{} 查询成功, filesize: {}, ip: {}, name: {}'.format(filename, df.shape[0], ip, user.zh_name))
            logger_running.info('filename:{} 查询成功, filesize: {}, ip: {}, name: {}'.format(filename, df.shape[0], ip, user.zh_name))
            # 合并结果
            return JsonResponse({
                'code': 200,
                'data': df.to_dict(orient='records'),
                'message': '查询成功'
            })
        else:
            return JsonResponse({
                'code': 201,
                'data': [],
                'message': '查询失败'
            })


def get_file_length(request):
    if request.method == 'GET':

        num = mysql_handler.get_file_length()

        return JsonResponse({
            'code': 200,
            'data': num,
            'message': '请求成功'
        })


def file_check(request):
    if request.method == 'GET':
        filename = request.GET.get('filename')
        precent = int(request.GET.get('precent'))

        df = mysql_handler.download_file(filename)

        num = int(precent / 100 * df.shape[0])

        if 'marktool' in filename:
            tmp = df[df['label'] != ''].sample(frac=1.0, random_state=0).head(
                num)[['uuid', 'file', 'context', 'question', 'answer', 'label']]
        else:
            # 分层抽样
            value_counts = df.label.value_counts()
            keys = list(value_counts.keys())
            each_precent = list(value_counts.values / df.shape[0] * num)
            # logger_running.info(each_precent)
            each_precent = [int(round(i)) for i in each_precent]
            # logger_running.info([keys, each_precent])
            tmp = [df[df['label'] == k].sample(
                v, random_state=0) for k, v in zip(keys, each_precent) if k != '']
            if len(tmp) > 0:
                tmp = pd.concat(tmp)[['uuid', 'file', 'sentence', 'label']]
            else:
                return JsonResponse({
                    'code': 200,
                    'data': [],
                    'message': '请求成功'
                })
            # 随机抽样
            # tmp = df.sample(frac=1.0).head(num))[['uuid', 'file', 'sentence', 'label']]

        tmp['index'] = [i for i in range(tmp.shape[0])]
        logger_running.info('filename: {}, precent: {}, shape: {}'.format(
            filename, precent, tmp.shape[0]))
        return JsonResponse({
            'code': 200,
            'data': tmp.to_dict(orient='records'),
            'message': '请求成功'
        })


def to_test(request):
    if request.method == 'POST':
        json_string = request.POST.get('jsonString')
        df = pd.concat([pd.DataFrame(each, index=[0])
                        for each in eval(json_string)])
        df.reset_index(drop=True, inplace=True)
        # print(df.head())

        conn = create_engine('mysql+pymysql://marktool:dZKk44peNi4XBNmp@123.60.147.137:3306/marktool?charset=utf8mb4')
        df[['uuid', 'file', 'label', 'sentence']].to_sql('to_test', con="conn", if_exists='append', index=False, chunksize=100)

        return JsonResponse({
            'code': 200,
            'data': "",
            'message': '保存成功'
        })


def search_not_empty(request):
    if request.method == 'GET':
        ip = get_remote_ip(request)
        zh_name = request.GET.get('zh_name')
        if not zh_name:
            return JsonResponse({
                'code': 201,
                'message': '请刷新页面'
            })
        _, token = authorization(request)

        mclasseng = request.GET.get('mclasseng')
        if mclasseng =='mainpage':
            return JsonResponse({
                'code': 200,
                'data': {
                    'marked': [],
                    'unname':[]
                },
                'message': '请求成功'
            })
        user_info = mysql_handler.user_login_by_token(token)
        if user_info:

            not_empty = mysql_handler.search_not_empty(mclasseng, zh_name)

            unname = mysql_handler.search_not_empty(mclasseng, 'name')
            logger_running.info('mclasseng:{} 查询成功, ip: {}, name: {}'.format(
                mclasseng, ip, user_info.zh_name))
        else:
            not_empty = pd.DataFrame()
            unname = pd.DataFrame()

        # 合并结果
        return JsonResponse({
            'code': 200,
            'data': {
                'marked': not_empty.to_dict(orient='records'),
                'unname': unname.to_dict(orient='records')
            },
            'message': '请求成功'
        })


def search_user_not_empty_file(request):
     if request.method == 'GET':
        ip = get_remote_ip(request)
        zh_name = request.GET.get('zh_name')
        mclasseng = request.GET.get('mclasseng')
        prefix = request.GET.get('prefix')
        if zh_name != '' and mclasseng != '' and prefix != '':
            not_empty = mysql_handler.search_user_not_empty_file(mclasseng, zh_name, prefix)
            # file marked, total
            search_result = mysql_handler.search_user_not_empty_file_info(mclasseng, zh_name, prefix)
            # file, creater, is_check, is_pass
            # if search_result.shape[0] == 0:
            if search_result.shape[0] == 0:
                search_result['file'] = not_empty.file.tolist()
                search_result['creater'] = not_empty.file.tolist()[
                    0].split('_')[1]
                search_result['is_check'] = '否'
                search_result['is_pass'] = ''
            if not_empty.shape[0] == 0:
                # search_result['total_num'] = search_result.file.map(lambda x: x.split('_')[2])
                search_result['total_num'] = search_result.file.map(lambda x: int(x.split('_')[2]))
                search_result['marked'] = 0
                result = search_result
            else:
                result = pd.merge(left=not_empty, right=search_result,on='file', how='left').fillna('')
            logger_running.info('mclasseng:{} 查询成功, ip: {}, name: {}'.format(mclasseng, ip, zh_name))
            # 合并结果
            if type(result) == 'DataFrame':
                return JsonResponse({
                    'code': 200,
                    'data': result.to_dict(orient='records'),
                    'message': '请求成功'
                })
            else:
                return JsonResponse({
                    'code': 200,
                    # 'data': result,
                    'data': result.to_dict(orient='records'),
                    'message': '请求成功'
                })
        else:
            return JsonResponse({
                'code': 202,
                'data': [],
                'message': '请求失败'
            })


def get_tag_distribution(request):
    '''查询某类文件标注数量

    '''
    if request.method == 'GET':
        tag = request.GET.get('tag')
        tag = '%' + tag + '%'

        df = mysql_handler.get_tag_distribution(tag)

        return JsonResponse({
            'code': 200,
            'data': df.to_dict(orient='records'),
            'message': '请求成功'
        })


def chrono_break(request):
    '''
    1. 搜索file_origin表
    2. 找到则修改file_origin表，修改各任务表文件名
    3. 找不到则返回无法还原
    '''
    if request.method == 'GET':
        filename = request.GET.get('filename')

        result = mysql_handler.chrono_break_read(filename, 'file')
        if result[0] == None or filename.split('_')[1] == 'name' or result[0]['origin'] == '':
            return JsonResponse({
                'code': 202,
                'data': [],
                'message': '无法还原，可能是以前上传或者单份上传的'
            })
        else:
            origin = result[0]['origin']
            serve = filename.split('.')[-1]

            # if serve in ['classification', 'marktool', 'graph', 'twotuples']:
            if serve in ['classification', 'marktool', 'graph', 'twotuples', 'multiclassification']:
                result = mysql_handler.update_file_origin(origin, origin)
                mysql_handler.chrono_break_update(origin, filename, serve)
            else:
                return JsonResponse({
                    'code': 202,
                    'data': [],
                    'message': '还原失败，无此任务数据'
                })
            return JsonResponse({
                'code': 200,
                'data': [],
                'message': '还原成功'
            })


def req_from_filename(request):
    if request.method == 'GET':
        ip = get_remote_ip(request)
        _, token = authorization(request)
        user_info = mysql_handler.user_login_by_token(token)

        if user_info:
            req_filename = request.GET.get('filename')
            df, category, a, filename = mysql_handler.req_from_filename(req_filename, user_info.zh_name)
            result = mysql_handler.chrono_break_read(req_filename)
            if result[0] != None and (result[0]['origin'] == result[0]['file'] or result[0]['file'] == ''):
                # 查询到要标注的数据后，还需要判断这份数据是否被别人领过
                # 用name文件请求 要修改file的字段
                origin = result[0]['origin']
                serve = origin.split('.')[-1]
                status = mysql_handler.update_file_origin(origin, filename)
                if status > 0:
                    status = mysql_handler.chrono_break_update(
                        filename, origin, serve)
            try:
                logger_running.info('请求filename: {}, 返回filename:{}, ip: {}, name: {}'.format(filename,
                                                                                             df.file[0], ip, user_info.zh_name))
            except:
                logger_running.error('请求filename: {}, ip: {}, name: {}'.format(filename,
                                                                               ip, user_info.zh_name))
                return JsonResponse({
                    'code':202,
                    "message":"请求失败"
                })
            if df.shape[0] > 0:
                code = 200
            else:
                code = 202
        else:
            df = pd.DataFrame()
            code = 202

        # 合并结果
        return JsonResponse({
            'code': code,
            'filename': filename,
            'data': df.to_dict(orient='records'),
            'category': category,
            'content': a,
            'message': '请求成功'
        })

def function1(already, arr):
    num = len(already)
    for line in arr:
        # print(line)
        a, b = line.split("#同义的实体#")
        if a in already or b in already:
            already.add(a)
            already.add(b)
    num2 = len(already)
    if num != num2:
        already = function1(already, arr)
    else:
        return already
    return already


def function2(arr):
    syms = []
    exits = set()
    current = -1
    for idx, line in enumerate(arr):
        a, b = line.split("#同义的实体#")
        already = set([a, b])
        if a not in exits and b not in exits:
            syms.append(already)
            current = len(syms) - 1
            exits = exits | already
            # print(line,"line",syms)
        else:
            exits = exits | already
            for index, al in enumerate(syms):
                if a in al or b in al:
                    syms[index].add(a)
                    syms[index].add(b)
                    current = index
                    break
        # print(line, syms[current], syms, arr[idx:])
        already = function1(syms[current], arr[idx:])
        # print(already)
        # print(line,already)
        exits = exits | already
        syms[current] = already
    return syms


# 生成同义词
def gen_same_word(arr):
    gen = itertools.permutations(arr, 2)
    return list(set(['#同义的实体#'.join(set(each)) for each in gen]))


def check(outer, inner):
    '''
    Args:
        outer: 标注人员标的
        inner: 质检标的

    Returns:

    '''
    uneed_entity = ['address', 'age', 'datetime', 'emotion', 'fluid', 'frequency', 'gender',
                    'identity', 'medicine', 'mobile', 'name', 'org', 'physiology', 'price', 'qq', 'route', 'wechat']
    need_entity = ["item", "symptom", "part", "cause", "virus", "check",
                   "surgery", "othertreatment", "foodtherapy", "doctor", "tool"]
    # 筛选对话
    outer = outer[-outer['entity_value_relationship'].str.contains(
        '|'.join(uneed_entity))].entity_value_relationship.tolist()
    inner = inner[-inner['entity_value_relationship'].str.contains(
        '|'.join(uneed_entity))].entity_value_relationship.tolist()
    same = list(set(outer) & set(inner))

    if len(outer) == 0 and len(inner) == 0:
        return outer, inner, len(outer), len(inner), 0, 0, 0
    elif len(outer) == 0 or len(inner) == 0:
        return outer, inner, len(outer), len(inner), 0, 0, 0
    # 筛选同义实体
    outer_same_entity = [
        each for each in outer if re.search(pattern='同义', string=each)]
    inner_same_entity = [
        each for each in inner if re.search(pattern='同义', string=each)]

    unique_outer_same_entity = function2(outer_same_entity)
    unique_inner_same_entity = function2(inner_same_entity)

    # 生成同义实体
    gen_same_outer_entity = [
        e for each in unique_outer_same_entity for e in gen_same_word(each)]
    gen_same_inner_entity = [
        e for each in unique_inner_same_entity for e in gen_same_word(each)]

    # 筛选非同义实体
    outer_unsame_entity = [
        each for each in outer if not re.search(pattern='同义', string=each)]
    inner_unsame_entity = [
        each for each in inner if not re.search(pattern='同义', string=each)]

    # 生成非同义实体
    for g in gen_same_outer_entity:
        # 正向生成
        tmp = [each.replace(g.split('#')[0], g.split('#')[-1])
               for each in outer_unsame_entity]
        outer_unsame_entity += tmp
        # 反向生成
        tmp = [each.replace(g.split('#')[-1], g.split('#')[0])
               for each in outer_unsame_entity]
        outer_unsame_entity += tmp
        outer_unsame_entity = list(set(outer_unsame_entity))

    for g in gen_same_inner_entity:
        tmp = [each.replace(g.split('#')[0], g.split('#')[-1])
               for each in inner_unsame_entity]
        inner_unsame_entity += tmp
        tmp = [each.replace(g.split('#')[-1], g.split('#')[0])
               for each in inner_unsame_entity]
        inner_unsame_entity += tmp
        inner_unsame_entity = list(set(inner_unsame_entity))

    # 生成非同义实体
    # 正向生成
    # gen_outer_unsame_entity = [each.replace(g.split('#')[0], g.split('#')[-1]) for g in gen_same_outer_entity for each in outer_unsame_entity]
    # 反向生成
    # gen_outer_unsame_entity += [each.replace(g.split('#')[-1], g.split('#')[0]) for g in gen_same_outer_entity for each in outer_unsame_entity]
    # gen_inner_unsame_entity = [each.replace(g.split('#')[0], g.split('#')[-1]) for g in gen_same_inner_entity for each in inner_unsame_entity]
    # gen_inner_unsame_entity += [each.replace(g.split('#')[-1], g.split('#')[0]) for g in gen_same_inner_entity for each in inner_unsame_entity]

    # 筛选非同义实体 + 生成非同义实体 + 生成同义实体
    A = list(set(outer_unsame_entity + gen_same_outer_entity))
    B = list(set(inner_unsame_entity + gen_same_inner_entity))
    C = len(set(A) & set(B))
    # 准确率               召回率
    return outer, inner, same, len(A), len(B),  C, round(C / len(A), 3), round(C / len(B), 3)


def graph_check(request):
    # 功能已废弃
    if request.method == 'GET':
        # 质检人员的文件名
        checker = request.GET.get('filename')
        dialog_id = int(request.GET.get('dialog_id'))

        # 标注人员的文件名
        '''example
        类别_质检_name-贰0.graph
        '''
        marker = checker.split('_')[0] + '_' + \
            checker.split('_')[-1].replace('-', '_')

        outer = mysql_handler.read_entity_value(dialog_id, marker)
        inner = mysql_handler.read_entity_value(dialog_id, checker)
        outer_entity, inner_entity, same, outer_shape, inner_shape, C, A, B = check(
            outer, inner)

        # 互不相同的实体
        outer_unique_entity = list(set(outer_entity) - set(inner_entity))
        inner_unique_entity = list(set(inner_entity) - set(outer_entity))
        max_len = max([len(outer_unique_entity), len(inner_unique_entity)])

        # 构造dataframe，列长度相同
        inner_unique_entity += ['' for i in range(
            max_len - len(inner_unique_entity))]
        outer_unique_entity += ['' for i in range(
            max_len - len(outer_unique_entity))]
        # same += ['' for i in range(max_len - len(same))]

        data = [[{'inner': i, 'outer': o}
                 for i, o in zip(inner_unique_entity, outer_unique_entity)]]
        same = [{'same': s} for s in same]
        data.append(same)
        # data = [
        #     {'inner': inner_unique_entity},
        #     {'outer': outer_unique_entity},
        #     {'same' : same}
        # ]
        # print(data)
        title = '标注实体数量：{}, 质检实体数量：{}, 相同实体数量：{}, 准确率：{}, 召回率：{}'.format(
            outer_shape, inner_shape, C, A, B)

        # 合并结果
        return JsonResponse({
            'code': 200,
            'data': data,
            'title': title,
            'message': '请求成功'
        })

def select_everyone_marked_count(request):
    if request.method == 'GET':
        zh_name = request.GET.get('zh_name', '')
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')

        result = mysql_handler.everyone_marked_count(start_date, end_date)
        # 判断时间区间有没有数据
        if result.shape[0] == 0:
            return JsonResponse({
                'code': 201,
                'message': '该区间无数据'
            })
        # 创建 名字 列
        result['name'] = result.file.map(lambda x:x.split('_')[1])
        # 创建 任务 列
        result['server'] = result.file.map(lambda x:x.split('.')[1])
        deltaday = datetime.strptime(end_date, "%Y-%m-%d %H:%M") - datetime.strptime(start_date, "%Y-%m-%d %H:%M")
        # 60秒 * 60分 * 24小时 - 60秒；
        # 前端设置传进来的时间为0点到晚上23点59分
        deltaday = deltaday.total_seconds() / 86340

        # 传入时间差大于1天，则按照1天划分，传入当天则按照1小时划分
        if deltaday == 1.:
            MINIMUM_TIME = '1H'
        else:
            MINIMUM_TIME = '1D'

        if zh_name != '':
            # 查询某个人
            df = result[result['name'] == zh_name]
            # 判断时间区间有没有数据
            if df.shape[0] == 0:
                return JsonResponse({
                    'code': 201,
                    'message': '该区间无数据'
                })
            df.index = df.last_change_time
            r = pd.DataFrame(df.groupby('file').name.resample(MINIMUM_TIME).count())
            r.reset_index(inplace=True)
            r['last_change_time'] = r['last_change_time'].astype('str')
            r = pd.pivot_table(r, values='name', index=['file'], columns=['last_change_time'], aggfunc=np.sum).fillna(0).to_dict()
        else:
            # 查询所有人
            df = result
            df.index = df.last_change_time
            r = pd.DataFrame(df.groupby('name').file.resample(MINIMUM_TIME).count())
            r.reset_index(inplace=True)
            r['last_change_time'] = r['last_change_time'].astype('str')
            r = pd.pivot_table(r, values='file', index=['name'], columns=['last_change_time'], aggfunc=np.sum).fillna(0).to_dict()

        # 统计每个任务的标注数量
        server_count = pd.DataFrame(df.groupby('server').name.count()).reset_index()
        server_count = server_count.rename(columns={'name': 'count'}).to_dict(orient='records')

        _new_r = {}
        # 前面把NAN的数据填充了0，因此要删除数量为0的数据
        for _d, _vs in r.items():
            _new_r[_d] = {}
            for _f, _num in _vs.items():
                if _num != 0:
                    _new_r[_d][_f] = _num

        return JsonResponse({
            'code': 200,
            'data': [_new_r, server_count],
            'message': '请求成功'
        })
