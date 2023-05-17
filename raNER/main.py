import datetime
import json
import numpy as np
from flask import Flask as _Flask
from flask.json import JSONEncoder as _JSONEncoder, jsonify

from modelscope.pipelines import pipeline
from modelscope.utils.constant import Tasks
from flask import Flask, request
from flask_cors import CORS,cross_origin
class JsonEncoder(json.JSONEncoder):
    """Convert numpy classes to JSON serializable objects."""
    def default(self, obj):
        if isinstance(obj, (np.integer, np.floating, np.bool_)):
            return obj.item()
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        else:
            return super(JsonEncoder, self).default(obj)
app = Flask('__main__')
cors = CORS(app)
p = pipeline('named-entity-recognition', 'damo/nlp_raner_named-entity-recognition_chinese-base-cmeee')
@app.route('/input',methods=['POST'])
@cross_origin()
def predict():
    assert request.json['sentence'] is not None
    a = p(request.json['sentence'], )
    return json.dumps(a,ensure_ascii=False, cls=JsonEncoder)

if __name__=='__main__':
    app.run(port=5005)
