# -*- coding: utf-8 -*-
import functools
import hashlib
import re
import time
import urllib
from functools import wraps
from inspect import _empty, signature

import simplejson as j
from invoker.config import config
from invoker.const import Env
from invoker.http import BaseClient


def _set_or_update_node(parent: dict, key: str, d: dict):
    if isinstance(parent.get(key, None), dict):
        parent[key].update(d)
    else:
        parent[key] = d


def hook_params(client: BaseClient, method: str, request: dict, has_token: bool, mix_json: bool):
    """
    自动填充必传的字段
    :param mix_json:
    :param client:
    :param method:
    :param request:
    :param has_token: 特殊接口必须使用该字段
    :return:
    """
    required = {
        'actionKey': 'appkey',
        'appkey': config.appkey,
        'access_key': client.login_info['data']['token'] if client.login_info else '',
        'csrf_token': client.login_info['data']['token'] if client.login_info else '',
        'csrf': client.login_info['data']['csrf'] if client.login_info else '',
        'ts': int(time.time())
    }
    if has_token:
        required["token"] = client.login_info['data']['token'] if client.login_info else ''
    if mix_json:
        request['params'].update(required)
        request['params'] = {k: v for k, v in request['params'].items() if v not in (None, "")}
        restore_key(request['params'])
        request['json'] = {k: v for k, v in request['json'].items() if v not in (None, "")}
        restore_key(request['json'])
    else:
        if method.upper() == "GET":
            if request.get("params"):
                request['params'].update(required)
            else:
                request['params'] = required
            request['params'] = {k: v for k, v in request['params'].items() if v not in (None, "")}
            restore_key(request['params'])
        elif request.get("json"):
            request['json'].update(required)
            request['json'] = {k: v for k, v in request['json'].items() if v not in (None, "")}
            restore_key(request['json'])
        elif isinstance(request.get("data"), dict):  # data有可能不是dict
            request['data'].update(required)
            request['data'] = {k: v for k, v in request['data'].items() if v not in (None, "")}
            restore_key(request['data'])


class UnsuitableEnv(Exception):
    '''环境错误'''


suitable_env = [i for i in config.apollo.config.keys() if i.startswith("FAT")]


def hook_mlive_params(request: dict):
    '''处理管理后台请求传参'''
    if config.env not in suitable_env:
        raise UnsuitableEnv('管理后台的接口只适合在环境{}调用，当前环境是{}，请给用例增加tag标签指定适合的环境'.format(
            suitable_env, config.env))
    required = request['data']
    restore_key(required)
    request['data'] = {'env': 'test', 'params': j.dumps(required)}


def restore_key(Dict):
    '''恢复key名'''
    for x in Dict:
        if x.startswith('int_'):
            Dict[x[4:]] = Dict[x]
            del Dict[x]
        if x.endswith('__'):
            Dict[x[:-2]] = Dict[x]
            del Dict[x]


def hook_headers(client: BaseClient, request: dict):
    '''处理http请求的headers'''
    request['headers'] = {"Host": "api.live.bilibili.co"}
    if client.login_info:
        request['headers'].update({
            "x-bililive-uid":
                str(client.mid),
            "Cookie":
                '; '.join([
                    "SESSDATA=" + client.login_info['data']['session'],
                    "bili_jct=" + client.login_info['data']['csrf']
                ])
        })
    request['headers'].update(client.extra_headers)


def hook_mlive_headers(request: dict):
    '''处理管理后台请求的headers'''
    request['headers'] = {
        'Host': 'uat-mlive.bilibili.co',
        'test': 'live',
        'Content-Type': 'application/x-www-form-urlencoded'
    }


def sign(Dict):
    '''移动端请求签名算法'''
    m = hashlib.md5()
    urlencoded = urllib.parse.urlencode(Dict)
    m.update(bytes(urlencoded + config.app_secret, 'utf8'))
    s = m.hexdigest()
    Dict.update({'sign': s})


def hook_sign(method: str, request: dict, mix_json: bool):
    '''为三种格式数据排序和添加移动端签名'''
    if mix_json:
        temp_dict = dict(**request['params'], **request['json'])
        temp_dict = {k: temp_dict[k] for k in sorted(temp_dict.keys())}
        sign(temp_dict)
        request['params'] = {
            k: temp_dict[k] for k in temp_dict.keys() if k not in request['json'].keys()}
    else:
        if method.upper() == "GET":
            request['params'] = {k: request['params'][k] for k in sorted(request['params'].keys())}
            sign(request['params'])
        elif request.get("json"):
            request['json'] = {k: request['json'][k] for k in sorted(request['json'].keys())}
            sign(request['json'])
        elif isinstance(request.get("data"), dict):  # data有可能不是dict
            request['data'] = {k: request['data'][k] for k in sorted(request['data'].keys())}
            sign(request['data'])


def smart_payload(func):
    '''自动组装payload'''

    @wraps(func)
    def _wrapper(*args, **kwargs):
        func(*args, **kwargs)  # to raise TypeError
        if 'params' not in kwargs.keys():
            parameters = signature(func).parameters
            arguments = list(parameters.keys())
            payload = {
                parameter.name: parameter.default
                for _, parameter in parameters.items()
                if parameter.default is not _empty and parameter.name != "self"
            }
            if arguments[0] == "self":
                arguments.pop(0)
                args = args[1:]
            if args:
                for index, val in enumerate(args):
                    arg_name = arguments[index]
                    payload[arg_name] = val
            payload.update(kwargs)
            return payload
        if isinstance(kwargs['params'], dict):
            payload = kwargs
            return payload

    return _wrapper


def api(rule,
        method="post",
        mix_json=False,
        is_json_req=False,
        arg_handler=None,
        mlive=False,
        has_token=False,
        **kwargs):
    """
    :param mix_json: 路由参数+json参数 调用为True
    :param rule: 接口地址,如果是restful接口,则: /query/<id>/
    :param method: 请求方式 get/post/option ...
    :param is_json_req: 是否是json请求,如果传True，传给requests.request为 json=payload
    :param arg_handler: 定义后,可以更改参数名称,如将驼峰参数名修改为其lower_case
    :param mlive: 是否是管理后台请求
    :param kwargs: 具体参考BaseClient._call_api的请求参数
    :param has_token: 业务上 token 值。
    :return:
    """

    def wrapper(func):

        @wraps(func)
        def _wrapper(self, *fargs, **fkwargs):
            payload = smart_payload(func)(self, *fargs, **fkwargs)
            special_ip = payload.get("special_ip")
            c = re.compile(r'<\S*?>')
            endpoint = rule
            paths = c.findall(endpoint)
            for path in paths:
                tp = path[1:-1]
                if tp not in payload:
                    raise ValueError("invalid restful api rule")
                else:
                    endpoint = endpoint.replace(path,
                                                str(payload.pop(tp)))  # url path must be string
            if arg_handler:
                payload = {arg_handler(k): v for k, v in payload.items()}
            req_kwargs = kwargs.pop("req_kwargs", {})
            if method.upper() == "GET":
                _set_or_update_node(req_kwargs, 'params', payload)
            elif is_json_req:
                _set_or_update_node(req_kwargs, 'json', payload)
            elif mix_json:
                _set_or_update_node(req_kwargs, 'json', payload['params'])
                _set_or_update_node(req_kwargs, 'params',
                                    {k: payload[k] for k in payload if k != 'params'})
            else:
                _set_or_update_node(req_kwargs, 'data', payload)

            if mlive:
                hook_mlive_params(req_kwargs)
                hook_mlive_headers(req_kwargs)
                _set_or_update_node(req_kwargs, 'data', {'real_url': rule})
                _set_or_update_node(req_kwargs, 'data', {'method': mlive})
                return self._call_api('/xlive/internal/live-admin/v1/general_proxy/proxy', 'post',
                                      req_kwargs, **kwargs)

            else:
                hook_params(self, method, req_kwargs, has_token, mix_json)
                hook_headers(self, req_kwargs)
                hook_sign(method, req_kwargs, mix_json)
                return self._call_api(endpoint=endpoint,
                                      method=method,
                                      req_kwargs=req_kwargs,
                                      special_ip=special_ip,
                                      **kwargs)

        return _wrapper

    return wrapper


class GRPCResp(object):

    def __init__(self, resp):
        self._resp = resp

    def __getattr__(self, item):
        return getattr(self._resp, item, None)

    def __getitem__(self, item):
        return self._resp[item]

    def __repr__(self):
        return "(GRPCResp) {content}".format(content=self._resp)


def grpc_proxy(*, service_name=None, path=None, **kwargs):
    """
    :param service_name: 服务名称
    :param path: 接口地址,如果是restful接口,则: /query/<id>/
    :param kwargs: 具体参考BaseClient._call_api的请求参数
    :return:
    """

    def wrapper(func):

        @wraps(func)
        def _wrapper(self, *fargs, **fkwargs):
            payload = smart_payload(func)(self, *fargs, **fkwargs)
            payload = {a: b for a, b in payload.items() if b is not None}
            req_kwargs = kwargs.pop("req_kwargs", {})
            _set_or_update_node(req_kwargs, 'headers', {'Host': 'livetest.bilibili.co'})
            _set_or_update_node(req_kwargs, 'params', {})
            _set_or_update_node(req_kwargs, 'params', {
                'service':
                    service_name if service_name is not None else getattr(self, "SERVICE_NAME")
            })
            _set_or_update_node(req_kwargs, 'params', {'path': path})
            _set_or_update_node(req_kwargs, 'params', {'data': j.dumps(payload)})
            resp = self._call_api('/grpc_proxy', 'get', req_kwargs, **kwargs)
            return GRPCResp(resp)

        return _wrapper

    return wrapper


get = functools.partial(api, method='get')
post = functools.partial(api, method='post')
json = functools.partial(api, is_json_req=True)
rpc = functools.partial(api, mlive="rpc")
grpc = functools.partial(api, mlive="grpc")
mix = functools.partial(api, mix_json=True)
