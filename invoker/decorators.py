# -*- coding: utf-8 -*-

import functools
import inspect
import queue
import threading
import time
import timeit
from collections import OrderedDict
from functools import wraps
from unittest import skip

import allure
import pytest
from invoker.const import Env, RespCode
from invoker.log import LOGGER


def singleton(cls):
    '''
    单例模式装饰器
    :param cls:
    :return:
    '''
    instances = {}

    def _singleton(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return _singleton


def singleton_with_parameters(cls):
    '''
    检查参数的单例模式装饰器,与singleton的区别为: 相同的初始化参数为同一个实例
    :param cls:
    :return:
    '''
    instances = {}

    def _singleton(*args, **kwargs):
        key = frozenset(inspect.getcallargs(cls.__init__, *args, **kwargs).items())
        if key not in instances:
            instances[key] = cls(*args, **kwargs)
        return instances[key]

    return _singleton


class SingletonIfSameParameters(type):
    '''如果初始化参数一致，则单实例'''

    _instances = {}
    _init = {}

    def __init__(cls, name, bases, dct):
        cls._init[cls] = dct.get('__init__', None)

    def __call__(cls, *args, **kwargs):
        init = cls._init[cls]
        if init is not None:
            key = (cls, args, repr(OrderedDict(kwargs.items())))
        else:
            key = cls

        if key not in cls._instances:
            cls._instances[key] = super(SingletonIfSameParameters, cls).__call__(*args, **kwargs)
        return cls._instances[key]


class MultiThreading(threading.Thread):
    QUEUE = queue.Queue()

    def __init__(self, func, thread_name=None, *args, **kwargs):
        super(MultiThreading, self).__init__(name=thread_name)
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def run(self):
        LOGGER.debug("[Start thread]: {}".format(self.name))
        result = self.func(*self.args, **self.kwargs)
        MultiThreading.QUEUE.put(result)

    def __del__(self):
        MultiThreading.QUEUE.empty()


class MaxRetriesExceeded(Exception):
    pass


def retry(exit_condition, interval=1, retries=10, duration=30):
    '''
    该装饰器可以用于异步业务接口,通过多次调用,确认业务处理完成
    当重试次数\重试时间 任一条件满足,均会退出重试逻辑,抛出异常
    :param exit_condition: 退出条件
    :param interval: 每次等待间隔
    :param retries: 重试次数
    :param duration: 重试时间
    :return:
    '''

    def wrapper(func):

        @wraps(func)
        def _wrapper(*args, **kwargs):
            n = 0
            start = timeit.default_timer()
            while 1:
                ret = func(*args, **kwargs)
                if not exit_condition(ret):
                    n += 1
                    if n > retries or timeit.default_timer() - start > duration:
                        raise MaxRetriesExceeded("unexpected result: {}".format(ret))
                    else:
                        time.sleep(interval)
                else:
                    return ret

        return _wrapper

    return wrapper


def delay(before=False, after=True, sec=3):
    """
    在某个函数执行之前/后 等待n秒后返回
    :param before: 执行之前
    :param after: 执行之后
    :param sec: 等待时间，秒
    """

    def decorator(function):

        @wraps(function)
        def wrapped(*args, **kwargs):
            if after:
                result = function(*args, **kwargs)
                time.sleep(sec)
                return result
            elif before:
                time.sleep(sec)
                return function(*args, **kwargs)

        return wrapped

    return decorator


def cached(func):
    '''
    缓存装饰器,用于function,当传入参数一致,func不会再次执行,而是直接从缓存里取出上次执行结果返回
    :param func:
    :return:
    '''
    cached_items = {}

    @wraps(func)
    def wrap(*args, **kwargs):
        key1 = "".join(map(lambda arg: str(id(arg)), args))
        key2 = OrderedDict(sorted({k: id(v) for k, v in kwargs.items()}.items()))
        key = key1 + "+" + str(key2)
        if key in cached_items:
            return cached_items[key]
        else:
            ret = func(*args, **kwargs)
            cached_items[key] = ret
            return ret

    return wrap


class Singleton:
    '''单实例元类'''

    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, '_instance'):
            orig = super(Singleton, cls)
            cls._instance = orig.__new__(cls, *args, **kwargs)
        return cls._instance


def checkpoint(func):

    @wraps(func)
    def wrapped(*args, **kwargs):
        parameters = inspect.signature(func).parameters
        arguments = list(parameters.keys())
        payload = {
            parameter.name: parameter.default
            for _, parameter in parameters.items()
            if parameter.default is not inspect._empty and parameter.name != "self"
        }
        if arguments[0] == "self":
            arguments.pop(0)
            args_ = args[1:]
        else:
            args_ = None
        if args_:
            for index, val in enumerate(args_):
                arg_name = arguments[index]
                payload[arg_name] = val
        payload.update(kwargs)

        func_name = func.__name__

        expect = payload.get("expect", None)
        actual = payload.get("actual", None)

        if "response" in func_name:
            expect = {"code": RespCode.SUCCESS}
            actual = payload.get("resp")

        tmp = func_name.split("_")

        if expect is None:
            expect = " ".join(tmp[1:])

        msg = "[Expect]: {ex}\n[Actual]: {ac}".format(ex=expect, ac=actual)
        # print(func_name)
        # print(msg)
        with allure.step('checkpoint: \n'):
            allure.attach(msg, func_name)
        func(*args, **kwargs)

    return wrapped


def unimplemented(func):
    '''标识出未完整实现用例逻辑的方法'''

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        case = func.__doc__ or func.__name__
        return skip("unimplemented: {}".format(case))(func)(*args, **kwargs)

    return wrapper


def redmine_issue(issue_id: int):
    '''
    标识已知问题，需提供issue id
    :param issue_id: redmine上的issue id，为整形
    '''

    def wrapper(func):

        @functools.wraps(func)
        def _wrapper(*args, **kwargs):
            return skip(
                "redmine issue: http://redmine.bilibili.com/issues/{}".format(issue_id))(func)(
                    *args, **kwargs)

        return _wrapper

    return wrapper


def obsolete(func):
    '''标识已经废弃的接口，用例跳过执行'''

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return skip("obsolete")(func)(*args, **kwargs)

    return wrapper


def unreleased(version):
    '''
    标识尚未上线的接口
    :param version: release版本号
    :return:
    '''

    def wrapper(func):

        @functools.wraps(func)
        def _wrapper(*args, **kwargs):
            return skip("remove flag `unreleased` after version: {}".format(version))(func)(
                *args, **kwargs)

        return _wrapper

    return wrapper


def procedures_issues(reason=""):

    def decorator(function):

        def wrapped(*args, **kwargs):
            raise Exception("[Procedure issues] {}\n[Function] {}".format(
                reason, function.__name__))

        return wrapped

    return decorator


def tag(*tags):
    """给类或方法添加多个标签"""

    def wrapper(obj):
        if inspect.isfunction(obj):
            specific_fixture_name = "change_env_for_function"
        else:
            specific_fixture_name = "change_env_for_class"

        for tag in tags:
            if tag in filter(lambda x: not x.startswith('__'), Env.__dict__.keys()):
                pytest.mark.usefixtures(specific_fixture_name)(obj)
            pytest.mark.__getattr__(tag)(obj)
        return obj

    return wrapper
