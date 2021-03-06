# coding=utf8

import unittest
import httpclient as http
import json
import time
import re
import sys
from dotmap import DotMap as dotdict
import jsonschema as jschema
from funcs import *
from . import *

import logging
log = logging.getLogger()

ht_save_data = {}

def get_save_data(section_name):
    return ht_save_data.get(section_name)


class TestDataError(Exception):
    def __init__(self, message):
        super(TestDataError, self).__init__(message)


def assertTrue(assertval, errmsg):
    if not assertval:
        raise TestDataError(errmsg)

code_re = re.compile(r"```.+```|`[^`]+`", re.MULTILINE|re.DOTALL)


## 执行，并替换字符串中的`code`部分的内容。
def dynamic_execute(text, env):
    if not text:
        return text

    def execute_and_replace(matchobj):
        func = matchobj.group(0)
        if func.startswith("```"):
            func = func[3:len(func)-3]
        else:
            func = func[1:len(func)-1]
        # log.error("`%s` globals: %s", func, json.dumps(globals().keys()))
        value = eval(func, globals(), env)
        assertTrue(value != None, " code `" + func + "` not return")
        return unicode(value) or u''

    newtext = code_re.sub(execute_and_replace, text)
    return newtext

def dynamic_execute_ex(obj, field, env):
    text = obj[field]
    if not text:
        return text
    newtext = text

    def execute_and_replace(matchobj):
        obj[field] = newtext
        func = matchobj.group(0)
        if func.startswith("```"):
            func = func[3:len(func)-3]
        else:
            func = func[1:len(func)-1]
        # log.error("`%s` globals: %s", func, json.dumps(globals().keys()))
        try:
            value = eval(func, globals(), env)
        except Exception, ex:
            log.error("eval(%s) failed! ex:%s", func, ex)
            assertTrue(False, ex)
        assertTrue(value != None, " code `" + func + "` not return")
        # log.info("execute code [%s] result: %s", func, str(value))
        return unicode(value) or u''

    while True:
        # 多次执行替换, 这样第一个执行替换后的结果, 能反馈到下一下执行中.
        (newtext, n) = code_re.subn(execute_and_replace, newtext, count=1)
        if n < 1:
            break
    return newtext

class HttpTest(unittest.TestCase):
    pass

def raw_args_eval(raw_args, current_section):
    raw_text = "\n".join(raw_args)
    if raw_text and current_section.funcs:
        for i, func in enumerate(current_section.funcs):
            raw_text = func(raw_text)
    return raw_text

def parse_args(str_args):
    if not str_args:
        return None
    arr = str_args.split("&")
    args = {}
    for i, arg in enumerate(arr):
        pair = arg.split("=")
        key = None
        value = None
        if len(pair) == 1:
            key = pair[0].strip()
            value = ""
        elif len(pair) == 2:
            key = pair[0].strip()
            value = pair[1].strip()
        else:
            log.error("---- invalid arg [%s]", arg)
        if key:
            args[key] = value
    return args

def parse_headers(raw_headers):
    headers = http.NewHeaders()
    header_lines = raw_headers.split('\n')
    for i, line in enumerate(header_lines):
        if line.strip():
            arr = line.split(':')
            assertTrue(len(arr) == 2, "invalid header:[" + line + "]")
            headers[arr[0].strip()]=arr[1].strip()

    return headers

## 去掉空行.
def lines_trim(lines):
    if lines:
        return [line for line in lines if (line and line.strip())]
    return lines

methods = {"GET": True, "POST": True}
def request_parse(raw_args, current_section, env):
    if current_section.funcs:
        request = raw_args_eval(raw_args, current_section)
        raw_args = request.split('\n')

    req_line = raw_args[0]
    arr = req_line.split(' ')
    assertTrue(len(arr) == 2, "invalid request line: " + req_line + " arr len(" + str(len(arr)) + ")")

    method = arr[0]
    assertTrue(methods.get(method) != None, "unexpected http method: " + method)

    args = dotdict({})
    args.method = method
    args.uri = arr[1].strip()
    if method == 'POST':
        raw_args = raw_args[1:]
        args.body = "\n".join(raw_args)
    else:
        args.body = ""

    return args

def timeout_parse(raw_args, current_section, env):
    timeout = raw_args_eval(raw_args, current_section)
    return float(timeout)

def sleep_before_parse(raw_args, current_section, env):
    sleep_before = raw_args_eval(raw_args, current_section)
    return float(sleep_before)

def more_headers_parse(raw_args, current_section, env):
    headers = ''
    raw_args = lines_trim(raw_args)
    if current_section.funcs:
        args = ''.join(raw_args)
        if args:
            for i, func in enumerate(current_section.funcs):
                args = func(args)
                func_name = current_section.func_names[i]
                assertTrue(type(args) == 'string', "more_headers function [" + func_name + "] return a no string value!")

        headers = args
    else:
        headers = "\n".join(raw_args)
    return headers

def error_code_parse(raw_args, current_section, env):
    raw_args = lines_trim(raw_args)
    raw_args = [raw_args_eval(raw_args, current_section)]

    assertTrue(len(raw_args) ==1, "invalid error_code lines: " + str(len(raw_args)))
    error_code = int(raw_args[0])
    assertTrue(error_code != None, "Invalid error_code:" + raw_args[0])

    return error_code

def response_body_parse(raw_args, current_section, env):
    expected_body = raw_args_eval(raw_args, current_section)

    return expected_body



def response_body_filter_parse(raw_args, current_section, env):
    raw_args = lines_trim(raw_args)
    if raw_args:
        funcs = get_func_by_name(raw_args, env)
        return funcs
    else:
        return []

def on_fail_parse(raw_args, current_section, env):
    raw_args = lines_trim(raw_args)
    if raw_args:
        funcs = get_func_by_name(raw_args, env)
        return funcs
    else:
        return []

## http://json-schema.org/latest/json-schema-validation.html
def response_body_schema_parse(raw_args, current_section, env):
    schema_text = raw_args_eval(raw_args, current_section)
    groups = code_re.findall(schema_text)
    if len(groups) == 0: # if have no code
        try:
            schema = json.loads(schema_text)
        except Exception, ex:
            log.error("json schema [[%s]] invalid! %s", schema_text, ex)
            raise ex
        jschema.Draft4Validator.check_schema(schema)

    return schema_text

def response_body_save_parse(raw_args, current_section, env):
    return True


directives = {
    "request" : {"parse": request_parse},
    "timeout" : {"parse": timeout_parse},
    "sleep_before": {"parse": sleep_before_parse},
    "more_headers" : {"parse": more_headers_parse},
    "error_code" : {"parse": error_code_parse},
    "response_body" : {"parse": response_body_parse},
    "response_body_schema": {"parse": response_body_schema_parse},
    "response_body_filter" : {"parse": response_body_filter_parse},
    "response_body_save" : {"parse": response_body_save_parse},
    "on_fail" : {"parse": on_fail_parse},
}


def args_proc(current_section, env):
    if current_section.raw_args:
        secinfo = current_section.secinfo
        if secinfo.parse:
            parse = secinfo.parse
            current_section.args = parse(current_section.raw_args, current_section, env)
        else:
            current_section.args = current_section.raw_args
        current_section.pop("raw_args")
    current_section.pop("secinfo")

def get_func_by_name(arr, env):
    funcs = []
    for i, func in enumerate(arr):
        func = func.strip()
        f = env.get(func)
        if f == None:
            OBJ = globals()
            f = OBJ.get(func)
        assertTrue(f != None, "global function [" + func + "] not found!")
        funcs.append(f)

    return funcs

def block_parse(block, block_pattern):
    lines = None
    if type(block) == list:
        lines = block
    else:
        lines = block.split("\n")

    sections = []
    current_section = None
    for i, line in enumerate(lines):
        if line.startswith(block_pattern):
            section = line[len(block_pattern):].strip()
            if current_section:
                sections.append(current_section)
            current_section = dotdict({'section_name': section})
        else:
            if current_section:
                if current_section.get('content') == None:
                    current_section['content'] = []
                current_section['content'].append(line)

        if i == len(lines)-1 and current_section:
            sections.append(current_section)

    return sections


def section_parse(block, env):
    raw_sections =  block_parse(block, "--- ")
    sections = dotdict({})
    for i, section_info in enumerate(raw_sections):
        section = section_info["section_name"]
        content = section_info["content"]
        arr = re.split(r"\s*", section)
        section_name = arr[0].strip()
        secinfo = directives.get(section_name)
        assertTrue(secinfo != None, "unexpected section : " + section_name)

        current_section = dotdict({"section_name": section_name, "secinfo": secinfo})
        if len(arr) > 1:
            arr = arr[1:]
            current_section.funcs = get_func_by_name(arr, env)
            current_section.func_names = arr

        current_section.raw_args = content
        args_proc(current_section, env)
        sections[current_section["section_name"]] = current_section

    return sections

def section_check(section):
    ## request check, args, method, url
    assertTrue(section.request != None, "'--- request' missing!")

    if section.error_code == None and section.response_body == None and section.response_body_schema == None:
        assertTrue(False, "'--- error_code' or '--- response_body' missing!")
    ## error_code check.

def str_match(string, pattern):
    m = re.match(r"^" + pattern + "$", string)
    return m != None

def short_str(string, slen):
    if not string:
        return string

    if len(string) <= slen:
        return string
    else:
        return string[0:slen-3] + u"+."

FILENAME_COUNTER = 1

def response_check(self, testname, req_info,  res, env):
    global ht_save_data
    global FILENAME_COUNTER
    req_debug = ""
    if self.res and self.res.req_debug:
        req_debug = self.res.req_debug

    # Check Http Code
    expected_code = 200
    if req_info.error_code and req_info.error_code.args:
        expected_code = req_info.error_code.args
    equals = res.status == expected_code
    if not equals:
        errmsg = u"request [%s] \nexpected error_code [%s], but got [%s] reason [%s]" % (
            req_debug, expected_code, res.status, res.body)
        self.assertTrue(equals, errmsg)

    expected_body = None
    response_body = req_info.response_body
    if response_body and response_body.args:
        # env["req_info"] = req_info
        response_body.args = dynamic_execute_ex(response_body, 'args', env)
        # env.pop("req_info")
        expected_body = response_body.args
    rsp_body = res.body

    if req_info.response_body_save:
        ht_save_data[testname] = rsp_body

    response_body_filter = req_info.response_body_filter
    if rsp_body and response_body_filter and response_body_filter.args:
       for i, filter in enumerate(response_body_filter.args):
            if rsp_body:
                rsp_body = filter(rsp_body)

    if expected_body:
        matched = rsp_body == expected_body or str_match(rsp_body, expected_body)
        if not matched:
            ## TODO: 更准确定位差异点。
            if len(rsp_body) > 1000 or len(expected_body) > 1000:
                filename_rsp_body = "./%s.rsp_body.%d.txt" % (testname, FILENAME_COUNTER)
                filename_exp_body = "./%s.exp_body.%d.txt" % (testname, FILENAME_COUNTER)
                FILENAME_COUNTER += 1
                log.error("write debug content to: %s", filename_rsp_body)
                log.error("write debug content to: %s", filename_exp_body)
                write_content(filename_rsp_body, rsp_body)
                write_content(filename_exp_body, expected_body)
                self.assertTrue(matched, u"request [%s] \nexpected response_body [file:%s], but got [file:%s]" % (
                        req_debug, filename_exp_body, filename_rsp_body))
            else:
                log.error(u"expected response_body[[%s]]", unicode(expected_body))
                log.error(u"             but got  [[%s]]", unicode(rsp_body))
                self.assertTrue(matched, u"request [%s] \nexpected response_body [%s], but got [%s]" % (
                        req_debug, expected_body, rsp_body))
    else:
        response_body_schema = req_info.response_body_schema
        if response_body_schema and response_body_schema.args:
            response_body_schema.args = dynamic_execute_ex(response_body_schema, 'args', env)
            schema = json.loads(response_body_schema.args)
            try:
                rsp_body = json.loads(rsp_body)
                jschema.validate(rsp_body, schema)
            except jschema.exceptions.ValidationError, ex:
                self.fail(u"request [" + req_debug + "]'s respone body is invalid:\n" + unicode(ex))
            except ValueError, ex:
                self.fail(u"request [" + req_debug + "]'s respone body is invalid:\n" + unicode(ex))


    return True


def make_test_function(testname, block, url, env):
    ## 支持变量内动态执行的包括：
    ## request:URL, request:POST-BODY, more_headers, response_body
    def http_test_internal(self):
        self.testname = testname
        req_info = section_parse(block, env)
        global G
        G.req_info = req_info

        self.req_info = req_info
        req_info.testname = testname

        section_check(req_info)
        request = req_info.request
        args = request.args
        method = args.method
        # env["req_info"] = req_info
        if args.uri:
            args.uri = dynamic_execute_ex(args, 'uri', env)

        if args.body:
            args.body = dynamic_execute_ex(args, 'body', env)

        more_headers = req_info.more_headers
        myheaders = http.NewHeaders()
        ## timeout = req_info.args or 1000*10
        if more_headers:
            # 可以在动态的代码里面,引用req_info.
            # env["req_info"] = req_info
            more_headers.args = dynamic_execute_ex(more_headers, 'args', env)
            # env.pop("req_info")
            myheaders = parse_headers(more_headers.args)

        # env.pop("req_info")
        if args.uri.startswith("http://") or \
            args.uri.startswith("https://"):
            uri = args.uri
        elif url:
            uri = url + args.uri
        else:
            uri = args.uri

        timeout = 5
        if req_info.timeout:
            timeout = req_info.timeout.args
        assertTrue(method == "GET" or method == "POST", "unexpected http method: " + method)

        sleep_before = 0
        if req_info.sleep_before:
            sleep_before = req_info.sleep_before.args
        if sleep_before > 0:
            time.sleep(sleep_before)

        if method == "GET":
            res = http.HttpGet(uri, myheaders, timeout)
        elif method == "POST":
            res = http.HttpPost(uri, request.args.body, myheaders, timeout)
        else:
            assertTrue(False, "method [%s] not supported" % (method))
        self.res = res
        assertTrue(res != None, "request to '" + uri + "' failed! err:" + str(res.reason))

        return response_check(self, testname, req_info, res, env)

    return http_test_internal

FMT = "@%s --- %s [%.3fs]"

class HttpTestResult(unittest.TextTestResult):
    def __init__(self, stream, descriptions, verbosity):
        super(HttpTestResult, self).__init__(stream, descriptions, verbosity)
        self.tests = []

    def getDebugInfo(self, test):
        cost = 0.0
        server_ip = ""
        try:
            if test and test.get("res"):
                if test.res.cost:
                    cost = test.res.cost
                if test.res.server_ip:
                    server_ip = test.res.server_ip
        except:
            pass

        return cost, server_ip

    def addError(self, test, err):
        # super(HttpTestResult, self).addError(test, err)
        self.tests.append(test)
        cost, server_ip = self.getDebugInfo(test)
        if self.showAll:
            self.stream.writeln(FMT % (server_ip, RED("ERROR"), cost))
        elif self.dots:
            self.stream.write(RED('E'))
            self.stream.flush()
        # error = self._exc_info_to_string(err, test)
        # log.error(RED(error))

    def addFailure(self, test, err):
        # super(HttpTestResult, self).addFailure(test, err)
        self.tests.append(test)
        cost, server_ip = self.getDebugInfo(test)
        if self.showAll:
            self.stream.writeln(FMT % (server_ip, RED("FAIL"), cost))
        elif self.dots:
            self.stream.write(RED('F'))
            self.stream.flush()
        # error = self._exc_info_to_string(err, test)
        # log.error(RED(error))

        testname = test.testname
        req_info = test.req_info
        if req_info and req_info.on_fail:
            on_fail = req_info["on_fail"]
            if on_fail.args:
                for i, callback in enumerate(on_fail.args):
                    callback(test, testname, error)


        # log.error(RED(test.testname + ":" + str(type(test))))

    def addSuccess(self, test):
        # unittest.TestResult.addSuccess(self, test)
        self.tests.append(test)
        cost, server_ip = self.getDebugInfo(test)
        if self.showAll:
            self.stream.writeln(FMT % (server_ip, GREEN("OK"), cost))
        elif self.dots:
            self.stream.write(GREEN('.'))
            self.stream.flush()

class SimpleTestRunner(unittest.TextTestRunner):
    def __init__(self, stream=sys.stderr, descriptions=1, verbosity=1, failfast=False, buffer=False, resultclass=None):
        unittest.TextTestRunner.__init__(self, stream=stream, descriptions=descriptions,
                        verbosity=verbosity, failfast=failfast, buffer=buffer, resultclass=resultclass)

    def run(self, test):
        "Run the given test case or test suite."
        result = self._makeResult()
        test(result)
        # result.printErrors()
        # if not result.wasSuccessful():
        #     self.stream.write("FAILED (")
        #     failed, errored = map(len, (result.failures, result.errors))
        #     if failed:
        #         self.stream.write("failures=%d" % failed)
        #     if errored:
        #         if failed: self.stream.write(", ")
        #         self.stream.write("errors=%d" % errored)
        #     self.stream.writeln(")")
        # else:
        #     pass
        return result

def run(blocks, url, env):
    suite = unittest.TestSuite()
    testcases = block_parse(blocks, "=== ")

    for testcase in testcases:
        testname = testcase.section_name
        testcontent = testcase.content

        test_func = make_test_function(testname, testcontent, url, env)
        func_name = "test_" + re.sub(r"[ #]", "_", testname)

        setattr(HttpTest, func_name, test_func)
        suite.addTest(HttpTest(func_name))
    # 执行测试
    runner = unittest.TextTestRunner(verbosity=2, resultclass=HttpTestResult)
    runner.run(suite)

def exec_one(block, url, env):
    suite = unittest.TestSuite()
    testcases = block_parse(block, "=== ")
    if len(testcases) != 1:
        error("invalid block, find %d blocks" % (len(testcases)))
    testcase = testcases[0]
    testname = testcase.section_name
    testcontent = testcase.content
    test_func = make_test_function(testname, testcontent, url, env)
    func_name = "test_" + re.sub(r"[ #]", "_", testname)

    setattr(HttpTest, func_name, test_func)
    suite.addTest(HttpTest(func_name))
    # 执行测试
    runner = SimpleTestRunner(verbosity=2, resultclass=HttpTestResult)
    # result is: rest_http_test.httptest.HttpTest
    return runner.run(suite).tests[0]
