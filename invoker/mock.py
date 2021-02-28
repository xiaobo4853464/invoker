import inspect
from functools import wraps
from typing import Literal

import requests


def visit(method, endpoint):
    if endpoint[0] != "/":
        raise TypeError("The first location of endpoint must be '/'")

    def decorator(function):
        @wraps(function)
        def wrapped(*args, **kwargs):
            req_kwargs = {}
            for k, p in zip(inspect.signature(function).parameters, args):
                req_kwargs[k] = p
            obj = req_kwargs.pop("self")
            req_kwargs.update(kwargs)
            _pre_check_code(req_kwargs.get("code", ""))

            if method == "post":
                r = requests.request(method=method, url=obj.URL + endpoint, headers=obj.HEADER, json=req_kwargs)
            else:
                r = requests.request(method=method, url=obj.URL + endpoint, headers=obj.HEADER, params=req_kwargs)

            r.raise_for_status()
            return r.json()

        return wrapped

    return decorator


def _pre_check_code(code_str, ):
    try:
        compile(code_str, "", "exec")
    except SyntaxError:
        raise SyntaxError(f"Please check your code is or not accord with 'python' code style \n Your code: {code_str}")


class LiveTestMock(object):
    """
    提供控制mock "livetest.bilibili.co" 的能力
    一个服务下可以有多个接口
    一个接口下可以有多个规则
    """
    URL = "http://livetest.bilibili.co"
    HEADER = {"Host": "livetest.bilibili.co"}
    CATEGORIES = Literal["live", "liverpc", "bapis", "http"]

    @visit("post", "/mock-rule/update_rule")
    def update_rule(self, method, id, code, remark=" "):
        """"""

    @visit("get", "/mock-rule/enable_rule")
    def enable_rule(self, id, enable: Literal["true", "false"], method: str):
        """
        开启/关闭 规则
        :param id: 规则 id
        :param enable: True 开启; False 关闭
        :param method: 接口路径
        :return:
        """

    @visit("get", "/mock-rule/delete_rule")
    def delete_rule(self, id, service: str, method: str):
        """
        删除规则
        :param id: 规则 id
        :param service: 服务名
        :param method: 接口路径
        :return:
        """

    @visit("post", "/mock-rule/add_rule")
    def add_rule(self, service: str, method: str, code: str, remark=" "):
        """
        添加接口
        :param service: 服务名
        :param method: 接口路径
        :param code: 使mock 生效的python 代码
        :param remark: 备注
        :return:
        """

    @visit("get", "/mock-manage/status")
    def get_category(self, type: CATEGORIES):
        """"""

    @visit("get", "/mock-manage/cancel")
    def mock_cancel(self, service, env, type):
        """"""

    @visit("get", "/mock-manage/register")
    def mock_register(self, service, env, type):
        """"""

    def get_service_name(self, type: CATEGORIES):
        r = self.get_category(type)
        return [i["service"] for i in r]

    def batch_operate(self, env, operation: Literal["cancel", "register"]):
        """
        提供批量开启/关闭 指定环境的所有mock。
        :param operation:
        :param env:环境信息，如："16"，"31"
        :return:
        """
        if operation == "cancel":
            call = self.mock_cancel
        elif operation == "register":
            call = self.mock_register
        else:
            raise TypeError("operation must be 'register' or 'cancel'")
        types = ["live", "liverpc", "bapis"]
        for t in types:
            service_names = self.get_service_name(t)
            for s in service_names:
                r = call(s, str(env), t)
                print(r)
