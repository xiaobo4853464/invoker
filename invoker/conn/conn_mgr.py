import logging

import pymemcache
import pymongo
import pymysql
import redis

from invoker.decorators import SingletonIfSameParameters
from invoker.log import LOGGER


class _Proxy(object):

    def __init__(self, obj):
        self.obj = obj

    def __getattr__(self, item):
        return getattr(self.obj, item)

    def __setattr__(self, key, value):
        if key == "obj":
            object.__setattr__(self, key, value)
        else:
            try:
                object.__getattribute__(self, key)
                object.__setattr__(self, key, value)
            except AttributeError:
                setattr(self.obj, key, value)


class _ConnectionProxy(_Proxy):

    def __getattr__(self, item):
        if item == "cursor":
            def _cursor(*args, **kwargs):
                return _CursorProxy(getattr(self.obj, item)(*args, **kwargs))

            return _cursor
        if item == "close":
            def return_null(*args, **kwargs):
                LOGGER.warning(
                    "call `forced_close` if really wanner shutdown the mysql connections")
                return None

            return return_null
        if item == "forced_close":
            return super().__getattr__("close")
        return super(_ConnectionProxy, self).__getattr__(item)


class _CursorProxy(_Proxy):

    def __enter__(self):
        '''不返回self.obj.__enter__，这样会导致不自动打印sql语句'''
        if getattr(self.obj, "__enter__"):  # 不用去捕捉异常
            return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return getattr(self.obj, "__exit__")(exc_type, exc_val, exc_tb)

    def __getattr__(self, item):
        if item == "execute":

            def _execute(*args, **kwargs):
                ret = getattr(self.obj, item)(*args, **kwargs)
                if isinstance(self.obj, pymysql.cursors.Cursor):
                    LOGGER.info(self.obj.mogrify(*args, **kwargs))
                else:
                    LOGGER.info(self.obj.statement)  # 打印sql语句
                return ret

            return _execute
        return super(_CursorProxy, self).__getattr__(item)


class MySQLConnectionMgr(metaclass=SingletonIfSameParameters):
    '''确保只会连接一次mysql'''

    BACKEND_PYMYSQL = "pymysql"
    BACKEND_OFFICIALMYSQL = "mysql-connector-python"

    def __init__(self, **kwargs):
        self._cnx = dict()
        self._backend = self.BACKEND_PYMYSQL
        self.kwargs = kwargs

    @property
    def _official_connection(self):
        try:
            import mysql.connector
        except ImportError:
            LOGGER.error("mysql-connector-python is not installed, switch to pymysql")
            self._backend = self.BACKEND_PYMYSQL
            return self._pymysql_connection
        cnx = self._cnx.get(self.BACKEND_OFFICIALMYSQL, None)
        if cnx is None:
            LOGGER.info("start to connect mysql", extra=self.kwargs)
            cnx = _ConnectionProxy(mysql.connector.connect(**self.kwargs))
            cnx.autocommit = True  # 解决各种疑难杂症...
            self._cnx[self.BACKEND_OFFICIALMYSQL] = cnx
        else:
            if not cnx.is_connected():
                LOGGER.info("trying to reconnect mysql")
                cnx.reconnect()
                cnx.autocommit = True
        return cnx

    @property
    def _pymysql_connection(self):
        cnx = self._cnx.get(self.BACKEND_PYMYSQL, None)
        if cnx is None:
            con_params = self.kwargs.copy()
            cursor_cls = con_params.get('cursorclass')
            if cursor_cls:
                con_params['cursorclass'] = cursor_cls.__name__
            LOGGER.info("start to connect mysql", extra=con_params)
            cnx = _ConnectionProxy(pymysql.connect(**self.kwargs))
            cnx.autocommit_mode = True
            self._cnx[self.BACKEND_PYMYSQL] = cnx
        else:
            if not cnx.open:
                LOGGER.info("trying to reconnect mysql")
                cnx.connect()
        return cnx

    @property
    def backend(self):
        return self._backend

    @backend.setter
    def backend(self, backend):
        if backend == self.BACKEND_OFFICIALMYSQL:
            self._backend = backend
        else:
            self._backend = self.BACKEND_PYMYSQL

    @property
    def connection(self):
        if self.backend == self.BACKEND_OFFICIALMYSQL:
            return self._official_connection
        return self._pymysql_connection


class MongoConnectionMgr(metaclass=SingletonIfSameParameters):

    def __init__(self, **kwargs):
        self._mongo_client = None
        self._connection_params = kwargs

    @property
    def client(self):
        if self._mongo_client is None:
            LOGGER.info("start a new mongo connection", extra=self._connection_params)
            self._mongo_client = pymongo.MongoClient(**self._connection_params)
        return self._mongo_client


class RedisConnectionMgr(metaclass=SingletonIfSameParameters):

    def __init__(self, **kwargs):
        self._redis_client = None
        self._params = kwargs

    @property
    def client(self):
        if self._redis_client is None:
            LOGGER.info("start a redis connection", extra=self._params)
            self._redis_client = redis.StrictRedis(**self._params, decode_responses=True)
        return self._redis_client


class MemcachedConnectionMgr(metaclass=SingletonIfSameParameters):

    def __init__(self, **kwargs):
        self._memcached_client = None
        self._params = kwargs

    @property
    def client(self):
        if self._memcached_client is None:
            LOGGER.info("start a memcached connection", extra=self._params)
            self._memcached_client = pymemcache.client.base.Client(tuple(self._params.values()))
        return self._memcached_client
