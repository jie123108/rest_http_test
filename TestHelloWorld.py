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
    
