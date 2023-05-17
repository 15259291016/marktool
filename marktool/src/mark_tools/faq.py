import json
import codecs
import os
import datetime
import logging
from marktool.src.utils.mysql_handler import MySqlHandler
from django.http import JsonResponse

'''
CREATE TABLE `mark_tool`.`faq` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `department_` VARCHAR(10) NOT NULL,
  `sentence_` VARCHAR(250) NOT NULL,
  `entity_` VARCHAR(15) NOT NULL,
  `type_` VARCHAR(10) NOT NULL,
  `name_` VARCHAR(6) NOT NULL,
  `time_` TIMESTAMP NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE INDEX `id_UNIQUE` (`id` ASC));
'''

# 日志
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
DATE_FORMAT = "%m/%d/%Y %H:%M:%S %p"
logging.basicConfig(filename='./log/run.log', level=logging.DEBUG,
                    format=LOG_FORMAT, datefmt=DATE_FORMAT)

mysql_handler = MySqlHandler()


def get_timestamp():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def read_json(path):
    try:
        return json.load(codecs.open(path, 'r', encoding='utf-8'))
    except FileNotFoundError as e:
        logging.warning('FileNotFoundError: ' + str(e))
        return {}

# 读取标签的配置文件
def read_config(request):
    if request.method == 'GET':
        department = request.GET.get('department').lower()
        try:
            classification,multiclassification, ner, relation, attribute = {}, {}, {}, {}, {}
            path = os.path.split(os.path.realpath(__file__))[0] + '/./../config/{}/{}.json'
            classification_path = path.format('classification', department)
            multiclassification_path = path.format('multiclassification', department)
            ner_path = path.format('ner', department)
            relation_path = path.format('relation', department)
            attribute_path = path.format('attribute', department)
            classification = read_json(classification_path)
            multiclassification = read_json(multiclassification_path)
            ner = read_json(ner_path)
            relation = read_json(relation_path)
            attribute = read_json(attribute_path)
        except Exception as e:
            logging.error('other error: ' + str(e))
        return JsonResponse({
            'code': 200,
            'data': {
                'config': {
                    'classification': classification,
                    'multiclassification': multiclassification,
                    'ner': ner,
                    'relation': relation,
                    'attribute': [] if attribute == {} else attribute
                }
            },
            'message': '请求成功'
        })
