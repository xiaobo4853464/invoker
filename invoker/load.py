from invoker.conn.conns import livetest_redis_sync


def load(tool_name):
    redis = livetest_redis_sync()
    space = {}
    exec(redis.get('executor:tool:' + tool_name), space)
    return space[tool_name]
