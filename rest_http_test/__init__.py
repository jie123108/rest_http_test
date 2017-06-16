import logging

# import coloredlogs
# coloredlogs.install()
console = logging.StreamHandler()
# console.setLevel(logging.INFO)
formatter = logging.Formatter(' %(asctime)s - %(filename)s:%(lineno)s - %(name)s - %(message)s')
console.setFormatter(formatter)
log = logging.getLogger()
log.addHandler(console)
log.setLevel(logging.INFO)

import httpclient as http
def SetHttpLogLevel(log_level):
	LEVELS = {
		"debug": logging.DEBUG,
		"info": logging.INFO,
		"warn": logging.WARN,
		"error": logging.ERROR,
		"fatal": logging.FATAL,
	}
	level = LEVELS.get(log_level)
	if level == None:
		log.error("invalid log_level: %s", log_level)
		return
	http.LOG_LEVEL = level

"""
You can use these ANSI escape codes:

Black        0;30     Dark Gray     1;30
Red          0;31     Light Red     1;31
Green        0;32     Light Green   1;32
Brown/Orange 0;33     Yellow        1;33
Blue         0;34     Light Blue    1;34
Purple       0;35     Light Purple  1;35
Cyan         0;36     Light Cyan    1;36
Light Gray   0;37     White         1;37
And then use them like this in your script:

#    .---------- constant part!
#    vvvv vvvv-- the code from above
RED='\033[0;31m'
NC='\033[0m' # No Color
printf "I ${RED}love${NC} Stack Overflow\n"
"""
RED_ = "\033[0;31m"
GREEN_ = "\033[0;32m"
YELLOW_ = "\033[1;33m"

NC_ = "\033[0m"

def RED(msg):
    return RED_ + msg + NC_

def GREEN(msg):
    return GREEN_ + msg + NC_

def YELLOW(msg):
    return YELLOW_ + msg + NC_

def write_content(filename, content):
	try:
		import codecs
		f = codecs.open(filename,'w', "utf-8")
		f.write(content)
		f.close()
	except Exception, ex:
		log.error("write(%s, content) failed! ex: %s", filename, ex)

# current request context (used in eval function)
from dotmap import DotMap as dotdict
G = dotdict({})
