"""
jsonpath expression:
    https://www.pluralsight.com/blog/tutorials/introduction-to-jsonpath
online tool for testing your json path:
    http://jsonpath.com/
"""
import os

import simplejson as json
from deepdiff import DeepDiff
from jsonpath_ng.ext import parse, parser

from invoker.dict_format import (change_dict_key_pattern, dict_format,
                              exclude_str_root)

projectPath = os.path.join(os.path.dirname(__file__), os.pardir, os.pardir)


def json_get(json, jsonPath):
    '''
    get value form json content with jsonpath
    :json: 
        json string
    :jsonPath:
        jsonpath expression string
        
    return:
        string
    example:
        json = {"team":{"number":10,"tester":"xiaobo"}}
        jsonPath = "$..tester"
        return: xiaobo
    '''
    try:
        jsonPath_expr = parse(jsonPath)
        __find = jsonPath_expr.find(json)
        if len(__find) == 0:
            # print "%s is not in %s" %(jsonPath, json)
            raise KeyError
        elif len(__find) == 1:
            return __find[0].value
        else:
            return [match.value for match in __find]
    except KeyError:
        return None


def jsonFile_get(json_file_path, jsonPath):
    '''
    get value form json file with jsonpath based on call json_get(json, jsonPath)
    :json_file_path:
        json file path string
    :jsonPath:
        jsonpath expression string
    return:
        string
    example:
        json_file_path = "/home/vivian/test.json"
        jsonPath = "$..tester"
        return: xiaobo
    '''
    # if is_windows():
    #     encoding_ = "gbk"
    # else:
    #     encoding_ = "utf-8"
    filePath = os.path.join(projectPath, json_file_path)
    if os.path.exists(filePath):
        with open(filePath, "r", encoding="utf-8") as jsonFile:
            jsonContent = json.load(jsonFile)
            json_content = json_get(jsonContent, jsonPath)
            # if json_content is None:
            #     print("Not found matched keys with jsonpath {} in file {}".format(jsonPath, json_file_path))
            return json_content
    return None


def jsonFile_set(json_file_path, jsonPath, new_value):
    '''
    get value form json content with jsonpath
    :json_file_path: 
        json file path string
    :jsonPath:
        jsonpath expression string
    :new_value: 
        string
        
    return:
        string
    example:
        json_file_path = "/home/vivian/test.json"
        content in json file:
        {"team":{"number":10,"tester":"vivian"}}
        jsonPath = "$..tester"
        new_value = "grady"
        
        after call jsonFile_set("/home/vivian/test.json", "$..tester", "grady")
        
        content in json file:
        {"team":{"number":10,"tester":"grady"}}
        
    '''
    filePath = os.path.join(projectPath, json_file_path)

    def get_updated_content(jsonContent):
        return json_set(jsonContent, jsonPath, new_value)

    write_JsonFile(filePath, get_updated_content)


def jsonFile_delete(jsonFilePath, jsonPath):
    filePath = os.path.join(projectPath, jsonFilePath)

    def get_updated_content(jsonContent):
        return json_delete(jsonContent, jsonPath)

    write_JsonFile(filePath, get_updated_content)


def write_JsonFile(filePath, getUpdateContentFun):
    with open(filePath, "r+") as jsonFile:
        jsonFile = open(filePath, "r+")
        jsonContent = json.load(jsonFile)
        newJsonContent = getUpdateContentFun(jsonContent)
        jsonFile.seek(0)
        jsonFile.write(json.dumps(newJsonContent, indent=4))
        jsonFile.truncate()
        jsonFile.close()


def json_set(jsonContent, jsonPath, newvalue):
    jsonPath_expr = parser(jsonPath)
    jsonPath_expr.update(jsonContent, newvalue)
    return jsonContent


def json_delete(jsonContent, jsonPath):
    jsonPath_expr = parser(jsonPath)
    jsonPath_expr.delete(jsonContent)
    return jsonContent


def json_get_with_priority(json_content, find_keys):
    priority = 0

    while priority < len(find_keys):
        xpath = json_get(json_content, '$..%s' % find_keys[priority])
        if xpath != None:
            return xpath
        priority += 1

    return None


def assertJson(expected, actual, ignore_compare_order=False):
    '''
    compare 2 dict
    '''

    def string2unicode(innest_dict):
        for k, v in innest_dict.items():
            if isinstance(v, str):
                innest_dict[k] = v
            elif isinstance(v, list) and all(isinstance(item, str) for item in v):
                innest_dict[k] = [v_str for v_str in v]
        return innest_dict

    expected = dict_format(expected, string2unicode)
    actual = dict_format(actual, string2unicode)
    #     comparedResultDetail = DeepDiff(expected, actual, ignore_order=ignore_compare_order, ignoreAdded=True, verbose_level=2)
    comparedResultDetail = DeepDiff(expected,
                                    actual,
                                    ignore_order=ignore_compare_order,
                                    verbose_level=2)  # using official method
    if comparedResultDetail != {}:
        comparedResultDetail = dict_format(comparedResultDetail, change_dict_key_pattern,
                                           ("new_value", "actual_value"))
        comparedResultDetail = dict_format(comparedResultDetail, change_dict_key_pattern,
                                           ("old_value", "expected_value"))
    comparedResultDetail = exclude_str_root(comparedResultDetail)

    return comparedResultDetail == {}, comparedResultDetail


def format_json_compare_list(d_list):
    '''
    format compared result list bsed on the list of return by assertJson(expected, actual, ignore_compare_order=False)
    '''
    try:
        for key, compare_result in d_list.iteritems():
            d_list[key] = format_json_compare(compare_result)
        return d_list
    except:
        print("fail to format_json_compare_list for %s" % d_list)


def format_json_compare(_dict):
    '''
    format compared result list bsed on the return of assertJson(expected, actual, ignore_compare_order=False)
    @example:
    _dict = 
    {
        "192.168.101.91": {
            "values_changed": {
                "['bmc']['p570']": {
                    "expected_value": "3.21.21.21", 
                    "actual_value": "3.15.17.15"
                }
            }
        }
    }
    
    @return:
    "192.168.101.91": {
            "bmc": {
                "p570": {
                    "expected_value": "3.21.21.21", 
                    "actual_value": "3.15.17.15"
                }
            }
        }
    }
    '''
    formated_dict = {}
    origin_dict = _dict
    if _dict.has_key("values_changed"):
        origin_dict = _dict["values_changed"]
    for key, value in origin_dict.iteritems():
        if "][" in key:
            keys = key.split("']['")
        else:
            keys = key.split['[']
        keys[0] = keys[0].replace("['", "")
        keys[-1] = keys[-1].replace("']", "")
        for i in reversed(range(len(keys))):
            new_key = keys[i]
            if not formated_dict.has_key(new_key):
                formated_dict[new_key] = {}
            if i == len(keys) - 1:
                formated_dict[new_key] = value
            else:
                last_inner_key = keys[i + 1]
                formated_dict[new_key].update({last_inner_key: formated_dict[last_inner_key]})
                formated_dict.pop(last_inner_key)
    return formated_dict
