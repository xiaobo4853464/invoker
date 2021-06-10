# -*- coding: utf-8 -*-
import inspect
import itertools
import os
import re
import signal
import sys
import time
import types

import pytest
import pytest_rerunfailures
import requests
import simplejson as json
from _pytest.mark import Mark, MarkDecorator
from _pytest.nodes import Collector
from _pytest.unittest import TestCaseFunction

from invoker.config import config
from invoker.conn.conns import livetest_redis_sync
from invoker.const import Env
from invoker.data_lib import get_all_data, get_test_data
from invoker.utility import attr_dict


def get_reruns_count(item):
    times = 2
    try:
        times = int(
            requests.get('http://172.22.33.224:897/live-api/case_analyse/rerun', {
                'id': get_raw_id(item),
                'group': group,
                'project': project,
                'branch': branch,
                'env': config.env
            },
                         timeout=0.1).text)
    except Exception as e:
        ...
    return times


def get_reruns_delay(item):
    return 0


def get_case_timeout():
    timeout = 30
    try:
        red = livetest_redis_sync()
        timeout = int(red.get('invoker_timeout'))
    except Exception:
        ...
    return timeout


def timeout_func(signum, frame):
    pytest.fail('用例运行超时，当前超时时间设置为{}秒'.format(case_timeout))


pytest_rerunfailures.get_reruns_count = get_reruns_count
pytest_rerunfailures.get_reruns_delay = get_reruns_delay
ENVS = [i for i in Env.__dict__ if not i.startswith("__")]
raw_ids = {}
result = {}
branch = config.cur_branch
group, project = config.cur_project.values()
case_timeout = get_case_timeout()
lock_name = 'invoker_lock:' + config.env
lock_id = str(time.time())
lock_timeout = case_timeout * 2
unlock_script = """
if (redis.call("get",KEYS[1]) == ARGV[1])
then
    return redis.call("del",KEYS[1])
end
"""


def acquire_session_lock():
    """获取session锁"""
    while 1:
        if livetest_redis_sync().set(lock_name, lock_id, ex=lock_timeout, nx=True):
            print('加锁:' + lock_name)
            print('锁id:' + lock_id)
            return
        print('等待已有Job运行完成...')
        time.sleep(1)


def renew_session_lock():
    """续期session锁"""
    livetest_redis_sync().expire(lock_name, lock_timeout)


def release_session_lock():
    """释放session锁"""
    unlock = livetest_redis_sync().register_script(unlock_script)
    result = unlock(keys=[lock_name], args=[lock_id])
    print('解锁:' + lock_name)
    print('锁id:' + lock_id)


def get_raw_id(item):
    return raw_ids.get(item.nodeid, item.nodeid)


def save_result():

    def save(_pass=True):
        red.zadd(
            'case_run_result:' + ':'.join([group, project, branch, config.env, x]), {
                json.dumps(
                    {
                        'pass': _pass,
                        'spend': result[x][y]['spend'],
                        'start': result[x][y]['start']
                    },
                    sort_keys=True,
                    ensure_ascii=False):
                    int(result[x][y]['start'])
            })

    try:
        red = livetest_redis_sync()
        red.zadd('invoker_user', {'/'.join([group, project]): int(time.time())})
        for x in result:
            for y in result[x]:
                if result[x][y]['setup'] and result[x][y]['call'] and result[x][y]['teardown']:
                    save()
                else:
                    save(False)
    except Exception:
        ...


@pytest.fixture(scope="class")
def change_env_for_class(request):
    request.addfinalizer(restore_env)
    for mark in request.cls.pytestmark:
        if mark.name in ENVS:
            config.env = mark.name


@pytest.fixture(scope="function")
def change_env_for_function(request):
    request.addfinalizer(restore_env)
    for x in request.keywords._markers:
        if x in ENVS:
            config.env = x


def restore_env():
    config.env = config.global_env


def pytest_configure(config):
    for x in ENVS:
        config.addinivalue_line("markers",
                                "{}: mark test to run only on named environment".format(x))
    acquire_session_lock()


def pytest_itemcollected(item: TestCaseFunction):
    """
    取用例的第一行描述当做case的名称
    doc: https://docs.pytest.org/en/latest/writing_plugins.html#_pytest.hookspec.pytest_itemcollected
    """
    func = item.obj
    desc = ""
    if func.__doc__ is not None:
        doc = func.__doc__.strip()
        if doc:
            # 如果没有写注释，按原来的逻辑，取方法名称
            if hasattr(item, "callspec"):
                # 参数化中有 desc 字段，优先显示参数化中的注释，否则逐行显示注释
                if item.callspec.params.get('data') and hasattr(item.callspec.params["data"], "desc"):
                    desc = item.callspec.params["data"].desc
                elif item.callspec.indices:
                    # 兼容mark.parametrize 和数据驱动一起获取数据
                    kw = list(item.callspec.indices.keys())[0]
                    docs = doc.splitlines()
                    base_index = 0
                    base_desc = docs[base_index]
                    params_index = item.callspec.indices[kw] + 1
                    post_desc = docs[params_index if params_index < len(doc.splitlines()) else 0].strip()
                    desc = f"{base_desc} {post_desc}"
            else:
                desc = doc.splitlines()[0]
    if desc:
        raw_id = item._nodeid
        item._nodeid = "{}::{}".format(item._nodeid, desc)
        raw_ids[item._nodeid] = raw_id


def pytest_generate_tests(metafunc):
    # generate each test case with keywords and data driven pattern
    test_module_path = metafunc.module.__file__
    function_name = metafunc.function.__name__
    test_data_path = test_module_path.replace("test_cases", "test_data").replace(".py", ".json")
    all_data = get_all_data(test_data_path)
    if all_data:
        default_data = [d for d in all_data if "test_" not in d]
        for item in default_data:
            # only set data for per class once
            if not hasattr(metafunc.cls, item):
                setattr(metafunc.cls, item, attr_dict(all_data[item]) if all_data[item] else None)
    test_data = get_test_data(test_data_path, function_name)
    if test_data:
        test_data = [attr_dict(d) for d in test_data]
        metafunc.parametrize("data", test_data)


# 获得py的作者
def pytest_make_collect_report(collector: Collector):

    def collect(self):
        return g2

    main_g = collector.collect()
    g1, g2 = itertools.tee(main_g)
    collector.collect = types.MethodType(collect, collector)
    pytest_objects = list(g1)
    if all(inspect.isclass(o.obj) for o in pytest_objects):
        for o in pytest_objects:
            mod_doc = inspect.getdoc(o.module)
            try:
                author = re.search("@author:(.*)", mod_doc).group(1).strip()
            except (AttributeError, IndexError, TypeError):
                author = "unknown"
            marker_ = MarkDecorator(
                Mark(name="allure_label", args=(author, config.env), kwargs={'label_type': 'tag'}))
            collector.add_marker(marker_)


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_setup(item):
    t = time.time()
    cur_result = result.setdefault(get_raw_id(item), {})
    cur_result[len(cur_result) + 1] = {
        'setup': False,
        'call': False,
        'teardown': False,
        'start': t,
        'spend': 0
    }
    signal.signal(signal.SIGALRM, timeout_func)
    signal.setitimer(signal.ITIMER_REAL, case_timeout)
    out = yield
    cur_result[len(cur_result)]['spend'] += int((time.time() - t) * 1000)


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_call(item):
    t = time.time()
    cur_result = result[get_raw_id(item)][len(result[get_raw_id(item)])]
    out = yield
    renew_session_lock()
    signal.setitimer(signal.ITIMER_REAL, 0)
    signal.signal(signal.SIGALRM, signal.SIG_DFL)
    cur_result['spend'] += int((time.time() - t) * 1000)


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_teardown(item, nextitem):
    t = time.time()
    cur_result = result[get_raw_id(item)][len(result[get_raw_id(item)])]
    signal.signal(signal.SIGALRM, timeout_func)
    signal.setitimer(signal.ITIMER_REAL, case_timeout)
    out = yield
    renew_session_lock()
    signal.setitimer(signal.ITIMER_REAL, 0)
    signal.signal(signal.SIGALRM, signal.SIG_DFL)
    cur_result['spend'] += int((time.time() - t) * 1000)


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_makereport(item, call):
    out = yield
    report = out.get_result()
    cur_result = result[get_raw_id(item)][len(result[get_raw_id(item)])]
    cur_result[report.when] = report.outcome == 'passed'


def pytest_sessionfinish(session):
    report_path = "{}/report".format(config.get_project_path)
    os.makedirs(report_path, exist_ok=True)
    with open("{}/environment.properties".format(report_path), "w") as f:
        f.write("Environment={}".format(config.env))
    save_result()


def pytest_unconfigure(config):
    release_session_lock()
