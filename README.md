rest_http_test
----------

https://github.com/jie123108/rest_http_test

rest\_http\_test is a data-driven test framework for testing restful services. is implementation by python.

### Hello World

[TestHelloWorld.py](TestHelloWorld.py)

```python
# coding=utf8

import thread
import time
import json
import urlparse
from BaseHTTPServer import BaseHTTPRequestHandler,HTTPServer

# Test Hello Server
class HelloWorldHandler(BaseHTTPRequestHandler):
    #Handler for the GET requests
    def do_GET(self):
        url = urlparse.urlparse(self.path)
        qs = urlparse.parse_qs(url.query)
        key = qs.get("key")
        key = key[0] if key else ""
        self.send_response(200)
        self.send_header('Content-type','text/plain')
        self.end_headers()
        self.wfile.write("Hello " + key)
        return

def startServer():
    server = HTTPServer(('', 1234), HelloWorldHandler)
    server.serve_forever()

key="lxj"
def TestHelloWorld():
    blocks = """
=== Test Hello World
--- request
GET /test/hello?key=`key`
--- timeout
1.01
--- more_headers
Host: test.com
--- error_code
200
--- response_body
Hello `key`
--- response_body_save
"""
    from rest_http_test import httptest
    httptest.run(blocks,"http://127.0.0.1:1234", globals())

if __name__ == '__main__':
    thread.start_new_thread(startServer, ())
    time.sleep(0.05)
    TestHelloWorld()
```

# 编写步骤
* 导入相关包:

```python
from rest_http_test import httpclient as http
from rest_http_test import httptest
from rest_http_test.funcs import *
from rest_http_test import *
```

* 编写数据驱动用例

数据驱动用例的语法,请参见<数据驱动用例语法说明>一节

* 启动测试

```python
from rest_http_test import httptest
httptest.run(blocks,"http://127.0.0.1:1234", globals())
```

# 数据驱动用例语法说明

rest_http_test 语法结构参考了`test:nginx`模块. 但是test:nginx只能使用perl编写, 并且只能用于nginx应用的测试. 所以用python实现一个类似的测试框架. 一来Python使用人群更广泛, 二来测试框架也可用于测试其它非nginx类的Web程序.


## 基本语法

```
=== 测试用例1
--- 测试数据段1 过滤函数
--- 测试数据段2 过滤函数1 过滤函数2
段数据
=== 测试用例2
--- 测试数据段1
段数据
--- 测试数据段2
```

## 过滤函数

* 测试数据段后面,可设置0到多个`过滤函数`, `过滤函数`按从左到右顺序作用于该段的数据上. `过滤函数在数据段解析时执行`.
* `过滤函数`必须是一个输入一个字符串, 并返回一个字符串的全局函数.
* 支持设置`过滤函数`的段包括:
	* request
	* timeout
	* more_headers
	* error_code
	* response_body
	* response_body_schema	
	
## 内嵌代码

* 部分数据段支持`内嵌代码`. `内嵌代码`与`过滤函数`的区别在于, `内嵌代码`在测试用例执行时,才动态执行, 此时可以拿到前面测试用例的结果数据. 而`过滤函数`是在解析阶段执行.
* 内嵌代码语法格式为, 在字符串中使用 `` 括起来, 与bash shell中嵌入变量类似, 如果要嵌入大段代码, 需要包装成一个全局函数, 该函数必须返回一个字符串:

```
name="jie123108"
def age():
	return 128

block = """
=== test unit
--- response_body json_fmt
{"name": `name`, "age": "age()"}
--- other section
"""
```
其中: `name`为一个全局变量, `age()` 为一个全局函数. 
`特别说明: 上面的例子中, 由于使用了过滤函数json_fmt(该函数会对输入的json进行解析并格式化), 而json解析时age()不是合法的数字, 所以需要使用双引号""包起来,当成字符串处理. `

* 支持内嵌代码的段包括:
	* request uri
	* request post body
	* more_headers
	* response_body	

## 支持的段包括:

#### request
HTTP请求段, 格式一段为:
* GET:

```
GET /path/to/url?arg=val&arg2=val2
```
* POST:

```
POST http://ip:port/path/to/url
post datas
```

#### timeout
请求超时时间, 单位是秒

#### more_headers
请求头列表, 格式一般为:

```
Host: www.test.com
X-Token: token
```

#### error_code
期待的HTTP响应吗. 

#### response_body
期待的HTTP响应体.

#### response_body_schema
HTTP响应体的json schema.
json schema语法请参考: [json schema](http://json-schema.org/latest/json-schema-core.html)

#### response_body_filter
响应体过滤器, 可以设置一个到多个过滤函数. 过滤函数将作用于返回的响应体上. 
过滤函数要求输入是字符串, 输出也是字符串.

#### response_body_save
保存响应内容到缓存中, 在下一个测试用例中,可通过以下函数,获取该响应体:

```python
name = "response body saved test name"
httptest.get_save_data(name)
```

#### on_fail
响应内容校验失败时的处理函数列表. 可给出一到多个预先定义的函数列表. 函数格式为:	

```python
def send_msg_to_dingding(test, testname, error):
	pass
```
其中:

* test 为单元测试对象, 定义请参见[httptest.py](rest_http_test/httptest.py)
* testname 测试名称
* error 出错信息

## 更多示例

[PyTestMain.py](PyTestMain.py)