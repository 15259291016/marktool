import DBUtils
import pandas as pd
import json
import re
import datetime

import pymysql
import requests
import sqlalchemy
import torch

from marktool.src.utils.logger import logger_running
from sqlalchemy import create_engine
import os

'''
import os
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.conf import settings

data = request.FILES['image'] # or self.files['image'] in your form

path = default_storage.save('tmp/somename.mp3', ContentFile(data.read()))
tmp_file = os.path.join(settings.MEDIA_ROOT, path)
'''
from modelscope.pipelines import pipeline
from marktool.src.utils.mysql_handler import MySqlHandler
from marktool.src.utils.mysql_handler import config
from marktool.src.utils.safety import get_remote_ip
from marktool.src.utils.safety import authorization
from django.http import JsonResponse, HttpResponse

import numpy as np

# 返回请求结果
mysql_handler = MySqlHandler()

p = pipeline('named-entity-recognition', 'damo/nlp_raner_named-entity-recognition_chinese-base-cmeee')

from sqlalchemy import create_engine

engine = create_engine('mysql+pymysql://marktool:dZKk44peNi4XBNmp@123.60.147.137:3306/marktool?charset=utf8mb4')


def response_data(data=[], marked='', category=[], code=200, message='success'):
    result = {
        'code': code,
        'message': message,
        'data': data,
        # 已标注category统计
        'marked': marked,
        # 当前句子上一次标注category
        'category': category
    }

    return json.dumps(result, ensure_ascii=False)


def cqas2dialogs(cqas, filename):
    '''
    Args:
        cqas: (list)

    Returns:
        dialogs: (dataframe)
    '''

    def check(i, j):
        pattern = r'[CQA][\d]{6,16}[@#$]{6}：'
        return True if re.match(pattern=pattern, string=cqas[i * 4 + j]) else False

    uuid, context, question, answer = [], [], [], []
    for i in range((len(cqas)) // 4 -1):
        # for j in range(3):
        #     if not check(i, j):
        #         logger_running.error(filename + ' cqa上传错误' +
        #                              'message: ' + cqas[i * 4 + j])
        #         return 'values error in {} lines'.format(str(i * 4 + j + 1))

        uuid.append(cqas[i * 4].split('@@##$$：')[0][1:])
        context.append(cqas[i * 4].split('@@##$$：')
                       [1].replace('\n', '').replace('\r', ''))
        question.append(cqas[i * 4 + 1].split('@@##$$：')
                        [1].replace('\n', '').replace('\r', ''))
        answer.append(cqas[i * 4 + 2].split('@@##$$：')
                      [1].replace('\n', '').replace('\r', ''))
    print(i)
    return pd.DataFrame({'uuid': uuid, 'context': context, 'question': question, 'answer': answer})


def twotuples_file(filename, ip=None):
    # 后缀
    do = filename.split('.')[1]
    # 查询数据库中是否存在该文件

    df_, _, _ = mysql_handler.confirm_file(do, filename)

    if df_.shape[0] > 0:
        # df_.columns = ['uuid', 'sentence', 'label', 'file']
        # 如果数据库中存在数据
        logger_running.info('file: {}, size: {}, ip: {}'.format(
            filename, df_.shape[0], ip))
        df_.sort_values('uuid', inplace=True)
        category = df_['label'].tolist()
        return df_, category
    else:
        df = pd.read_csv(open('tmp/{}'.format(filename),
                              encoding='utf-8')).fillna('')
        os.remove('tmp/{}'.format(filename))
        df.sort_values('id', ascending=True, inplace=True)
        df['file'] = filename
        df['ner'] = ''
        df['tuple'] = ''
        conn = create_engine(
            'mysql+pymysql://{}:{}@{}:3306/{}?charset={}'.format(config['user'], config['passwd'], config['host'],
                                                                 config['database'], config['charset']))
        message = df_to_sql(df, 'two_tuples')
        # 没写完，当出现异常怎么办
        return df, []


def intention_file(filename, ip=None):
    # 后缀
    do = filename.split('.')[1]
    # 查询数据库中是否存在该文件

    df_, _, _ = mysql_handler.confirm_file(do, filename)

    if df_.shape[0] > 0:
        # df_.columns = ['uuid', 'sentence', 'label', 'file']
        # 如果数据库中存在数据
        logger_running.info('file: {}, size: {}, ip: {}'.format(
            filename, df_.shape[0], ip))
        df_.sort_values('uuid', inplace=True)
        category = df_['label'].tolist()
        return df_, category
    else:
        df = pd.read_csv(open('tmp/{}'.format(filename),
                              encoding='utf-8')).fillna('')
        os.remove('tmp/{}'.format(filename))
        try:
            df.sort_values('id', ascending=True, inplace=True)
        except:
            df.sort_values('uuid', ascending=True, inplace=True)
        df['file'] = filename
        df['ner'] = ''
        df['tuple'] = ''
        msessage = df_to_sql(df, 'classification')
        # 没写完，当出现异常怎么办
        return df, []


def graph_file(filename, ip=None):
    # 后缀
    do = filename.split('.')[-1]
    # 查询数据库中是否存在该文件

    df_, (relation, ner), marked_status = mysql_handler.confirm_file(do, filename)
    if df_.shape[0] > 0:
        # df_.columns = ['uuid', 'sentence', 'label', 'file']
        # 如果数据库中存在数据
        logger_running.info('file: {}, size: {}, ip: {}'.format(
            filename, df_.shape[0], ip))
        df_.sort_values(['dialog_id', 'sentence_id'], inplace=True)
        # category = pd.read_sql('SELECT * FROM entity_relationship WHERE file="%s"' % filename, con=mysql_handler.driver)
        # category.sort_values('dialog_id', inplace=True, ascending=True)
        # category = category.groupby('dialog_id').apply(lambda x:x['entity_value_relationship'].tolist()).to_dict()
        return df_, (relation, ner), marked_status
    else:
        try:
            df = pd.read_csv(open('tmp/{}'.format(filename),
                                  encoding='utf-8')).fillna('')
        except UnicodeDecodeError:
            os.remove('tmp/{}'.format(filename))
            return 'unicode error', [[], []], []
        os.remove('tmp/{}'.format(filename))
        df.sort_values(['dialog_id', 'sentence_id'], inplace=True)
        df['file'] = filename
        dialog_id = df.dialog_id.unique().tolist()
        df_to_sql(df, 'grpah')
        # 没写完，当出现异常怎么办

        marked_status = []
        for idx, did in enumerate(list(set(dialog_id))):
            marked_status.append({
                'dialog_id': did,
                'id': idx,
                'marked': 'sentence-no-mark'
            })
        return df, [[], []], marked_status


def generate_classification_label(df, output):
    '''生成标注工具配置文件

    意图类别   意图
       A        A';
                B';
       C        C';
    to:
        [{
            value:
            label:
            children: []
        }]
    '''
    result = []
    col = df.columns
    title = col[0]
    gp = df.groupby(title)
    for idx, g in enumerate(gp):
        df_ = df[df[title] == g[0]]
        result.append({
            'value': df_[col[0]].tolist()[0],
            'label': df_[col[0]].tolist()[0],
            'children': [{
                'value': v,
                'label': v,
            } for v in df_[col[1]].tolist()]
        })
    if not os.path.exists(os.path.dirname(output)):
        os.makedirs(os.path.dirname(output))

    with open(output, mode='w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=4)
    return result


# 保存上传的数据文件
def file_save(file, output):
    destination = open(output, 'wb+')
    [destination.write(chunk) for chunk in file.chunks()]
    destination.close()


def df_to_sql(df, table_name):
    try:
        df.to_sql(table_name, con=engine,
                  if_exists='append', index=False)
        return True
    except Exception as e:
        message = re.findall(pattern='.*(\".*\").*', string=str(e)[:150])
        logger_running.error('table: {}, {}, {}'.format(table_name, df.file.tolist()[0], message))
        return message


def save_file_origin(df, user_name):
    # 保存退回的文件名 构造表数据
    origin = list(df['file'].unique())
    # file 和 origin 相同
    upload_date = datetime.datetime.now()
    df_ = pd.DataFrame({
        'file': [""] * len(origin),
        'origin': origin,
        'upload_date': [upload_date] * len(origin),
        'creater': [user_name] * len(origin)
    })
    df_to_sql(df_, 'file_origin')


def deal_big_data(big_data, filename, user_name):
    # 提取任务类型、切分数量
    server = filename.split('.')[1]
    cut_num = int(filename.split('.')[0].split('_')[2])
    big_data.reset_index(drop=True, inplace=True)

    file_list = mysql_handler.search_not_empty(server, filename.split('_')[0] + '%' + 'name')
    # 把最大的文件id号取出来
    if file_list.shape[0] == 0:
        max_file_id = 0
    else:
        file_list = file_list['file'].str.split('_', expand=True)
        max_file_id = max([int(file.split('.')[0])
                           for file in file_list.loc[:, 2].tolist()]) + 1

    # big_data['file'] = filename
    # 切分文件
    cut_file = []
    if server == 'session' or (server == 'graph' and '单句' not in filename):
        # 段落类型的文件切分
        dialog_id = big_data.dialog_id.unique()
        for i in range(dialog_id.size // cut_num + 1):
            tmp = big_data[big_data['dialog_id'].isin(
                dialog_id[cut_num * i: cut_num * (i + 1)])]
            replace_filename = filename.replace(
                str(cut_num), str(i + max_file_id))
            tmp['file'] = replace_filename
            cut_file.append(tmp)

    else:
        # 单句类型的文件切分
        # cut_num['graph'] = 2000
        for i in range(big_data.shape[0] // cut_num + 1):
            tmp = big_data.iloc[cut_num * i: cut_num * (i + 1), ]
            replace_filename = filename.replace(
                str(cut_num), str(i + max_file_id))
            tmp['file'] = replace_filename
            cut_file.append(tmp)
    big_data = pd.concat(cut_file)

    if server == 'marktool':
        # sql = 'SELECT * FROM marktool WHERE "%s"' % filename
        # num = pd.read_sql(sql, con=mysql_handler.driver).shape[0]
        # if num == 0:
        big_data['label'] = ''
        status = df_to_sql(big_data, 'marktool')
        # 保存上传的文件名，退回用
        save_file_origin(big_data, user_name)
        return status
    elif server == 'graph':
        # sql = 'SELECT * FROM graph WHERE "%s"' % filename
        # num = pd.read_sql(sql, con=mysql_handler.driver).shape[0]
        # if num == 0:
        status = df_to_sql(big_data, 'graph')
        # 保存上传的文件名，退回用
        save_file_origin(big_data, user_name)
        return status
    elif server == 'classification':
        # sql = 'SELECT * FROM classification WHERE "%s"' % filename
        # num = pd.read_sql(sql, con=mysql_handler.driver).shape[0]
        # if num == 0:
        big_data['label'] = ''
        status = df_to_sql(big_data, 'classification')
        # 保存上传的文件名，退回用
        save_file_origin(big_data, user_name)
        return status
    elif server == 'multiclassification':
        # sql = 'SELECT * FROM classification WHERE "%s"' % filename
        # num = pd.read_sql(sql, con=mysql_handler.driver).shape[0]
        # if num == 0:
        big_data['label'] = ''
        status = df_to_sql(big_data, 'multiclassification')
        # 保存上传的文件名，退回用
        save_file_origin(big_data, user_name)
        return status
    elif server == 'twotuples':
        # sql = 'SELECT * FROM classification WHERE "%s"' % filename
        # num = pd.read_sql(sql, con=mysql_handler.driver).shape[0]
        # if num == 0:
        big_data['label'] = ''
        status = df_to_sql(big_data, 'two_tuples')
        # 保存上传的文件名，退回用
        save_file_origin(big_data, user_name)
        return status


def upload_file(request):
    ip = get_remote_ip(request)
    _, token = authorization(request)
    user = mysql_handler.user_login_by_token(token)
    user_name = user.zh_name
    try:
        file = request.FILES.get('file')
        filename = file.name
        base_path = 'marktool/src/config'
        path = os.path.join(base_path, filename)
        # 区分是配置文件还是标注数据
        if filename.split('.')[-1] == 'xlsx':
            # 保存上传的excel标签
            file_save(file, os.path.join(base_path, filename))
            df = pd.read_excel(path).fillna(method='ffill')
            # 删除excel标签
            os.remove(os.path.join(base_path, filename))
            # 把标签转化成json
            # 服务类型，classification || ner || relation
            serve = filename.split('_')[1].split('.')[0]
            if serve == 'classification':
                generate_classification_label(df, os.path.join(
                    base_path, 'classification', filename.split('_')[0] + '.json'))
                return JsonResponse(json.loads(response_data(data='', message='上传成功')))
            elif serve == 'multiclassification':
                generate_classification_label(df, os.path.join(
                    base_path, 'multiclassification', filename.split('_')[0] + '.json'))
                return JsonResponse(json.loads(response_data(data='', message='上传成功')))
            elif serve == 'ner':
                # 读取第一列
                zh = df.iloc[:, 0].tolist()
                # 读取第二列
                en = df.iloc[:, 1].tolist()
                ner = {z: e for z, e in zip(zh, en)}

                json.dump(ner, open(os.path.join(base_path, 'ner', filename.split('_')[0] + '.json'), encoding='utf-8',
                                    mode='w'), indent=4, ensure_ascii=False)
                return JsonResponse(json.loads(response_data(data='', message='上传成功')))
            elif serve == 'relation':
                relation = df.iloc[:, 0].tolist()
                json.dump(relation, open(os.path.join(base_path, 'relation', filename.split(
                    '_')[0] + '.json'), encoding='utf-8', mode='w'), indent=4, ensure_ascii=False)
                return JsonResponse(json.loads(response_data(data='', message='上传成功')))
            elif serve == 'attribute':
                generate_classification_label(df, os.path.join(
                    base_path, 'attribute', filename.split('_')[0] + '.json'))
                return JsonResponse(json.loads(response_data(data='', message='上传成功')))
            return JsonResponse(
                json.loads(response_data(data='', message='上传失败')))
    except Exception as e:
        logger_running.error(e)
        df, _, _ = mysql_handler.confirm_file('intention', filename)
        return JsonResponse(
            json.loads(response_data(data=df.to_dict(
                orient='records'))))

    # 上传文件不是标签，不是大份数据，则处理小份数据
    do = filename.split('.')[1]
    if do in ['graph', 'marktool', 'classification', 'twotuples', 'multiclassification', 'cqa']:
        file_save(file, os.path.join('tmp', filename))

    # 未标注大份数据上传
    if 'name' in filename:
        if 'marktool' in filename:
            text = open('tmp/' + filename, encoding='utf-8').readlines()
            big_data = cqas2dialogs(text, filename)
        else:
            big_data = pd.read_csv(open('tmp/{}'.format(filename), encoding='utf-8')).fillna('')
        os.remove('tmp/' + filename)
        message = deal_big_data(big_data, filename, user_name)
        if message == True:
            message = '上传成功'
            logger_running.error('上传文件成功 filename: {}, user: {}'.format(filename, user_name))
        return JsonResponse(json.loads(response_data(data='', message=message)))

    if do == 'twotuples' or do == 'action' or do == 'classification' or do == 'multiclassification':
        if do == 'twotuples':
            df, category = twotuples_file(filename, ip)
        else:
            df, category = intention_file(filename, ip)
        if type(df) == int:
            return JsonResponse(
                json.loads(response_data(
                    code=503, data='values error in {} lines'.format(df), message='上传失败'))
            )
        else:
            return JsonResponse(
                json.loads(response_data(data=df.to_dict(orient='records'), category=category, message='上传成功'))
            )
    elif do == 'marktool':
        text = open('tmp/' + filename, encoding='utf-8').readlines()
        os.remove('tmp/' + filename)
        try:
            df = cqas2dialogs(text, filename)
            if type(df) == str:
                return JsonResponse(
                    json.loads(response_data(code=503, data=df,
                                             message="analysis file error"))
                )
        except Exception as e:
            logger_running.error(filename + ' 文件解析错误 ' + str(e))
            return JsonResponse(
                json.loads(response_data(code=401, data="文件解析错误",
                                         message="analysis file error"))
            )

        column_map = {
            'uuid': 'uuid',
            'context': 'context',
            'answer': 'answer',
            'question': 'question',
            'label': 'label',
        }
        # 查询数据库中是否存在该文件
        df_, _, _ = mysql_handler.confirm_file('marktool', filename)
        # print(df_)
        if df_.shape[0] > 0:
            logger_running.info(
                'file: {}, size: {}, ip: {}'.format(filename, df_.shape[0], ip))

            df_.columns = [column_map[each_label]
                           for each_label in list(df_.columns)]
            df_.sort_values('uuid', inplace=True)
            category = df_[df_['label'] != '']['label'].tolist()

            return JsonResponse(
                json.loads(response_data(data=df_.to_dict(
                    orient='records'), category=category))
            )
        else:
            df['file'] = filename
            df['label'] = ''
            # 传入数据库
            # conn = create_engine(
            #     'mysql+pymysql://{}:{}@localhost:3306/{}?charset={}'.format(config['user'], config['passwd'], config['database'], config['charset']))
            df.sort_values('uuid', inplace=True)
            message = df_to_sql(df, 'marktool')
            if message != True:
                return JsonResponse(
                    json.loads(response_data(code='500', data=[], message=message))
                )
            # df = mysql_handler.confirm_file('marktool', file)
            df = df[['uuid', 'context', 'question', 'answer', 'label']]
            df.columns = [column_map[each_label]
                          for each_label in list(df.columns)]

            return JsonResponse(
                json.loads(response_data(data=df.to_dict(
                    orient='records'), message='上传成功'))
            )
    elif do == 'graph':
        df, (relation, ner), marked_status = graph_file(filename, ip)
        if type(df) == int:
            return JsonResponse(
                json.loads(response_data(
                    code=503, message='values error in {} lines'.format(df)))
            )
        elif type(df) == str:
            return JsonResponse(
                json.loads(response_data(
                    code=400, message='unicode error'))
            )
        else:
            return JsonResponse({
                'code': 200,
                'data': df.to_dict(orient='records'),
                'message': '上传成功',
                'content': marked_status,
                'category': (relation, ner)
            })


def updateinfo(request):
    from django import db
    sql = 'select * from update_info order by version desc'
    data = pd.read_sql(sql, db.connection)
    data_set = []
    for i in data.itertuples(name='Pandas'):
        data_set.append(
            {'version': i.version, 'fix': i.fix.split(','), 'feat': i.feat.split(','), 'id': i.id,'datetime':str(i.create_datetime)[:10]})
    data.rename({'create_datetime': 'datetime'})
    if data_set:
        return JsonResponse({
            'code': 200,
            'data': data_set
        })
    else:
        return JsonResponse({
            'code': 200,
            'data': []
        })

def default_dump(obj):
    """Convert numpy classes to JSON serializable objects."""
    if isinstance(obj, (np.integer, np.floating, np.bool_)):
        return obj.item()
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    else:
        return obj

def predict(request):
    sentence = request.GET.get('sentence')
    data = p(sentence)
    return HttpResponse(json.dumps(data, ensure_ascii=False, default=default_dump))

def mark(request):
    '''
    查询数据库中是否标注了这条记录
    如果没有
    则更新并返回200
    如果有
    则更新并返回201
    '''
    if request.method == 'POST':
        # 获取前端传过来的值
        file = request.POST.get('filename')
        server = file.split('.')[1]
        code = 200
        if server == 'marktool':
            uuid = request.POST.get('uuid')
            context = request.POST.get('context')
            answer = request.POST.get('answer')
            label = request.POST.get('category')
            # 更新label
            _ = mysql_handler.update_marked(
                server, {'context': context, 'uuid': uuid, 'file': file, 'answer': answer, 'label': label})
            labeled = mysql_handler.confirm_mark(
                server, {'uuid': uuid, 'file': file})
            if label == labeled:
                # 已标注
                code = 200
                status = 1
            else:
                code = 201
                status = 0
            if status == 1:
                return JsonResponse({
                    'code': code,
                    'marked': label,
                    'message': '请求成功',
                })
            else:
                logger_running.error(
                    '标注失败，当前传入label: {}, 数据库label: {}, status: {}, file: {}, uuid: {}'.format(
                        label, labeled, status, file, uuid))
                return JsonResponse({
                    'code': code,
                    'message': '更新失败',
                })
        elif server == 'action' or server == 'classification' or server == 'multiclassification':
            uuid = request.POST.get('uuid')
            label = request.POST.get('label')
            ner = request.POST.get('ner')
            _tuple = request.POST.get('tuple')
            # 更新label
            try:
                status_code = mysql_handler.update_marked(server,
                                                          {'server': server, 'uuid': uuid,
                                                           'label': label, 'ner': ner, 'tuple': _tuple,
                                                           'file': file})
            except Exception as e:
                print(e)
                status_code = 0
            # print(label, labeled, label == labeled)
            if status_code == 0:
                code = 500
                status = 0
            else:
                code = 200
                status = 1

            if status == 1:
                return JsonResponse({
                    'code': code,
                    'marked': label,
                    'message': '请求成功',
                })
            else:
                logger_running.error('标注失败，当前传入label: {} status: {}, file: {}, uuid: {}'.format(
                    label, status, file, uuid))
                return JsonResponse({
                    'code': code,
                    'message': '更新失败',
                })
        elif server == 'graph':
            dialog_id = request.POST.get('dialog_id')
            entity_value_relationship = request.POST.get(
                'entity_value_relationship')
            early_entity_value_relationship = request.POST.get(
                'early_entity_value_relationship')
            delete = request.POST.get('delete', None)

            # 删除数据，删除后则退出函数
            if delete == 'delete':
                mysql_handler.delete_relation(file=file, dialog_id=int(
                    dialog_id), entity_value_relationship=entity_value_relationship)

                return JsonResponse({
                    'code': 200,
                    'message': '删除成功',
                })

            labeled = mysql_handler.confirm_mark(server,
                                                 {'dialog_id': dialog_id,
                                                  'file': file
                                                  })
            '''
            查到有标签后，则执行更新标签的命令，否则执行插入数据的命令
            '''
            if labeled != None:
                df = pd.DataFrame(labeled)
                has = df[df['entity_value_relationship'].isin(
                    [entity_value_relationship, early_entity_value_relationship])].shape[0]
            else:
                has = 0
            if has == 0:
                # 插入label
                _ = mysql_handler.update_marked(server,
                                                {'server': server, 'dialog_id': dialog_id,
                                                 'entity_value_relationship': entity_value_relationship, 'file': file},
                                                True)
                if _ == 1:
                    return JsonResponse({
                        'code': code,
                        'message': '插入标签',
                    })
                else:
                    logger_running.error('插入标签失败，当前传入label: {}, 数据库label: {}, status: {}, file: {}'.format(
                        entity_value_relationship, labeled, _, file))
                    return JsonResponse({
                        'code': 500,
                        'message': '插入标签失败',
                    })
            else:
                # 更新label
                _ = mysql_handler.update_marked(server,
                                                {'server': server, 'dialog_id': dialog_id,
                                                 'entity_value_relationship': entity_value_relationship, 'file': file,
                                                 'early_entity_value_relationship': early_entity_value_relationship})
                if _ >= 1:
                    return JsonResponse({
                        'code': code,
                        'message': '更新标签',
                    })
                else:
                    logger_running.error('更新标签失败，当前传入label: {}, 数据库label: {}, status: {}, file: {}'.format(
                        entity_value_relationship, labeled, _, file))
                    return JsonResponse({
                        'code': 500,
                        'message': '更新标签失败',
                    })
        elif server == 'twotuples':
            uuid = request.POST.get('uuid')
            label = request.POST.get('label')
            ner = request.POST.get('ner')
            _tuple = request.POST.get('tuple')

            # 更新label
            status_code = mysql_handler.update_marked(server,
                                                      {'server': server, 'uuid': uuid,
                                                       'label': label, 'ner': ner, 'tuple': _tuple,
                                                       'file': file})
            # print(label, labeled, label == labeled)
            if status_code == 0:
                code = 201
                status = 0

            else:
                code = 200
                status = 1

            if status == 1:
                return JsonResponse({
                    'code': code,
                    'marked': label,
                    'message': '请求成功',
                })
            else:
                logger_running.error('标注失败，当前传入label: {} status: {}, file: {}, uuid: {}'.format(
                    label, status, file, uuid))
                return JsonResponse({
                    'code': code,
                    'message': '更新失败',
                })


def mark_multiclassification(request):
    file = request.POST.get('filename')
    server = file.split('.')[1]
    code = 200
    if server == 'multiclassification':
        uuid = request.POST.get('uuid')
        label = request.POST.get('label')
        status_code = mysql_handler.update_marked(server,
                                                  {'server': server, 'uuid': uuid,
                                                   'label': label,
                                                   'file': file})
        # print(label, labeled, label == labeled)
        if status_code == 0:
            code = 201
            status = 0
        else:
            code = 200
            status = 1

        if status == 1:
            return JsonResponse({
                'code': code,
                'marked': label,
                'message': '请求成功',
            })
        else:
            logger_running.error('标注失败，当前传入label: {} status: {}, file: {}, uuid: {}'.format(
                label, status, file, uuid))
            return JsonResponse({
                'code': code,
                'message': '更新失败',
            })


def query_filelist(request):
    if request.method == 'GET':
        ip = get_remote_ip(request)
        df = mysql_handler.query_list(0, 0)

        # 返回结果
        return JsonResponse({
            'code': 200,
            'data': df.to_dict(orient='records'),
            'message': '请求成功'
        })


def all_relation_delete(request):
    if request.method == 'GET':
        dialog_id = int(request.GET.get('dialog_id'))
        filename = request.GET.get('filename')

        status = mysql_handler.all_relation_delete(filename, dialog_id)

        # 返回结果
        return JsonResponse({
            'code': 200,
            'data': status,
            'message': '请求成功'
        })
