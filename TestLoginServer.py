# coding=utf8
import random
import json
from flask import Flask
from flask import request
app = Flask(__name__)

USER_ID_COUTER = 100
# code cache
codes = {}
#user table
users = {}
#token cache
tokens = {}

def json_ok(data):
    jso = {"ok": True}
    if data:
        jso["data"] = data
    return jso
def json_fail(reason):
    jso = {"ok": False}
    if reason:
        jso["reason"] = reason
    return jso


@app.route("/account/sms/send", methods=['POST'])
def sms_send():
    data = request.get_json(silent=False)
    tel = data["tel"]
    code = ''.join(random.sample("0123456789",4))
    # send code to $tel
    # save code to cache
    codes[tel] = code

    return json.dumps(json_ok({"code": code}))

@app.route("/account/reg", methods=['POST'])
def account_reg():
    data = request.get_json(silent=False)
    tel = data["tel"]
    code = data["code"]
    username = data["username"]
    code_ok = codes.get(tel)
    # code is invalid
    if code != code_ok:
        print("tel: %s, code_ok: %s, request code: %s" % (tel, str(code_ok), str(code)))
        return json.dumps(json_fail("ERR_CODE_INVALID"))
    
    # generate user_id
    global USER_ID_COUTER
    user_id = USER_ID_COUTER
    USER_ID_COUTER += 1

    userinfo = {"username": username, "tel": tel, "user_id": user_id}
    # regisger user to db
    users[tel] = userinfo
    users[user_id] = userinfo

    # create a token
    token = ''.join(random.sample("abcdefghijklmn", 10))
    tokens[token] = user_id

    return json.dumps(json_ok({"token": token, "user_id": user_id}))

@app.route("/account/user_info/set", methods=['POST'])
def account_userinfo_set():
    token = request.headers.get('X-Token', '')
    # get token from cache
    user_id = tokens.get(token)
    # token not exists
    if not user_id:
        return json.dumps(json_fail("ERR_TOKEN_INVALID")), 401
    # get userinfo by user_id
    userinfo = users.get(user_id)
    data = request.get_json(silent=False)
    # update userinfo
    for k, v in data.iteritems():
        userinfo[k] = v
    # save userinfo
    users[user_id] = userinfo 

    return json.dumps(json_ok(None))

@app.route("/account/user_info/get")
def account_userinfo_get():
    token = request.headers.get('X-Token', '')
    # get token from cache
    user_id = tokens.get(token)
    # token not exists
    if not user_id:
        return json.dumps(json_fail("ERR_TOKEN_INVALID")), 401
    # get userinfo by user_id
    userinfo = users.get(user_id)
    return json.dumps(json_ok(userinfo))


def startServer():
    app.run(debug=True, use_reloader=False)

if __name__ == "__main__":
    startServer()
