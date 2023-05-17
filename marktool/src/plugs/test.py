from modelscope.pipelines import pipeline
from modelscope.utils.constant import Tasks

semantic_cls = pipeline(Tasks.information_extraction, 'damo/nlp_bert_relation-extraction_chinese-base')
result = semantic_cls(input='导致这个问题的原因是很多的，比如常见的包皮过长，包茎，病菌，病毒感染等')
# inputs = {
#         "source_sentence": ["目前的症状表现是什么"],
#         "sentences_to_compare": [
#             "问性别",
#             "问年龄",
#             "问症状"
#         ]
#     }


print(result)