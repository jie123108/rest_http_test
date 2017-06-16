# coding=utf8
import json
import logging
log = logging.getLogger()


def xtabs(x):
    if not x:
        return u""
    t = []
    for i in range(x):
        t.append(u'  ')

    return u''.join(t)

def table_format_ex(jso, level, replace_fields):
    lines = []
    jt = type(jso)
    if jt == dict:
        keys = jso.keys()
        keys.sort()
        for k in keys:
            if replace_fields and k in replace_fields:
                value = replace_fields.get(k)
            else:
                value = jso[k]
                vtype = type(value)
                if vtype == dict or vtype == list:
                    value = u"\n" + table_format_ex(value, level + 1, replace_fields)

            if value != None:
            	lines.append(xtabs(level) + k + u":" + unicode(value))
    elif jt == list:
        for i in range(len(jso)):
            value = jso[i]
            vtype = type(value)
            if vtype == dict or vtype == list:
                value = u"\n" + table_format_ex(value, level + 1, replace_fields)

            lines.append(xtabs(level) + str(i) + u":" + unicode(value))

    return "\n".join(lines)

def table_format(jso, level):
    return table_format_ex(jso, level, None)

def json_fmt(s):
    if not s:
        return ''

    try:
        jso  = json.loads(s)
    except Exception, ex:
        log.error(u"loads(%s) failed! err: %s", s, str(ex))
        return s

    if jso:
        return table_format(jso, 0)
    else:
        return s

def trim(string):
    return string.strip()
