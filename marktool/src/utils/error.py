import json
from django.http import HttpResponse

# api地址错误
def api_not_found(request, exception, **kwargs):
    httpResponse = HttpResponse()

    httpResponse.status_code = 204
    httpResponse.content = json.dumps({
            'code': 404,
            'data': 'API 地址错误',
            'message': 'api not found'
        }, ensure_ascii=False)
    return httpResponse

# api内部错误
def api_error(request, **kwargs):
    httpResponse = HttpResponse()

    httpResponse.status_code=202
    httpResponse.content = json.dumps({
            'code': 500,
            'data': '出问题了',
            'message': 'api error'
        }, ensure_ascii=False)
    # logging.error()
    return httpResponse
