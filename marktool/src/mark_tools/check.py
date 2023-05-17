import os
import pandas as pd
from sqlalchemy import create_engine

from marktool.src.utils.mysql_handler import MySqlHandler
from marktool.src.utils.safety import authorization
from django.http import JsonResponse
from marktool.src.utils.logger import logger_running
from sklearn.metrics import classification_report
from marktool.src.mark_tools.query import zip_files, return_file

mysql_handler = MySqlHandler()


def submit_check(request):
    # 提交质检
    if request.method == 'GET':
        filename = request.GET.get('filename')
        zh_name = request.GET.get('zh_name')

        # 查询是否有这份数据
        search_status = mysql_handler.search_file_origin(filename)
        if search_status['count'] == 1:
            # 有则修改
            submit_status = mysql_handler.submit_check(filename)
            return JsonResponse({
                'code': 200,
                'data': submit_status,
                'message': '提交成功！'
            })
        elif search_status['count'] == 0:
            # 无则新增这条数据
            insert_status = mysql_handler.insert_file_origin(
                filename, '是')
            if insert_status == 1:
                return JsonResponse({
                    'code': 200,
                    'data': insert_status,
                    'message': '提交成功！！'
                })

        return JsonResponse({
            'code': 202,
            'message': '提交失败'
        })


def query_check_file(request):
    # 查询所有质检文件
    if request.method == 'GET':
        result = mysql_handler.query_check_file()
        if result[0] is None:
            result = pd.DataFrame()
        result = pd.DataFrame(result)

        return JsonResponse({
            'code': 200,
            'data': result.to_dict(orient='record'),
            'message': '请求成功'
        })


def check(request):
    # 点击质检按钮
    if request.method == 'GET':
        filename = request.GET.get('filename')
        server = filename.split('.')[1]
        # 标注人员名字
        zh_name = filename.split('_')[1]
        _, token = authorization(request)
        user_info = mysql_handler.user_login_by_token(token)
        # 质检人员名字
        replace_name = "质检人"+user_info.zh_name
        # 标注人员标的数据
        df, _, _ = mysql_handler.confirm_file(server, filename)
        # 质检人员标过的数据                           文件名 + 名字
        df_, _, _ = mysql_handler.confirm_file(server, '_'.join(filename.split('_')[:2]).replace(zh_name, replace_name) + '%')
        if df_.shape[0] > 0:
            # 如果质检人员标的数据没标满，则返回没标完的那一份
            if df_[df_['label'] == ''].shape[0] > 0:
                return JsonResponse({
                    'code': 200,
                    'data': df_[df_['label'] == ''].file.tolist()[0],
                    'message': '这份没标完啊'
                })
            # 过滤质检标过的数据
            max_id = df_.sort_values('file', ascending=False).file.tolist()[0].split('.')[0].split('_')[2]
            new_filename = filename.replace(zh_name, replace_name).replace(str(max_id), str(int(max_id) + 1))
            df = df[df['uuid'].isin(df_.uuid.unique().tolist())]
        else:
            max_id = -1
            new_filename = filename.replace(zh_name, replace_name).replace(str(max_id), str(int(max_id) + 1))
            # 插入check表
            status = mysql_handler.insert_check_file(filename, gen_check_file=new_filename)
            if status == 1:
                logger_running.info('质检人员分配 {}'.format(new_filename))
            else:
                logger_running.info('分配 {} 失败，status: {}'.format(new_filename, status))
        # 筛选10%和上次质检不同的数据
        num = int(df.shape[0]*0.1)
        df_ = df.sample(num)
        # 生成给质检的数据
        df_['file'] = new_filename
        df_['label'] = ''
        engine = create_engine('mysql+pymysql://marktool:dZKk44peNi4XBNmp@123.60.147.137:3306/marktool?charset=utf8mb4')
        if server == 'classification':
            df_.iloc[:,1:].to_sql('classification', con=engine, if_exists='append', index=False)
        elif server == 'multiclassification':
            df_.to_sql('multiclassification', con=engine, if_exists='append', index=False)
        elif server == 'graph':
            df_.to_sql('graph', con=engine, if_exists='append', index=False)
        elif server == 'marktool':
            df_.to_sql('marktool', con=engine, if_exists='append', index=False)
        elif server == 'twotuples':
            df_.to_sql('twotuples', con=engine, if_exists='append', index=False)
        return JsonResponse({
            'code': 200,
            'data': new_filename,
            'message': '质检数据分配成功'
        })


def caculate_rate(request):
    if request.method == 'GET':
        filename = request.GET.get('filename')
        server = filename.split('.')[1]
        # 标注人员名字
        zh_name = filename.split('_')[1]
        _, token = authorization(request)
        user_info = mysql_handler.user_login_by_token(token)
        # 质检人员名字
        replace_name = "质检人"+ user_info.zh_name
        # 质检人员标过的数据                           文件名 + 名字
        df_, _, _ = mysql_handler.confirm_file(server, '_'.join(filename.split('_')[:2]).replace(zh_name, replace_name) + '%')
        if df_.empty:
            return JsonResponse({
                'code':'202',
                'message':"质检员还未对文件质检"
            })
        # 筛选质检人员最大文件
        max_file = df_.sort_values('file', ascending=False).file.tolist()[0]
        df_ = df_[df_['file'] == max_file].sort_values('uuid')
        # 如果质检人员没标完
        if df_[df_['label'] == ''].shape[0] > 0:
            # 提醒 + 跳转
            return JsonResponse({
                'code': 201,
                # 'data': new_filename,
                'message': max_file + ' 没标完'
            })
        # 标注人员标的数据
        df, _, _ = mysql_handler.confirm_file(server, filename)

        df.drop_duplicates('uuid', inplace=True)
        df_.drop_duplicates('uuid', inplace=True)
        df = df[df['uuid'].isin(df_.uuid.tolist())].sort_values('uuid')

        rate_df = pd.DataFrame(classification_report(df_.label.tolist(), df.label.tolist(), output_dict=True)).T
        rate = rate_df.loc["accuracy"]["precision"]
        if rate >= 0.95:
            # 修改file_origin表 is_pass, pass_date
            mysql_handler.update_file_origin_pass()
            # 存入check表 rate, is_pass, pass_date
            mysql_handler.update_file_check(float(rate), '否')
        else:
            mysql_handler.update_file_origin_pass('否')
            # 存入check表 rate, is_pass
            mysql_handler.update_file_check(float(rate), '否')

        rate_df.to_excel('./tmp/{}.xlsx'.format(filename), engine='xlsxwriter')
        zip_files(files='./tmp/{}.xlsx'.format(filename))
        os.remove('./tmp/{}.xlsx'.format(filename))

        return JsonResponse({
            'code': 200,
            'data': rate,
            'message': '请求成功'
        })
