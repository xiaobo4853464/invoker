# -*- coding: utf-8 -*-
import copy
import functools
import hashlib
import random
import string
import threading
from decimal import Decimal

import invoker.log
import requests
import simplejson as json
from attrdict import AttrDict


def get_item(inst, item, cls):
    try:
        value = super(cls, inst).__getitem__(item)
    except KeyError as e:
        raise AttributeError
    if isinstance(value, (str)):
        try:
            if isinstance(json.loads(value), (dict, list)):
                value = json.loads(value)
                t = Dict(value) if isinstance(value, dict) else List(value)
                return t
        except Exception:
            ...
    if isinstance(value, (dict, list)):
        t = Dict(value) if isinstance(value, dict) else List(value)
        inst.__setitem__(item, t)
        return t
    return value


class Dict(dict):

    def __init__(self, d=None):
        d = d or {}
        if isinstance(d, (str, bytes)):
            try:
                d = json.loads(d)
            except Exception:
                ...
        super().__init__(d)

    def __setattr__(self, key, value):
        super().__setitem__(key, value)

    def __getattr__(self, item):
        return get_item(self, item, Dict)

    def __getitem__(self, item):
        return get_item(self, item, Dict)

    def __iter__(self):
        for x, y in self.items():
            if isinstance(y, (dict, list)):
                yield (x, Dict(y)) if isinstance(y, dict) else (x, List(y))
            else:
                try:
                    if isinstance(json.loads(y), (dict, list)):
                        y = json.loads(y)
                        yield (x, Dict(y)) if isinstance(y, dict) else (x, List(y))
                    else:
                        yield (x, y)
                except Exception as e:
                    yield (x, y)

    def get(self, k, v=None):
        try:
            return get_item(self, k, Dict)
        except Exception as e:
            return v


class List(list):

    def __getitem__(self, item):
        return get_item(self, item, List)

    def __iter__(self):
        self.__n = -1
        return self

    def __next__(self):
        self.__n += 1
        if self.__n == len(self):
            raise StopIteration
        return self[self.__n]


attr_dict = functools.partial(AttrDict._constructor, configuration=list)


def md5_str(content, encoding='utf-8'):
    '''
    计算字符串的MD5值
    :param content:输入字符串
    :param encoding: 编码方式
    :return:
    '''
    m = hashlib.md5(content.encode(encoding))
    return m.hexdigest()


def md5_file(fp, block=1024):
    '''
    计算文件的MD5值
    :param fp:文件路径
    :param block:读取的块大小
    :return:
    '''
    m = hashlib.md5()
    with open(fp, 'rb') as f:
        while 1:
            c = f.read(block)
            if c:
                m.update(c)
            else:
                break
    return m.hexdigest()


def gen_rand_str(length=8, s_type='hex', prefix=None, postfix=None):
    '''
    生成指定长度的随机数，可设置输出字符串的前缀、后缀字符串
    :param length: 随机字符串长度
    :param s_type:
    :param prefix: 前缀字符串
    :param postfix: 后缀字符串
    :return:
    '''
    if s_type == 'digit':
        formatter = "{:0" + str(length) + "}"
        mid = formatter.format(random.randrange(10**length))
    elif s_type == 'ascii':
        mid = "".join([random.choice(string.ascii_letters) for _ in range(length)])
    elif s_type == "hex":
        formatter = "{:0" + str(length) + "x}"
        mid = formatter.format(random.randrange(16**length))
    else:
        mid = "".join([random.choice(string.ascii_letters + string.digits) for _ in range(length)])

    if prefix is not None:
        mid = prefix + mid
    if postfix is not None:
        mid = mid + postfix
    return mid


def low_case_to_camelcase(arg_name):
    '''
    category_id -> categoryId
    :param arg_name:
    :return:
    '''
    args = arg_name.split("_")
    return args[0] + "".join([a.capitalize() for a in args[1:]])


class Counter(object):
    '''
    一个简单的线程安全的计数器,每调用一次则增加1
    C = Counter()
    C.counter
    '''

    def __init__(self, start=0):
        self._counter = start
        self.lock = threading.RLock()

    @property
    def counter(self):
        self.lock.acquire()
        self._counter += 1
        ret = self._counter
        self.lock.release()
        return ret

    @property
    def current(self):
        self.lock.acquire()
        ret = self._counter
        self.lock.release()
        return ret


def merge_dicts(d1, d2):
    '''合并两个dict对象,如果子节点也是dict,同样会被合并'''
    common_keys = set(d1.keys()) & set(d2.keys())
    for k in common_keys:
        if isinstance(d1[k], dict) and isinstance(d2[k], dict):
            d2[k] = merge_dicts(d1[k], d2[k])
    d1.update(d2)
    return d1


def get_str_format(deci, n):
    x = "{:." + str(n) + "f}"
    return x.format(Decimal(deci))


g_msg = ""


def valid_response(expect_response, actual_response):
    global g_msg
    if not (isinstance(expect_response, dict) & isinstance(actual_response, dict)):
        g_msg = "expect_response or actual_response not json, please check!"
        return g_msg

    expect_keys = list(expect_response.keys())
    expect_keys.sort()
    actual_keys = list(actual_response.keys())
    actual_keys.sort()

    if actual_keys != expect_keys:
        g_msg = "These keys not in expect_response" + str(
            [x for x in actual_keys if x not in expect_keys])
        return g_msg

    for expect_key in expect_keys:
        expect_value = expect_response[expect_key]["type"]
        actual_value = actual_response[expect_key]
        if expect_value == "integer" and not isinstance(actual_value, int):
            g_msg = "The actual type of value is not integer:" + expect_key
        elif expect_value == "string" and not isinstance(actual_value, str):
            g_msg = "The actual type of value is not string:" + expect_key
        elif expect_value == "array" and not isinstance(actual_value, list):
            g_msg = "The actual type of value is not list:" + expect_key
        elif expect_value == "object" and not isinstance(actual_value, dict):
            g_msg = "The actual type of value is not json:" + expect_key
        elif expect_value == "object" and isinstance(actual_value, dict):
            valid_response(expect_response[expect_key]["child"], actual_value)
        elif expect_value == "array" and isinstance(actual_value, list):
            for item in actual_value:
                valid_response(expect_response[expect_key]["child"], item)
    return g_msg


def get_key_route(expect_response, key_name, router=None):
    router = copy.deepcopy(router)

    if router is None:
        router = []

    if isinstance(expect_response, dict):
        for key, value in expect_response.items():
            if key_name == key:
                router.append(key)
                if "child" in router:
                    router = [x for x in router if x != "child"]
                router = "/".join(router)
                return router
            elif isinstance(value, dict):
                router.append(key)
                route = get_key_route(value, key_name, router)
                if route:
                    return route
                else:
                    if router:
                        router.pop()


def get_invalid_field(expect_response,
                      actual_response,
                      origin_expect_response,
                      invalid_field_list=None):
    if invalid_field_list is None:
        invalid_field_list = []

    if not (isinstance(expect_response, dict) & isinstance(actual_response, dict)):
        return "invalid date"

    expect_keys = list(expect_response.keys())
    expect_keys.sort()

    actual_keys = list(actual_response.keys())
    actual_keys.sort()

    if actual_keys != expect_keys:
        invalid_field_list.extend([x for x in actual_keys if x not in expect_keys])
        invalid_field_list.extend([x for x in expect_keys if x not in actual_keys])

    common_keys = [x for x in expect_keys if x in actual_keys]

    for key in common_keys:
        expect_value = expect_response[key]["type"]
        actual_value = actual_response[key]
        field_router = get_key_route(origin_expect_response, key)
        field_dict = {
            "filed": field_router,
            "expect_value_type": expect_value,
            "actual_value": actual_value
        }
        if expect_value == "integer" and not isinstance(actual_value, int):
            invalid_field_list.append(field_dict)
        elif expect_value == "string" and not isinstance(actual_value, str):
            invalid_field_list.append(field_dict)
        elif expect_value == "array" and not isinstance(actual_value, list):
            invalid_field_list.append(field_dict)
        elif expect_value == "object" and not isinstance(actual_value, dict):
            invalid_field_list.append(field_dict)
        elif expect_value == "object" and isinstance(actual_value, dict):
            get_invalid_field(expect_response[key]["child"], actual_value, origin_expect_response,
                              invalid_field_list)
        elif expect_value == "array" and isinstance(actual_value, list):
            for item in actual_value:
                get_invalid_field(expect_response[key]["child"], item, origin_expect_response,
                                  invalid_field_list)
    return invalid_field_list


def transform(j):

    def t(k):
        for x in k:
            if 'description' in k[x]:
                del k[x]['description']
            if '$$ref' in k[x]:
                del k[x]['$$ref']
            if 'properties' in k[x]:
                k[x]['child'] = k[x]['properties']
                del k[x]['properties']
                t(k[x]['child'])
            if 'items' in k[x]:
                k[x]['child'] = k[x]['items']['properties']
                del k[x]['items']
                t(k[x]['child'])

    b = json.loads(j).get('properties')
    t(b)
    return b


def read_json(path):
    with open(path, "r", encoding='utf-8') as json_file:
        return json.load(json_file)
