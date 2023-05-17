import configparser
import os
import json

# 获取config配置文件


def getConfig(section, key):
    config = configparser.ConfigParser()
    path = os.path.split(os.path.realpath(__file__))[0] + '/../config/database.conf'
    # print(path)
    config.read(path, encoding='utf-8')
    return config.get(section, key)


def generate_label(df, output):
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
