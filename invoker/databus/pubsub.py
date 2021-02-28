import redis
import requests
import simplejson as json
from invoker.conn.conns import livetest_redis_sync
from invoker.databus.databus_pb2 import Header


def get_host():
    instances = requests.get(
        'http://172.23.34.16:7171/discovery/fetchs?env=uat&status=1&appid=middleware.databus').json(
        )['data']['middleware.databus']['instances']
    for x in instances:
        for y in x['addrs']:
            if 'databus' in y:
                return y[y.rfind('/') + 1:y.rfind(':')], y[y.rfind(':') + 1:]


def get_color(env):
    info = livetest_redis_sync().hget('fat_env_info', env)
    if not info:
        raise Exception('获取环境信息错误')
    return json.loads(info)['color']


class Pub:

    def __init__(self, key, secret, group, topic, env=None):
        host, port = get_host()
        if env:
            self.c = redis.Redis(host=host,
                                 port=port,
                                 password='{}:{}@{}/topic={}&role=pub&color={}'.format(
                                     key, secret, group, topic, get_color(env)))
        else:
            self.c = redis.Redis(host=host,
                                 port=port,
                                 password='{}:{}@{}/topic={}&role=pub'.format(
                                     key, secret, group, topic))

    def send(self, key='', value={}, metadata={}):
        '''发送消息'''
        return self.c.hset(key, Header(metadata=metadata).SerializeToString(), json.dumps(value))


class Sub:

    def __init__(self, key, secret, group, topic, env=None):
        host, port = get_host()
        if env:
            self.c = redis.Redis(host=host,
                                 port=port,
                                 password='{}:{}@{}/topic={}&role=sub&color={}'.format(
                                     key, secret, group, topic, get_color(env)))
        else:
            self.c = redis.Redis(host=host,
                                 port=port,
                                 password='{}:{}@{}/topic={}&role=sub'.format(
                                     key, secret, group, topic))

    def get(self):
        '''获取消息'''
        return list(map(lambda x: json.loads(x.decode()), self.c.mget('')))

    def commit(self, message):
        '''消费消息'''
        return self.c.set(message['partition'], message['offset'])
