import pandas as pd
import json


def process_medical(file_path):
    df = pd.read_json(file_path)
    data = pd.DataFrame({'role': ["server" for i in range(len(df))], 'sentence': [i[:200] for i in df['text']],
                         'dialog_id': [i for i in range(len(df))], 'sentence_id': [i for i in range(len(df))]})
    data.to_csv(file_path.split('/')[-1].split('.')[0] + '_name_1000_医疗数据.graph', index=False)


def process_dermatologyaction(file_path):
    df = pd.read_csv(file_path)
    a = df[~df['sentence'].str.contains('\d{8,11}')].drop('uuid', axis=1)
    b = a[:5000]
    b['uuid'] = [i for i in range(800000, 805000)]
    col = b.pop('uuid')
    b.insert(loc=0, column='uuid', value=col)
    b.to_csv('dermatologyaction_name_1000_意图5k.multiclassification', index=False)
    print('清洗完成')


def process_txt_to_cqa(file_path):
    f = open(file_path, encoding='utf-8')
    a=''
    for i in f:
        a+=i.replace('\t',',')
    b = a.split('\n')
    df = [j.split(',') for j in b]
    o = pd.DataFrame(
        {'uuid': [df[k][0] for k in range(len(df) - 1)], 'question': [df[k][1] for k in range(len(df) - 1)],
         'answer': [df[k][2] for k in range(len(df) - 1)]})
    o.to_csv('aly.cqa',index=False)
    print('cqa完成')

def process_cqa(file_path):
    df = pd.read_csv(file_path)
    # df = df[df['uuid']==1][:4000].reset_index()
    df = df[df['uuid']==1]
    df = df[df.answer.str.len()<255].reset_index().drop('index',axis=1)
    with open('file.txt','w',encoding='utf-8') as f:
        for i in range(3000):
            a = f'C10000{i}@@##$$：\n'
            b = f'Q10000{i}@@##$$：{df.question[i]}\n'
            c = f'A10000{i}@@##$$：{df.answer[i]}\n\n'
            f.write(a)
            f.write(b)
            f.write(c)
    print('写好了')

def process_xlsx(file_path):
    df = pd.read_excel(file_path)
    print(df)

if __name__ == '__main__':
    # process_medical(r"data/medical.json")
    # process_dermatologyaction(r'data/dermatologyaction_name_1000_试标2w.multiclassification')
    # process_txt_to_cqa(r'data/dev.txt')
    process_cqa('aly.cqa')
    # process_xlsx(r'data/dermatologyaction_牛智超_0_试标2w.xlsx')
