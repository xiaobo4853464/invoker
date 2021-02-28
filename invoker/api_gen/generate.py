import keyword
import os
import pathlib
import re
import unicodedata

import simplejson as json

from invoker.api_gen import crawl

depth = 0


def scan(r, cur_depth):
    global depth
    cur_depth += 1
    depth = max(depth, cur_depth)
    if isinstance(r, dict):
        for x in r:
            if x and x != 'mock':
                scan(r[x], cur_depth)


def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        pass

    try:
        unicodedata.numeric(s)
        return True
    except (TypeError, ValueError):
        pass

    return False


def writeline(s):
    f.write(str(s) + '\n')


if __name__ == "__main__":
    apis, services = crawl.get_api_and_service()
    current_p_name = os.path.split(os.path.dirname(__file__))[0]
    with open(os.path.dirname(__file__) + '/generation.py', 'w', encoding='utf8') as f:
        writeline('''"""auto generate by generate.py. do not modified!!!"""''')
        writeline('''import abc\n''')
        writeline('''from invoker.http import BaseClient''')
        writeline('''from invoker.utility import Dict''')
        writeline('''from invoker.http.helper import get, post, json\n\n''')
        writeline('class Generation(BaseClient):')
        writeline('    @abc.abstractmethod')
        writeline('    def __init__(self, mid=None, *args, **kwargs):')
        writeline('        super().__init__(*args, **kwargs)')
        writeline('        self.interceptor = lambda r, j: Dict(j)')
        writeline('        self.mid = int(mid) if mid is not None else None')
        writeline('        self.login_info = self.login_info = self.login(self.mid)\n')

        for x in apis:
            p = x[1:].replace('/', '_').replace('-', '_').replace('.', '_')

            if "#" in p:
                continue

            err_param_flag = False

            if apis[x]['method'] == 'GET':
                parms = apis[x]['req_query']
                parm = []

                for y in parms:
                    y['name'] = y['name'].split('=')[0]
                    z = y['name'] + '__' if keyword.iskeyword(y['name']) else y['name']
                    if 'form:"' in z:
                        err_param_flag = True
                        print(p, z)
                        break
                    if z not in parm:
                        parm.append(z)

                if err_param_flag is True:
                    continue

                parm.remove('appkey') if 'appkey' in parm else ...
                parm = ' = None, '.join(parm)
                writeline('    @get("{}")'.format(x))
                if parm:
                    writeline('    def {}(self,{}):'.format(p, (' ' + parm + ' = None')))
                else:
                    writeline('    def {}(self):'.format(p))
            elif apis[x].get('req_body_other'):
                body = json.loads(apis[x]['req_body_other'])['properties']
                scan(body, 0)
                if depth <= 3:
                    writeline('    @post("{}")'.format(x))
                else:
                    writeline('    @json("{}")'.format(x))
                if not body:
                    writeline('    def {}(self):'.format(p))
                else:
                    for y in body:
                        if keyword.iskeyword(y):
                            body[y + '__'] = body[y]
                            del body[y]
                        if is_number(y[0]):
                            body['int_' + y] = body[y]
                            del body[y]
                    writeline('    def {}(self,{}):'.format(
                        p, (' ' + ' = None, '.join([y for y in body]) + ' = None')))
                depth = 0
            else:
                writeline('    @post("{}")'.format(x))
                writeline('    def {}(self):'.format(p))
            writeline("        '''http://bapi.bilibili.co/project/{}/interface/api/{}'''\n".format(
                apis[x]['project_id'], apis[x]['_id']))

    for x, y in services.items():
        interface = {a: b for a, b in apis.items() if b['project_id'] == x}
        y = y.replace("-", "_")
        if not os.path.exists('/'.join([current_p_name, 'cases', y])):
            try:
                os.makedirs('/'.join([current_p_name, 'cases', y]))
                os.makedirs('/'.join([current_p_name, 'cases', y, "test_cases"]))
                os.makedirs('/'.join([current_p_name, 'cases', y, "test_data"]))
                pathlib.Path("/".join([current_p_name, 'cases', y, "test_cases", "__init__.py"])).touch()
                pathlib.Path("/".join([current_p_name, 'cases', y, "test_data", "__init__.py"])).touch()

            except FileExistsError:
                ...
