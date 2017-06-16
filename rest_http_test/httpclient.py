# coding=utf8
'''
http请求封装
'''

import urllib2
import hashlib
import sys
import socket
import time
try:
    import json as simplejson
except:
    import simplejson
import logging
log = logging.getLogger()

LOG_LEVEL = logging.FATAL
# LOG_LEVEL = logging.INFO

class CaseInsensitiveDict(dict):
    @classmethod
    def _k(cls, key):
        return key.lower() if isinstance(key, basestring) else key

    def __init__(self, *args, **kwargs):
        super(CaseInsensitiveDict, self).__init__(*args, **kwargs)
        self._convert_keys()
    def __getitem__(self, key):
        return super(CaseInsensitiveDict, self).__getitem__(self.__class__._k(key))
    def __setitem__(self, key, value):
        super(CaseInsensitiveDict, self).__setitem__(self.__class__._k(key), value)
    def __delitem__(self, key):
        return super(CaseInsensitiveDict, self).__delitem__(self.__class__._k(key))
    def __contains__(self, key):
        return super(CaseInsensitiveDict, self).__contains__(self.__class__._k(key))
    def has_key(self, key):
        return super(CaseInsensitiveDict, self).has_key(self.__class__._k(key))
    def pop(self, key, *args, **kwargs):
        return super(CaseInsensitiveDict, self).pop(self.__class__._k(key), *args, **kwargs)
    def get(self, key, *args, **kwargs):
        return super(CaseInsensitiveDict, self).get(self.__class__._k(key), *args, **kwargs)
    def setdefault(self, key, *args, **kwargs):
        return super(CaseInsensitiveDict, self).setdefault(self.__class__._k(key), *args, **kwargs)
    def update(self, E={}, **F):
        super(CaseInsensitiveDict, self).update(self.__class__(E))
        super(CaseInsensitiveDict, self).update(self.__class__(**F))
    def _convert_keys(self):
        for k in list(self.keys()):
            v = super(CaseInsensitiveDict, self).pop(k)
            self.__setitem__(k, v)

def NewHeaders():
	return CaseInsensitiveDict()


def headerstr(headers):
    if not headers:
        return ""

    lines = []
    for key in headers:
        if key != "User-Agent":
            value = headers[key]
            lines.append("-H'" + str(key) + ": " + str(value) + "'")

    return ' '.join(lines)


def GetDebugStr(method, url, body, headers, timeout):
    req_debug = ""
    if method == "PUT" or method == "POST":
        debug_body = ''
        content_type = headers.get("Content-Type")
        if content_type == None or content_type.startswith("text") or content_type == 'application/json':
            if len(body) < 1024:
                debug_body = body
            else:
                debug_body = body[0:1023]
        else:
            debug_body = "[[not text body: "  + str(content_type) + "]]"
        req_debug = "curl -v -X " + method + " " + headerstr(headers) + " '" + url + "' -d '" + debug_body + "' -o /dev/null"
    else:
        req_debug = "curl -v -X " + method + " " + headerstr(headers) + " '" + url + "' -o /dev/null"

    return req_debug

class Response(object):
    def __init__(self, data):
        self._data = data

    def __getattr__(self, attr):
        return self._data.get(attr, None)
    def __str__(self):
        return str(self._data)

def HttpReq(method, url, body, headers, timeout):
    timeout = timeout or 10
    headers = headers or NewHeaders()
    req_debug = GetDebugStr(method, url, body, headers, timeout)
    timeout_str = str(timeout)
    if LOG_LEVEL <= logging.INFO:
    	log.info("REQUEST [ %s ] timeout: %s", req_debug, timeout_str)

    res = Response({"status": 500, "body":  None, "headers": NewHeaders()})
    server_ip = ""
    begin = time.time()
    try:
        if method == 'POST':
            req = urllib2.Request(url, data=body, headers=headers)
        else:
            req = urllib2.Request(url, data=None, headers=headers)

        resp = urllib2.urlopen(req, timeout=timeout)
        try:
            (ip, port) = resp.fp._sock.fp._sock.getpeername()
            server_ip = ip
        except Exception, e:
            log.error("resp.fp._sock.fp._sock.getpeername failed! %s", str(e))
    except urllib2.HTTPError, e:
        status = e.code
        body = e.read()
        if LOG_LEVEL <= logging.ERROR:
    		log.error("REQUEST [ %s ] failed! http_code: %s resp: %s", req_debug, status, body)
        res = Response({"status": status, "body":  body or str(e), "headers": NewHeaders()})
    except Exception, e:
        msg = 'REQUEST [ %s ] failed! err: %s' %(req_debug, e)
        if LOG_LEVEL <= logging.ERROR:
    		log.error(msg)
        res = Response({"status": 500, "body":  str(e), "headers": NewHeaders()})
    else:
        status = resp.code
        body = resp.read()
        res = Response({"status": status, "body": body, "headers": resp.headers.dict})

    cost = time.time()-begin
    res.cost = cost
    res.server_ip = server_ip or ""


    if res.status >= 400:
        if LOG_LEVEL <= logging.ERROR:
    		log.error("FAIL REQUEST [ %s ] status: %s, cost: %.3f body: %s", req_debug, res.status, cost, res.body)
    else:
        if LOG_LEVEL <= logging.INFO:
    		log.info ("REQUEST [ %s ] status: %s, cost: %.3f", req_debug, res.status, cost)
    res.req_debug = req_debug

    return res

def HttpGet(url, headers, timeout):
    return HttpReq('GET', url, None, headers, timeout)

def HttpPost(url, body, headers, timeout):
    return HttpReq('POST', url, body, headers, timeout)

class OKJsonResponse(object):
    def __init__(self, status, headers, body, req_debug):
        if isinstance(body, str):
            try:
                resp = simplejson.loads(body)
            except Exception, ex:
                n = status/100
                if n == 2:
                    log.error('decoding response(%s) error : %s', body, ex)
                    resp = {'ok': False, 'reason': "JSON_ERROR", 'data': u'服务器错误'}
                elif n == 3:
                    resp = {'ok': False, 'reason': "3xx", 'data': u'返回状态：' + str(status)}
                elif n == 4:
                    resp = {'ok': False, 'reason': "4xx", 'data': u'请求参数错误：' + str(status)}
                elif n == 5:
                    resp = {'ok': False, 'reason': "5xx", 'data': u'服务器错误：' + str(status)}
                else:
                    resp = {'ok': False, 'reason': "INVALID_RESP_CODE", 'data': u'服务器错误：' + str(status)}

        elif isinstance(body, dict):
            resp = body

        self._body = resp
        self._status = status
        self._headers = headers
        self._req_debug = req_debug

    @property
    def body(self):
        return self._body
    @property
    def status(self):
        return self._status
    @property
    def headers(self):
        return self._headers
    @property
    def req_debug(self):
        return self._req_debug

    @property
    def ok(self):
        return self._body.get('ok')
    @property
    def reason(self):
        return self._body.get('reason')
    @property
    def data(self):
        return self._body.get('data')

    def __str__(self):
        return str(self._body)

def RestHttpReq(method, url, body, headers, timeout):
    res = HttpReq(method, url, body, headers, timeout)
    res_json = OKJsonResponse(res.status, res.headers, res.body, res.req_debug)
    return res_json

def RestHttpPost(url, body, headers, timeout):
    return RestHttpReq('POST', url, body or '', headers, timeout)

def RestHttpGet(url, headers, timeout):
    return RestHttpReq('GET', url, None, headers, timeout)

class RedirectException(BaseException):
    def __init__(self, location):
        self.location = location

class RedirctHandler(urllib2.HTTPRedirectHandler):
    """docstring for RedirctHandler"""

    def http_error_302(self, req, fp, code, msg, headers):
        location = headers["Location"]
        raise RedirectException(location)
    http_error_301 = http_error_303 = http_error_304 = http_error_307 = http_error_302

def GetLocation(url,timeout=25):
    req = urllib2.Request(url)
    debug_handler = urllib2.HTTPHandler()
    opener = urllib2.build_opener(debug_handler, RedirctHandler)

    location = None
    try:
        opener.open(url,timeout=timeout)
    except urllib2.URLError as e:
        if hasattr(e, 'code'):
            error_info = e.code
        elif hasattr(e, 'reason'):
            error_info = e.reason
    except RedirectException as e:
        location = e.location
    if location:
        return location, None
    else:
        return False, error_info

if __name__ == '__main__':
    pass
