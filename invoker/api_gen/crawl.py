import asyncio

import aiohttp
import simplejson as json

api_list_proj = "http://bapi.bilibili.co/api/project/list?limit=9999&group_id=87"
api_get_cat_id = "http://bapi.bilibili.co/api/project/get?limit=9999&id="
api_list_cat = "http://bapi.bilibili.co/api/interface/list_cat?limit=9999&catid="
api_get_api = "http://bapi.bilibili.co/api/interface/get?id="
t = '&token='
token = 'f750f7c8391900599096'
proj_id, proj_in, cat_id, api_id, api = [], {}, [], [], {}


async def get_proj_id():
    async with aiohttp.ClientSession() as session:
        async with session.get(api_list_proj + t + token) as resp:
            data = json.loads((await resp.read()).decode('utf8'))['data']['list']
            for x in data:
                if x['_id'] not in [801]:
                    proj_id.append(x['_id'])
                    proj_in[x['_id']] = x['name']


async def get_cat_id(pid):
    async with aiohttp.ClientSession() as session:
        async with session.get(api_get_cat_id + pid + t + token) as resp:
            data = json.loads((await resp.read()).decode('utf8'))['data']['cat']
            for x in data:
                if ' (测试' not in x['name'] and ' (test' not in x['name']:
                    cat_id.append(x['_id'])


async def get_api_id(cid):
    async with aiohttp.ClientSession() as session:
        async with session.get(api_list_cat + cid + t + token) as resp:
            data = json.loads((await resp.read()).decode('utf8'))['data']['list']
            for x in data:
                api_id.append(x['_id'])


async def get_api(aid):
    async with aiohttp.ClientSession() as session:
        async with session.get(api_get_api + aid + t + token) as resp:
            data = json.loads((await resp.read()).decode('utf8'))['data']
            if data['uid'] == 999999 and (not api.get(data['path']) or
                                          api[data['path']]['up_time'] < data['up_time']):
                api[data['path']] = data


def get_api_and_service():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.wait([get_proj_id()]))
    loop.run_until_complete(asyncio.wait([get_cat_id(str(p)) for p in proj_id]))
    loop.run_until_complete(asyncio.wait([get_api_id(str(c)) for c in cat_id]))
    loop.run_until_complete(asyncio.wait([get_api(str(a)) for a in api_id]))
    services = {}
    for x in api.values():
        services[x['project_id']] = proj_in[x['project_id']]
    return api, services
