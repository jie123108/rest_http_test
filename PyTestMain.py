# coding=utf8

import os
import json
from rest_http_test import httpclient as http
from rest_http_test import httptest
from rest_http_test.funcs import *
from rest_http_test import *
from dotmap import DotMap as dotdict

DINGDING_TOKEN = os.environ["DINGDING_TOKEN"]

test_tel = "10022224444"
def username():
    return "jie123108"

age=18
address = "china shenzhen"
def new_username():
    return "jie123108@163.com"

def get_save_data_as_json(name):
    save_data = httptest.get_save_data(name)
    return dotdict(json.loads(save_data or '{}'))

def get_sms_code():
    jso = get_save_data_as_json("Test SMS Send")
    #print("jso:", jso)

    return str(jso.data.code)

def get_token():
    jso = get_save_data_as_json("Test Reg OK")
    return str(jso.data.token)


def get_user_id():
    jso = get_save_data_as_json("Test Reg OK")
    return str(jso.data.user_id)

def json_fmt_ex(s):
    if not s:
        return ''

    try:
        jso  = json.loads(s)
    except Exception, ex:
        log.error("loads(", s, ") failed! err:", str(ex))

    if jso:
        replace_fields = {"code": "###", "token": "###", "user_id": "0"}
        text = table_format_ex(jso, 0, replace_fields)
        return text
    else:
        return s

def send_msg_to_dingding(test, testname, error):
    uri = "https://oapi.dingtalk.com/robot/send?access_token=" + DINGDING_TOKEN
    headers = http.NewHeaders()
    headers["Content-Type"] = "application/json"
    timeout = 10
    msg = """服务监控[%s]出错了:
    %s
    """ % (testname, error)
    body = json.dumps({"msgtype": "text","text": {"content": msg}})
    res = http.HttpPost(uri, body, headers, timeout)
    if res.status != 200:
        log.error("send message to dingding failed! err: %s, request[%s]",
            res.status, res.req_debug)
    else:
        body = json.loads(res.body)
        if body.get("errcode") == 0:
            log.warn(RED("服务监控[%s]出错了, 已成功发送消息到钉钉" % (testname)))
        else:
            log.error(RED("服务监控[%s]出错了, 发送消息到钉钉出错了" % (testname)))
# http://eli.thegreenplace.net/2014/04/02/dynamically-generating-python-test-cases/
test_blocks = """
=== Test SMS Send
--- request
POST /account/sms/send
{"tel": "`test_tel`"}
--- timeout
1.01
--- more_headers
Host: test.com
Content-Type: application/json
--- error_code
200
--- response_body json_fmt_ex
{"data":{"code":"0"}, "ok": true}
--- response_body_filter
json_fmt_ex
--- response_body_save

=== Test Reg Code Invalid
--- request
POST /account/reg
{"code": "0000", "tel": "`test_tel`","username": "`username()`"}
--- more_headers
Host: test.com
Content-Type: application/json
--- error_code
200
--- response_body json_fmt
{"reason": "ERR_CODE_INVALID", "ok": false}
--- response_body_filter
json_fmt

=== Test Reg OK
--- request
POST /account/reg
{"code": "`get_sms_code()`", "tel": "`test_tel`","username": "`username()`"}
--- more_headers
Host: test.com
Content-Type: application/json
--- error_code
200
--- response_body json_fmt_ex
{"data": {"token": "###", "user_id": "###"}, "ok": true}
--- response_body_filter
json_fmt_ex
--- response_body_save

=== Test Userinfo Set
--- request
POST /account/user_info/set
{"age": `age`, "address": "`address`", "username": "`new_username()`"}
--- more_headers
Host: test.com
Content-Type: application/json
X-Token: `get_token()`
--- error_code
200
--- response_body json_fmt_ex
{"ok": true}
--- response_body_filter
json_fmt_ex
--- response_body_save

=== Test Userinfo Get Token Invalid
--- request
GET /account/user_info/get
--- more_headers
X-Token: Invalid-Token
--- error_code
401
--- response_body json_fmt
{"reason": "ERR_TOKEN_INVALID", "ok": false}
--- response_body_filter
json_fmt

=== Test Userinfo Get OK
--- request
GET /account/user_info/get
--- more_headers
X-Token: `get_token()`
--- error_code
200
--- response_body json_fmt
{"ok": true, "data": {"tel": "`test_tel`33", "user_id": "`get_user_id()`", "age": "`age`", "address": "`address`", "username": "`new_username()`"}}
--- response_body_filter
json_fmt

"""

"""
=== Test Userinfo Check by Schema
--- request
GET /account/user_info/get
--- more_headers
X-Token: `get_token()`
--- error_code
200

--- response_body_schema
{
    "type" : "object",
    "properties" : {
        "ok" : {"type" : "boolean", "enum": [true]},
        "reason": {"type": "string"},
        "data" : {"type" : "object",
            "properties": {
                "user_id": {"type": "integer"},
                "usename": {"type": "string"},
                "tel": {"type": "string"},
                "age": {"type": "integer"},
                "address": {"type": "string"}
            },
            "required": ["user_id", "username"]
        }
    },
    "required" : ["ok", "data"]
}

=== Test Userinfo Check Failed
--- request
GET /account/user_info/get
--- more_headers
X-Token: NONE
--- error_code
200

--- on_fail
send_msg_to_dingding

"""

def test_main():
    httptest.run(test_blocks,"http://127.0.0.1:5000", globals())

if __name__ == '__main__':
    from TestLoginServer import startServer
    import thread
    import time
    thread.start_new_thread(startServer, ())
    time.sleep(0.05)
    test_main()


