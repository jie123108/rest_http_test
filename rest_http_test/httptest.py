# coding=utf8

import unittest
import httpclient as http
import json
import re
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

code_re = re.compile(r"`[^`]*`")


## 执行，并替换字符串中的`code`部分的内容。
def dynamic_execute(text, env):
    if not text:
        return text

    def execute_and_replace(matchobj):
        text = matchobj.group(0)
        text = text[1:len(text)-1]
        # log.error("`%s` globals: %s", text, json.dumps(globals().keys()))
        value = eval(text, globals(), env)
        assertTrue(value != None, " code `" + text + "` not return")
        return str(value) or ''

    newtext = code_re.sub(execute_and_replace, text)
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
	schema = json.loads(schema_text)
	jschema.Draft4Validator.check_schema(schema)

	return schema

def response_body_save_parse(raw_args, current_section, env):
	return True


## TODO: timeout指令支持。
directives = {
	"request" : {"parse": request_parse},
	"timeout" : {"parse": timeout_parse},
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
	# Check Http Code
	expected_code = 200
	if req_info.error_code and req_info.error_code.args:
		expected_code = req_info.error_code.args
	self.assertEquals(res.status, expected_code,
		"expected error_code [" + str(expected_code)
		+ "], but got [" + str(res.status) + "] reason ["
		+ str(res.body) + "]")

	expected_body = None
	response_body = req_info.response_body
	if response_body and response_body.args:
		# env["req_info"] = req_info
		response_body.args = dynamic_execute(response_body.args, env)
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
				self.assertTrue(matched, u"expected response_body [file:%s], but got [file:%s]" % (
						filename_exp_body, filename_rsp_body))
			else:
				log.error(u"expected response_body[[%s]]", expected_body)
				log.error(u"             but got  [[%s]]", rsp_body)
				self.assertTrue(matched, u"expected response_body [%s], but got [%s]" % (
						short_str(expected_body,1024), short_str(rsp_body, 1024)))
	else:
		response_body_schema = req_info.response_body_schema
		if response_body_schema and response_body_schema.args:
			schema = response_body_schema.args
			try:
				rsp_body = json.loads(rsp_body)
				jschema.validate(rsp_body, schema)
			except jschema.exceptions.ValidationError, ex:
				self.fail(ex)
			except ValueError, ex:
				self.fail(ex)


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
			args.uri = dynamic_execute(args.uri, env)

		more_headers = req_info.more_headers
		myheaders = http.NewHeaders()
		## timeout = req_info.args or 1000*10
		if more_headers:
			# 可以在动态的代码里面,引用req_info.
			# env["req_info"] = req_info
			more_headers.args = dynamic_execute(more_headers.args, env)
			# env.pop("req_info")
			myheaders = parse_headers(more_headers.args)

		if args.body:
			args.body = dynamic_execute(args.body, env)
		# env.pop("req_info")
		if args.uri.startswith("http://") or \
			args.uri.startswith("https://"):
			uri = args.uri
		else:
			uri = url + args.uri

		timeout = 10
		if req_info.timeout:
			timeout = req_info.timeout.args
		assertTrue(method == "GET" or method == "POST", "unexpected http method: " + method)

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
		cost, server_ip = self.getDebugInfo(test)
		if self.showAll:
			self.stream.writeln(FMT % (server_ip, RED("ERROR"), cost))
		elif self.dots:
			self.stream.write(RED('E'))
			self.stream.flush()
		error = self._exc_info_to_string(err, test)
		log.error(RED(error))

	def addFailure(self, test, err):
		# super(HttpTestResult, self).addFailure(test, err)
		cost, server_ip = self.getDebugInfo(test)
		if self.showAll:
			self.stream.writeln(FMT % (server_ip, RED("FAIL"), cost))
		elif self.dots:
			self.stream.write(RED('F'))
			self.stream.flush()
		error = self._exc_info_to_string(err, test)
		log.error(RED(error))

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
		cost, server_ip = self.getDebugInfo(test)
		if self.showAll:
			self.stream.writeln(FMT % (server_ip, GREEN("OK"), cost))
		elif self.dots:
			self.stream.write(GREEN('.'))
			self.stream.flush()


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

