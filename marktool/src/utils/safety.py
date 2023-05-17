import json
import base64

def get_remote_ip(request):
    if 'HTTP_X_FORWARDED_FOR' in request.META.keys():
        ip = request.META['HTTP_X_FORWARDED_FOR']
    else:
        ip = request.META['REMOTE_ADDR']

    return ip


def authorization(request):
    token = request.META.get('HTTP_AUTHORIZATION', 'Bearer ')
    if token != None:
        try:
            user = json.loads(base64.b64decode(token[7:]))
        except:
            return None, None
    else:
        return None, None
    return user, token[7:]