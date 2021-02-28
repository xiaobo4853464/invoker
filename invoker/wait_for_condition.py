import inspect
import math
import time

import allure
import simplejson as json

L = ["test_case,call_method,method_params,total_time,spent_time,count,is_success"]


def wait_for_condition(func, exit_condition, interval=1, time_out=60, **kwargs):
    """

    :param func: 你要请求的方法
    :param exit_condition: 退出条件的方法
    :param interval: 间隔时间
    :param time_out: 超时时间
    :param kwargs: 请求的方法的参数
    :return:
    """
    args = ()
    test_case_name = inspect.stack()[1][3]
    real_kwargs = kwargs
    stringify_real_kwargs = json.dumps(real_kwargs).replace(",", "，")
    start_time = time.time()
    end_time = start_time + time_out
    count = 1
    call_func_name = func.__name__

    while time.time() <= end_time:
        time.sleep(interval)
        resp = func(*args, **real_kwargs)
        if exit_condition(resp):
            count_, total_time, spent_time, is_success = count, time_out, time.time(
            ) - start_time, True
            r = resp
            break
        count += 1
    else:
        print("[Request Time Out]: func_name: {}, params: {}".format(call_func_name, real_kwargs))
        count_, total_time, spent_time, is_success = count, time_out, time_out, False

        r = None

    spent_time = math.ceil(spent_time)
    data_t = tuple(
        str(i) for i in (test_case_name, call_func_name, stringify_real_kwargs, total_time,
                         spent_time, count_, is_success))
    data = ",".join(data_t)

    # 过滤广播数据请求
    if call_func_name != 'post':
        L.append(data)

    with allure.step("call method: <{}>:\n".format(call_func_name)):
        for d, c in zip(data_t, tuple(L[0].split(","))):
            allure.attach(d, c)

    return r
