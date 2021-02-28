import asyncio
import types

import aioredis
import pymysql
from invoker.config import config
from invoker.conn.conn_mgr import (MemcachedConnectionMgr, MySQLConnectionMgr, RedisConnectionMgr)
from invoker.shell_proxy.client import ShellClient
from invoker.utility import attr_dict


def get_mysql(mysql_login_info=None, cursorcls_as_dict=True):
    if not mysql_login_info:
        # 默认拿service中设置的环境
        mysql_login_info = config.mysql

    mysql = MySQLConnectionMgr(autocommit=True,
                               charset='utf8mb4',
                               cursorclass=pymysql.cursors.DictCursor if cursorcls_as_dict else pymysql.cursors.Cursor,
                               **mysql_login_info).connection.cursor()

    # monkey patch
    def query(self, sql, fetch_all=False):
        try:
            self.execute(sql)
        except Exception as e:
            raise e
        else:
            if isinstance(self.obj, pymysql.cursors.DictCursor):
                if fetch_all:
                    result = [attr_dict(r) if r else attr_dict({}) for r in self.fetchall()]
                else:
                    r = self.fetchone()
                    result = attr_dict(r) if r else attr_dict({})
            else:
                if fetch_all:
                    result = self.fetchall()
                else:
                    result = self.fetchone()

        return result

    mysql.query = types.MethodType(query, mysql)
    return mysql


def get_redis(**kwargs):
    if not kwargs:
        login_info = config.redis
    else:
        temp = config.redis
        temp.update(kwargs)
        login_info = temp

    redis = RedisConnectionMgr(**login_info).client

    def fuzzy_delete(self, exp_key):
        try:
            keys = self.keys(exp_key)
            for key in keys:
                self.delete(key)
        except Exception as e:
            raise e
        return "OK"

    redis.fuzzy_delete = types.MethodType(fuzzy_delete, redis)
    return redis


def get_memcached():
    return MemcachedConnectionMgr(**config.memcached).client


def get_shell():
    return ShellClient(config.ip)


def livetest_redis_sync():
    return RedisConnectionMgr(**config.livetest_redis).client


def livetest_redis_async():
    return asyncio.get_event_loop().run_until_complete(
        aioredis.create_redis_pool('redis://' + config.livetest_redis['host'],
                                   password=config.livetest_redis['password'],
                                   encoding='utf8'))


def livetest2_mysql_sync():
    return get_mysql(config.livetest2_mysql)
