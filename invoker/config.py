# -*- coding: utf-8 -*-
import inspect
import os
import sys

import requests
import simplejson as json

from invoker.const import Env
from invoker.decorators import SingletonIfSameParameters


def get_function_name():
    '''获取正在运行函数(或方法)名称'''
    return inspect.stack()[1][3]


class Apollo(metaclass=SingletonIfSameParameters):

    def __init__(self,
                 config_server_url='http://172.22.33.224:8082',
                 app_id='config',
                 cluster='default',
                 namespace='application.json'):
        self.config_server_url = config_server_url
        self.app_id = app_id
        self.cluster = cluster
        self.url = '{host}/{configs}/{app_id}/{cluster}/{namespace}'.format(
            host=self.config_server_url,
            configs='configs',
            app_id=self.app_id,
            cluster=self.cluster,
            namespace=namespace)
        self.config = json.loads(requests.get(self.url).json()['configurations']['content'])


class _Config:
    apollo = Apollo()
    env = global_env = Env.FAT31  # 默认运行环境

    def get_config_specified_env(self, env):
        return self.apollo.config.get(env)

    @property
    def cur_project(self):
        group, project = '', ''
        url = os.popen('git remote get-url origin').read().strip()
        if url.startswith('git'):
            group, project = url[url.find(':') + 1:url.rfind('.')].split('/')
        if url.startswith('http'):
            group, project = url.split('/')[-2:]
        return {'group': group, 'project': project}

    @property
    def cur_branch(self):
        return os.popen('git name-rev --name-only HEAD').read().strip().split('/')[-1]

    @property
    def get_project_path(self):
        return sys.path[0]

    @property
    def configs(self):
        return self.apollo.config.get(self.env)

    @property
    def memcached(self):
        return self.configs.get(get_function_name())

    @property
    def mysql(self):
        return self.configs.get(get_function_name())

    @property
    def redis(self):
        return self.configs.get(get_function_name())

    @property
    def ip(self):
        return self.configs.get(get_function_name())

    @property
    def appkey(self):
        return self.apollo.config.get(get_function_name())

    @property
    def app_secret(self):
        return self.apollo.config.get(get_function_name())

    @property
    def tidb_test(self):
        return self.apollo.config.get(get_function_name().upper())

    @property
    def tidb_trading(self):
        return self.apollo.config.get(get_function_name())

    @property
    def broadcast_listener(self):
        return self.apollo.config.get(get_function_name().upper())

    @property
    def livetest_redis(self):
        return self.apollo.config.get(get_function_name().upper())

    @property
    def livetest2_mysql(self):
        return self.apollo.config.get(get_function_name().upper())


config = _Config()
