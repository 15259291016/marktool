import base64
import json
import os
import re
import threading
import time
import pymysql
import pandas as pd
import datetime

from django import db
from sqlalchemy import create_engine

from marktool.apps.user.models import User
from marktool.src.utils.logger import logger_mysql
from marktool.src.utils.logger import logger_running
from collections import namedtuple


# conf = 'database-info-stable'
# conf = 'database-info-dev'
config = {
    'host': os.getenv('localhost', '123.60.147.137'),
    'user': os.getenv('user', 'marktool'),
    'passwd': os.getenv('password', 'dZKk44peNi4XBNmp'),
    'database': os.getenv('database', 'marktool'),
    'charset': os.getenv('charset', 'utf8mb4')
}


class MySqlHandler:
    def __init__(self):
        from django.db import connection
        self.conn = connection
        self.driver = connection

    def __del__(self):
        if self.conn:
            self.conn.close()

    def exec(self, sql):
        sql = sql.strip()
        operate = sql.split(' ')[0].lower()
        result = 0
        try:
            cursor = self.conn.cursor()
            if operate == 'select':
                status = cursor.execute(sql)
                # status = cursor.execute(sql)excute
                if status == 0:
                    result = [None]
                else:
                    columns = [col[0] for col in cursor.description]
                    result = [dict(zip(columns, row)) for row in cursor.fetchall()]

            elif operate in ['delete', 'update', 'insert']:
                cursor.execute(sql)
                self.conn.commit()
                result = cursor.rowcount
        except Exception as e:
            print(e)
            cursor().execute(sql)
            self.conn.commit()
            result = cursor.rowcount

            logger_mysql.error('mysql exec error, sql: {}, error: {}'.format(sql, e))
            logger_mysql.error('请求太过频繁')
        finally:
            self.conn.close()

        return result

    def close_conn(self):
        self.conn.close()
        self.cursor.close()

    # ------------------------------- 操作文件 -------------------------------------
    def chrono_break_read(self, filename, origin='origin'):
        # 返回file 在 file_origin 中的结果
        sql = 'SELECT * FROM file_origin WHERE %s="%s"' % (origin, filename)
        result = self.exec(sql)
        return result

    def update_file_origin(self, old, new):
        # 修改 file_origin
        last_change_date = datetime.datetime.now()
        sql = 'UPDATE file_origin SET file="%s", last_change_date="%s" WHERE origin="%s"' % (
            new, last_change_date, old)
        # print('update-file-origin sql: ', sql)
        result = self.exec(sql)
        return result

    def chrono_break_update(self, old, new, serve):
        # 修改各任务数据表
        if serve == 'classification':
            sql = 'UPDATE classification SET file="%s" WHERE file = "%s"' % (
                old, new)
        elif serve == 'multiclassification':
            sql = 'UPDATE multiclassification SET file="%s" WHERE file = "%s"' % (
                old, new)
        elif serve == 'marktool':
            sql = 'UPDATE marktool SET file="%s" WHERE file = "%s"' % (
                old, new)
        elif serve == 'graph':
            sql = 'UPDATE graph SET file="%s" WHERE file = "%s"' % (
                old, new)
        elif serve == 'twotuples':
            sql = 'UPDATE two_tuples SET file="%s" WHERE file = "%s"' % (
                old, new)
        status = self.exec(sql)
        # print('status: ', status, 'sql: ', sql)
        return status

    def download_file(self, file):
        if 'marktool' in file:
            sql = 'select * from marktool where file="%s"' % (file)
        else:
            sql = 'select * from classification where file="%s"' % (file)
        df = pd.read_sql(sql, self.driver)
        return df

    def delete_file(self, file):
        if 'marktool' in file:
            sql = 'delete from marktool where file="%s"' % (file)
        elif 'multiclassification' in file:
            sql = 'delete from multiclassification where file="%s"' % (file)
        elif 'classification' in file:
            sql = 'delete from classification where file="%s"' % (file)
        elif 'graph' in file:
            sql1 = 'delete from graph where file="%s";' % (file)
            sql2 = 'delete from entity_relationship where file="%s";' % (file)
            self.exec(sql1)
            self.exec(sql2)
            sql = 'delete from entity_relationship where file="%s"' % (file)
        elif 'twotuples' in file:
            sql = 'delete from two_tuples where file="%s"' % (file)
        num = self.exec(sql)
        return num

    def query_list(self, pagesize, currpage, ip=None):
        currpage -= 1
        sql1 = 'select file, count(*) as total from marktool group by file limit %d, %d' % (
            pagesize * currpage, pagesize)
        sql2 = 'select file, count(label) as marked from marktool where label <> "" group by file limit %d, %d' % (
            pagesize * currpage, pagesize)
        t0 = time.time()

        df1 = pd.read_sql(sql1, con=self.driver)
        t1 = time.time()

        df2 = pd.read_sql(sql2.replace('\\', ''), con=self.driver)
        t2 = time.time()

        df = pd.merge(df1, df2, on='file', how='left').fillna(0)
        t3 = time.time()
        df.marked = df.marked.astype('int16')
        df.total = df.total.astype('int16')
        logger_mysql.info(
            '查询总数据用时: {}, 查询标注数据用时: {}, 合并用时: {}, ip: {}'.format(t1 - t0, t2 - t1, t3 - t2, ip))
        return df

    def get_tag_distribution(self, tag):
        sql = '''
        SELECT label, count(label) as count, count(label) / (SELECT COUNT(1) from marktool where file like "%s" and label <>"") as p FROM marktool
        WHERE file like "%s"
        GROUP BY label;
        ''' % (tag, tag)

        result = self.exec(sql)
        df = pd.DataFrame(index=[0]).from_records(result)
        return df

    def filename_search(self, filename, server):
        # 文件类型是以英文单词开头，所以判断文件名的首个字母则知道要查询的是文件名还是人民
        # filename = filename + '%' if filename[1] in 'qwertyuiopasdfghjkzxcvbnm' else '%' + filename + '%'
        filename = f"%{filename}%"

        cqa = '''select t1.file, marked, total 
        from (select file, count(*) as total from marktool where file like "%s" group by file) t1 
        left join 
        (select file, count(label) as marked from marktool 
        where label <> "" and file like "%s" group by file) t2 
        on t1.file=t2.file
        ''' % (filename, filename)

        clss = '''select t1.file, marked, total
        from (select file, count(*) as total from classification where file like "%s" group by file) t1 
        left join 
        (select file, count(label) as marked from classification
        where label <> "" and file like "%s" group by file) t2
        on t1.file = t2.file
        ''' % (filename, filename)

        multiclss = '''select t1.file, marked, total
        from (select file, count(*) as total from multiclassification where file like "%s" group by file) t1 
        left join 
        (select file, count(label) as marked from multiclassification
        where label <> "" and file like "%s" group by file) t2
        on t1.file = t2.file
        ''' % (filename, filename)

        twotuples = '''select t1.file, marked, total
        from (select file, count(*) as total from two_tuples where file like "%s" group by file) t1 
        left join 
        (select file, count(label) as marked from two_tuples
        where tuple <> "" and file like "%s" group by file) t2
        on t1.file = t2.file
        ''' % (filename, filename)

        graph = '''select t1.file, t2.marked, count(distinct(dialog_id)) as total
        FROM graph t1 inner join (
            select file, count(distinct(dialog_id)) as marked
            FROM entity_relationship
            where file like "%s"
            group by file
        ) t2 
        where t1.file like "%s" and t1.file = t2.file
        group by file;
        ''' % (filename, filename)

        if server == 'cqa':
            result = self.exec(cqa)
        elif server == 'classification':
            result = self.exec(clss)
        elif server == 'multiclassification':
            result = self.exec(multiclss)
        elif server == 'graph':
            result = self.exec(graph)
        elif server == 'twotuples':
            result = self.exec(twotuples)

        if result[0] is not None:
            result = [row for row in result]
            df = pd.DataFrame().from_records(result).fillna(0)
            df.columns = ['file', 'marked', 'total']
            df.marked = df.marked.astype('int16')
            df.total = df.total.astype('int16')
        else:
            df = pd.DataFrame()
        return df

        # count = []
        # for each in [marktool, clss, twotuples, graph]:
        #     # t0 = time.time()
        #     result = self.exec(each)
        #     # t1 = time.time()
        #     # print(t1-t0)
        #     if result[0] != None:
        #         result = [row for row in result]
        #         df = pd.DataFrame().from_records(result).fillna(0)
        #         df.columns = ['file', 'marked', 'total']
        #         df.marked = df.marked.astype('int16')
        #         df.total = df.total.astype('int16')
        #     else:
        #         df = pd.DataFrame()
        #     count.append(df)
        # return pd.concat(count)

    def read_entity_value(self, dialog_id, filename):
        sql = 'select * from entity_relationship where file like "%s" and dialog_id = "%d"' % (
            filename, dialog_id)
        try:
            result = pd.read_sql(sql, con=self.driver)
            return result
        except Exception as e:
            logger_mysql.error('error: {}, sql: {}'.format(e, sql))

    def get_file_length(self):
        sql = '''select count(*) num from (select distinct file from marktool) a;
        '''
        num = self.exec(sql)
        try:
            return int(num[0]['num'])
        except Exception as e:
            logger_mysql.error('error: {}, num: {}'.format(e, num))

    def all_relation_delete(self, filename, dialog_id):
        sql = '''delete from entity_relationship 
        where file like "%s" and dialog_id = "%d" 
        and (LENGTH(entity_value_relationship) - LENGTH(REPLACE(entity_value_relationship, "#", ''))) / LENGTH("#") >= 2;''' \
              % (filename, dialog_id)
        # print(sql)
        num = self.exec(sql)
        return num

    # ---------------------------------- faq.py -------------------------------------
    def read_faq(self, serve_, department_):
        sql = 'select * from faq where serve_=%s and department_=%s order by id desc limit 10' % (
            repr(serve_), repr(department_))

        result = self.exec(sql)
        if result[0] != None:
            # result = [row for row in result]
            # if result:
            df = pd.DataFrame(index=[0]).from_records(result)
            faq = df.to_dict(orient='records')
            # else:
        # faq = pd.DataFrame()
        else:
            faq = pd.DataFrame().to_dict(orient='records')
        return faq

    def upload_faq(self, sentence_, entity_, type_, name_, time_, department_, serve_):
        sql = '''insert into faq 
        (sentence_, entity_, type_, name_, time_, department_, serve_)
        values (%s, %s, %s, %s, %s, %s, %s)
        ''' % (repr(sentence_), repr(entity_), repr(type_), repr(name_), repr(time_), repr(department_), repr(serve_))

        result = self.exec(sql)
        if result == 1:
            return True
        else:
            return False

    def delete_faq(self, sentence_, type_, name_, department_, serve_):
        sql = '''delete from faq where sentence_=%s and type_=%s and name_=%s and department_=%s
                ''' % (repr(sentence_), repr(type_), repr(name_), repr(department_))
        result = self.exec(sql)
        if result >= 1:
            return True
        else:
            return False

    def search_entity(self, entity_, department_):
        sql = "select * from faq where entity_='%s' and department_='%s'" % (
            entity_, department_)

        result = self.exec(sql)
        if result:
            result = [row for row in result]
            df = pd.DataFrame().from_records(result)
            df.columns = ['id', 'sentence_', 'entity_', 'type_',
                          'name_', 'time_', 'department_', 'serve_']
            return df.to_dict(orient='records')
        else:
            return pd.DataFrame()

    def search_user_not_empty_file_info(self, mclasseng, username, prefix):
        sql = f"SELECT file, creater, is_check, is_pass FROM file_origin WHERE file like '{prefix}%{username}\_%{mclasseng}'"
        result = self.exec(sql)
        if result:
            if result[0] == None:
                return pd.DataFrame()
        return pd.DataFrame(result)

    def everyone_marked_count(self, start_date, end_date):
        classification = '''
        SELECT file, last_change_time
        FROM classification
        WHERE last_change_time >= "%s" and last_change_time <= "%s";
        ''' % (start_date, end_date)

        multiclassification = '''
        SELECT file, last_change_time
        FROM multiclassification '''
        # WHERE last_change_time >= "%s" and last_change_time <= "%s";
        # ''' % (start_date, end_date)


        cqa = '''
        SELECT file, last_change_time
        FROM marktool
        WHERE last_change_time >= "%s" and last_change_time <= "%s";
        ''' % (start_date, end_date)

        entity_relationship = '''
        SELECT file, last_change_time
        FROM entity_relationship
        WHERE last_change_time >= "%s" and last_change_time <= "%s";
        ''' % (start_date, end_date)

        two_tuples = '''
        SELECT file, last_change_date as last_change_time
        FROM two_tuples
        WHERE last_change_date >= "%s" and last_change_date <= "%s";
        ''' % (start_date, end_date)

        # sql = [classification, marktool, entity_relationship, two_tuples]
        # pool = Pool(4)
        # result = pool.map(self.exec, sql)
        # for each in result:
        #     print(each)
        # result = pd.concat([pd.DataFrame(each) for each in result])
        # return result
        count = []
        for each in [cqa, classification, two_tuples, entity_relationship, multiclassification]:
            # t0 = time.time()
            result = self.exec(each)
            # t1 = time.time()
            # print(t1-t0)
            if result[0] != None:
                result = [row for row in result]
                df = pd.DataFrame().from_records(result).fillna(0)
            else:
                df = pd.DataFrame()
            count.append(df)
        return pd.concat(count)

    def search_user_not_empty_file(self, mclasseng, username, prefix):
        '''
            Args:
                prefix: str, 文件名的前缀
        '''
        if mclasseng == 'classification':
            sql = '''select t1.file, marked, total
                    from (select file, count(*) as total from classification where file like "%s" group by file) t1 
                    left join 
                    (select file, count(label) as marked from classification
                    where label <> "" and file like "%s" group by file) t2
                    on t1.file = t2.file
                    ''' % (prefix + '%' + username + '\_%classification', prefix + '%' + username + '\_%classification')
        if mclasseng == 'multiclassification':
            sql = '''select t1.file, marked, total
                    from (select file, count(*) as total from multiclassification where file like "%s" group by file) t1 
                    left join 
                    (select file, count(label) as marked from multiclassification
                    where label <> "" and file like "%s" group by file) t2
                    on t1.file = t2.file
                    ''' % (prefix + '%' + username + '\_%multiclassification', prefix + '%' + username + '\_%multiclassification')
                    # ''' % ('%multiclassification', '%multiclassification')

        elif mclasseng == 'twotuples':
            sql = '''select t1.file, marked, total
                    from (select file, count(*) as total from two_tuples where file like "%s" group by file) t1 
                    left join 
                    (select file, count(label) as marked from two_tuples
                    where tuple <> "" and file like "%s" group by file) t2
                    on t1.file = t2.file
                    ''' % (prefix + '%' + username + '\_%twotuples', prefix + '%' + username + '\_%twotuples')
        elif mclasseng == 'cqa':
            sql = '''select t1.file, marked, total 
                    from (select file, count(*) as total from marktool where file like "%s" group by file) t1 
                    left join 
                    (select file, count(label) as marked from marktool 
                    where label <> "" and file like "%s" group by file) t2 
                    on t1.file=t2.file
                    ''' % (prefix + '%' + username + '\_%marktool',prefix + '%' + username + '\_%marktool')
        elif mclasseng == 'graph':
            sql = '''select t1.file, t2.marked, count(distinct(dialog_id)) as total
                    FROM graph t1 inner join (
                        select file, count(distinct(dialog_id)) as marked
                        FROM entity_relationship
                        where file like "%s"
                        group by file
                    ) t2 
                    where t1.file like "%s" and t1.file = t2.file
                    group by file;
                    ''' % (prefix + '%' + username + '\_%graph', prefix + '%' + username + '\_%graph')
        result = self.exec(sql)
        if result:
            if result[0] is None:
                return pd.DataFrame()
        return pd.DataFrame(result)

    def search_not_empty(self, mclasseng, username):
        if mclasseng == 'classification':
            sql = "select distinct(file) as file from classification where file like '%s'" % ('%' + username + '\_%classification')
        elif mclasseng == 'multiclassification':
            sql = "select distinct(file) as file from multiclassification where file like '%s'" % ('%' + username + '%multiclassification')
        elif mclasseng == 'action':
            sql = "select distinct(file) as file from classification where file like '%s'" % ('%' + username + '\_%action')
        elif mclasseng == 'marktool':
            sql = "select distinct(file) as file from marktool where file like '%s'" % ('%' + username + '\_%marktool')
        elif mclasseng == 'graph' :
            sql = "select distinct(file) as file from graph where file like '%s'" % ('%' + username + '\_%graph')
        elif mclasseng == 'twotuples':
            sql = "select distinct(file) as file from two_tuples where file like '%s'" % ('%' + username + '\_%twotuples')
        elif mclasseng == 'cqa':
            sql = "select distinct(file) as file from marktool where file like '%s'" % ('%' + username + '\_%marktool')
        result = self.exec(sql)
        # if result[0] is None:
        if result[0] is None or result is None:
            return pd.DataFrame()
        return pd.DataFrame(result)

    def req_from_filename(self, filename, username):
        # df, a, b = self.confirm_file(server, filename) 可优化，把下一句的判断提上来
        server = filename.split('.')[-1]
        df, a, b = self.confirm_file(server, filename)
        new_filename = filename
        if 'name' in filename:
            # 筛选选取文件的人已经标过的这个科室的文件
            search_filename = filename.split('_')[0] + '\_' + username + '%'
            file_list = self.search_not_empty(server, search_filename)
            # 把最大的文件id号取出来
            if file_list.shape[0] == 0 or file_list.columns[0] == 0:
                max_file_id = 0
            else:
                file_list = file_list['file'].str.split('_', expand=True)
                try:
                    max_file_id = max([int(re.findall(string=file, pattern='[\d]{1,2}')[
                                      0]) for file in file_list.loc[:, 2].tolist()]) + 1
                except ValueError as e:
                    logger_running.error(e)
                    max_file_id = 0
                except Exception as e:
                    logger_running.error(e)
                    max_file_id = 0
                    # print(file_list.loc[:, 2].tolist())
                    raise
            # new_filename =  + '_' +  + '_' + str(max_file_id) + filename.split('_')[2] + '.' + server
            new_filename = '{}_{}_{}_{}.{}'.format(
                filename.split('_')[0],
                username,
                str(max_file_id),
                filename.split('_')[3].split('.')[0],
                server
            )
            self.replace_filename(server, new_filename, filename)

            if df.shape[0] > 0:
                # 把返回的文件的文件名也替换掉
                df['file'] = new_filename
        return df, a, b, new_filename

    # 取到未分配的文件后，把文件名修改成领取的人
    def replace_filename(self, mclasseng, new_filename, filename):
        if mclasseng == 'classification':
            sql = "UPDATE classification SET file = '%s' where file = '%s'" % (
                new_filename, filename)
        elif mclasseng.lower() == 'multiclassification':
            sql = "UPDATE multiclassification SET file = '%s' where file = '%s'" % (
                new_filename, filename)
        elif mclasseng.lower() == 'marktool':
            sql = "UPDATE marktool SET file = '%s' where file = '%s'" % (
                new_filename, filename)
        elif mclasseng.lower() == 'graph':
            sql = "UPDATE graph SET file = '%s' where file = '%s'" % (
                new_filename, filename)
        elif mclasseng.lower() == 'twotuples':
            sql = "UPDATE two_tuples SET file = '%s' where file = '%s'" % (
                new_filename, filename)

        num = self.exec(sql)
        if num > 0:
            return True
        return False

    # ---------------------------------- mark.py -------------------------------------
    def delete_relation(self, file, dialog_id, entity_value_relationship):
        sql = "DELETE FROM entity_relationship WHERE file='%s' and dialog_id='%d' and entity_value_relationship='%s'" % (
            file, dialog_id, entity_value_relationship)
        num = self.exec(sql)
        return num

    def confirm_file(self, server, file):
        if server == 'marktool':
            sql = "select uuid, context, question, answer, label, file from marktool where file like '%s'" % (
                file)
        elif server == 'action' or server == 'classification':
            sql = "select id, uuid, sentence, label, ner, tuple, file from classification where file like '%s' order by id" % (
                file)
        # elif server == 'action' or server == 'classification' or server == 'multiclassification':
        #     sql = "select id, uuid, sentence, label, ner, tuple, file from classification where file like '%s' order by id" % (
        #         file)
        elif server == 'multiclassification':
            sql = "select uuid, sentence, label,file from multiclassification where file like '%s' order by uuid" % (
                file)
        elif server == 'twotuples':
            sql = "select id, uuid, sentence, label, ner, tuple, file from two_tuples where file like '%s'" % (
                file)
        elif server == 'graph':
            sql = "select dialog_id, sentence_id, role, sentence, entity, file from graph where file like '%s'" % (file)
        else:
            # 空dataframe
            logger_mysql.error('error: {}, server: {}, file: {}'.format(
                '找不到server、file数据', server, file))
            return pd.DataFrame(), ([], []), ''
        result = self.exec(sql)
        if result[0] != None:
            result = [row for row in result]
            df = pd.DataFrame().from_records(result)
        else:
            df = pd.DataFrame()

        if server == 'graph':
            # df = 对话
            if df.shape[0] > 0:
                # df_.columns = ['uuid', 'sentence', 'label', 'file']
                # 如果数据库中存在数据
                # dialog
                df.sort_values(['dialog_id', 'sentence_id'],
                               inplace=True, ascending=True)
                # entity relationship
                category = pd.read_sql(
                    'SELECT * FROM entity_relationship WHERE file="%s"' % file, con=self.driver)
                category.sort_values(
                    ['dialog_id', 'last_change_time'], inplace=True, ascending=True)
                # 提取关系标签
                relation = category[(category["entity_value_relationship"].str.count("#") >= 2) | (category["entity_value_relationship"].isin(['无需标注', '我也不知道怎么标']))]
                relation = relation.groupby('dialog_id').apply(lambda x: x['entity_value_relationship'].tolist()).to_dict()
                # 提取NER
                ner = category[category["entity_value_relationship"].str.count("\$") == 3]
                ner = ner.groupby('dialog_id').apply(lambda x: x['entity_value_relationship'].tolist()).to_dict()
                # print(relation, ner, category)
                a = df.drop_duplicates('dialog_id').sort_values('dialog_id').reset_index(drop=True)[['dialog_id']].to_dict(orient="records")
                # b = category.dialog_id.unique().tolist()
                b = category[(category["entity_value_relationship"].str.count("#") >= 2) | (category["entity_value_relationship"].isin(['无需标注', '我也不知道怎么标']))].dialog_id.unique().tolist()
                b.append(-1)
                # print(relation,a, b)
                i = 0
                for idx, each in enumerate(a):
                    if each['dialog_id'] == b[i]:
                        a[idx]['id'] = idx
                        a[idx]['marked'] = 'sentence-mark'
                        i += 1
                    else:
                        a[idx]['id'] = idx
                        a[idx]['marked'] = 'sentence-no-mark'
                '''
                a: dict,
                    [
                        "a": {
                            "dialog_id": xxx,
                            "id": xx,
                            "mark": x
                        }
                    ] 
                    标注情况，没标注的对话全是0，长度和df的dialog_id.unique().size相同
                b: list, 标过的dialog_id
                label: dict,
                    {
                        "dialog_id": [entity relationship]
                    }
                marked_status: same a, a是中间dict的格式
                '''

                marked_status = pd.DataFrame(a).to_dict(orient='records')
                return df, (relation, ner), marked_status
            else:
                return df, ([], []), []

        return df, [], []

    def confirm_mark(self, server, kwargs):
        if server == 'marktool':
            sql = 'select label from marktool where uuid="%s" and file="%s"' % (
                kwargs['uuid'], kwargs['file'])
        elif server == 'intention' or server == 'action':
            sql = "select label from classification where uuid='%s' and file='%s'" % (
                kwargs['uuid'], kwargs['file'])
        elif server == 'graph':
            sql = "select entity_value_relationship from entity_relationship where dialog_id=%d and file='%s'" % (
                int(kwargs['dialog_id']), kwargs['file'])
        else:
            return ''

        one = self.exec(sql)
        try:
            return one[0]['label']
        except KeyError as e:
            return one
        except TypeError as e:
            logger_mysql.warning(
                'error:{}, kwargs: {}'.format(e, kwargs))
            return None

    def update_marked(self, server, kwargs, sql=False):
        last_change_time = datetime.datetime.now()
        if server == 'marktool':
            sql = "update marktool set context='%s', label='%s', answer='%s', last_change_time='%s' where uuid='%s' and file='%s'" % (kwargs['context'].replace(r"'", '"'), kwargs['label'], kwargs['answer'].replace(r"'", '"'), last_change_time,
                kwargs['uuid'], kwargs['file'])
        elif server == 'classification':
            sql = "update classification set label='%s', ner='%s', tuple='%s', last_change_time='%s' where uuid='%s' and file='%s'" % (
                kwargs['label'], kwargs['ner'], kwargs['tuple'], last_change_time, kwargs['uuid'], kwargs['file'])
        elif server == 'multiclassification':
            sql = "update multiclassification set label='%s' where uuid='%s' and file='%s'" % (kwargs['label'], kwargs['uuid'], kwargs['file'])
        elif server == 'twotuples':
            sql = "update two_tuples set label='%s', ner='%s', tuple='%s', last_change_date='%s' where uuid='%s' and file='%s'" % (
                kwargs['label'], kwargs['ner'], kwargs['tuple'], last_change_time, kwargs['uuid'], kwargs['file'])
        elif server == 'graph':
            if sql == False:
                sql = "update entity_relationship set entity_value_relationship='%s', last_change_time='%s' where dialog_id='%s' and file='%s' and entity_value_relationship='%s'" % (
                    kwargs['entity_value_relationship'], last_change_time,
                    kwargs['dialog_id'], kwargs['file'], kwargs['early_entity_value_relationship'])
            else:
                sql = "insert into entity_relationship (entity_value_relationship, last_change_time, dialog_id, file) values ('%s', '%s', %d, '%s')" % (kwargs['entity_value_relationship'], last_change_time, int(kwargs['dialog_id']), kwargs['file'])

        status = self.exec(sql)
        return status

    # ---------------------------------- user.py -------------------------------------
    def user_login_by_username(self, username):
        user = User.objects.filter(username=username).first()
        return user

    def user_login_by_token(self, token):
        username = json.loads(base64.b64decode(token))['username']
        user = User.objects.filter(username=username).first()
        return user

    def write_user_token(self, username, token, ip):
        last_change_date = datetime.datetime.now()
        sql = 'update user set token="%s", ip="%s", last_change_date="%s" where username="%s"' % (
            token, ip, last_change_date, username)

        status = self.exec(sql)
        # 返回值永远都是1
        return status

    def insert_user(self, username, password, permission, zh_name):
        # 创建用户
        sql = 'insert into user (username, password, permission, zh_name) values ("%s", "%s", %d, "%s")' % (username, password, permission, zh_name)
        status = self.exec(sql)
        # 返回值永远都是1
        return status

    def update_user(self, username, password, permission, zh_name):
        # 修改用户信息
        sql = 'update user set password="%s", permission=%d, zh_name="%s" where username="%s"' % (password, permission, zh_name, username)
        status = self.exec(sql)
        # 返回值永远都是1
        return status

    def update_user_last_login_date(self, username):
        # 修改用户最后登录时间
        last_change_date = datetime.datetime.now()
        sql = 'update user set last_change_date="%s" where username="%s"' % (last_change_date, username)
        status = self.exec(sql)
        # 返回值永远都是1
        return status
    # ---------------------------------- check.py -------------------------------------
    def search_file_origin(self, filename):
        sql = 'SELECT count(1) as count FROM file_origin WHERE file="%s"' % (filename)
        user = self.exec(sql)
        return user[0]

    def submit_check(self, filename, is_check='是'):
        submit_check_date = datetime.datetime.now()
        sql = f"UPDATE file_origin SET is_check='{is_check}', submit_check_date='{submit_check_date}' WHERE file='{filename}';"
        status = self.exec(sql)
        return status

    def insert_file_origin(self, filename, is_check='是'):
        # 标注人员提交质检文件
        submit_check_date = datetime.datetime.now()
        sql = 'INSERT INTO file_origin (file, submit_check_date, is_check) values ("%s", "%s", "%s")' % (
            filename, submit_check_date, is_check
        )
        status = self.exec(sql)
        return status

    def update_file_origin_pass(self, is_pass='是'):
        # 准确率达到95%后，修改file_origin表
        last_change_time = datetime.datetime.now()
        sql = f"UPDATE file_origin SET is_pass='{is_pass}', passed_date='{last_change_time}'"
        status = self.exec(sql)
        return status

    def update_file_check(self, rate, is_pass):
        # rate, is_pass, pass_date
        last_change_time = datetime.datetime.now()
        if is_pass == '是':
            sql = f"UPDATE file_check SET rate='{rate}', is_pass='{last_change_time}', pass_date='{is_pass}'"
        else:
            sql = f"UPDATE file_check SET rate='{rate}', is_pass='{is_pass}'"
        status = self.exec(sql)
        return status

    def query_check_file(self):
        sql = 'SELECT file,creater, submit_check_date, is_pass FROM file_origin WHERE is_check="是"'
        status = self.exec(sql)
        return status

    def insert_check_file(self, check_file, gen_check_file):
        # 质检人员点击质检按钮，保存这条日志
        check_date = datetime.datetime.now()
        sql = 'INSERT INTO file_check (check_file, gen_check_file, check_date) values ("%s", "%s", "%s")' % (
            check_file, gen_check_file, check_date
        )
        status = self.exec(sql)
        return status


