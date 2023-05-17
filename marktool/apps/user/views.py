from django.http import JsonResponse
import time
import pandas as pd

from marktool.src.utils.safety import get_remote_ip
from sqlalchemy import create_engine

#链接数据库
# engine = create_engine('mysql+pymysql://root:12345678@localhost:3306/testdb')
engine = create_engine('mysql+pymysql://marktool:dZKk44peNi4XBNmp@123.60.147.137:3306/marktool?charset=utf8mb4')

# host=123.60.147.137
# user=marktool
# passwd=dZKk44peNi4XBNmp
# database=marktool
# charset=utf8mb4


# Create your views here.
def query_list(request):
    if request.method == 'GET':
        ip = get_remote_ip(request)

        pagesize = int(request.GET.get('pagesize'))
        currpage = int(request.GET.get('currpage'))
        # mclasseng = request.GET.get('mclasseng')
        # 查询每一份文件的总量和标注量
        currpage -= 1
        sql1 = 'select file, count(*) as total from marktool group by file limit %d, %d' % (
            pagesize * currpage, pagesize)
        sql2 = 'select file, count(label) as marked from marktool where label <> "" group by file limit %d, %d' % (
            pagesize * currpage, pagesize)

        df1 = pd.read_sql(sql1, con=engine)

        df2 = pd.read_sql(sql2.replace('\\', ''), con=engine)

        df = pd.merge(df1, df2, on='file', how='left').fillna(0)
        t3 = time.time()
        df.marked = df.marked.astype('int16')
        df.total = df.total.astype('int16')

        # logger_running.info('查询成功')
        # 合并结果
        return JsonResponse({
            'code': 200,
            'data': df.to_dict(orient='records'),
            'message': '请求成功'
        })


def search_user_not_empty_file(request):
    if request.method == 'GET':
        ip = get_remote_ip(request)
        zh_name = request.GET.get('zh_name')
        mclasseng = request.GET.get('mclasseng')
        prefix = request.GET.get('prefix')
        if zh_name != '' and mclasseng != '' and prefix != '':
            str1 = f"{mclasseng}%{zh_name}\_%{prefix}"
            from marktool.apps.user.models import FileOrigin
            from marktool.src.utils.mysql_handler import MySqlHandler
            mysql_handler = MySqlHandler()
            not_empty = mysql_handler.search_user_not_empty_file(
                mclasseng, zh_name, prefix)
            # sql = f"-- SELECT file, creater, is_check, is_pass FROM file_origin WHERE file like '{str1}'"
            #
            # not_empty=pd.read_sql(sql,engine)
            # file marked, total
            data_set =  FileOrigin.objects.filter(file__startswith='graph').filter(file__contains='nzc').filter(file__contains='test')
            if data_set:
                search_result = pd.DataFrame.from_records( FileOrigin.objects.filter(file__startswith='graph').filter(file__contains='nzc').filter(file__contains='test').values())
            else:
                search_result = pd.DataFrame()
            # file, creater, is_check, is_pass
            # if search_result.shape[0] == 0:
            if search_result.empty and not not_empty.empty:
                search_result['file'] = not_empty.file.tolist()
                search_result['creater'] = not_empty.file.tolist()[
                    0].split('_')[1]
                search_result['is_check'] = '否'
                search_result['is_pass'] = ''
            if not_empty.shape[0] == 0 and not search_result.empty:
                # search_result['total_num'] = search_result.file.map(lambda x: x.split('_')[2])
                search_result['total_num'] = search_result.file.map(lambda x: int(x.split('_')[2]))
                search_result['marked'] = 0
                result = search_result
            else:
                result = pd.merge(left=not_empty, right=search_result,
                                  on='file', how='left').fillna('')
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
