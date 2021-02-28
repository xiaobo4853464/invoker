from collections import OrderedDict
from copy import deepcopy


def instance_to_dict(cls_instance, class_key=None):
    '''
    convert class instance to dictionary
    Args:
        cls_instance:
            type: class instance
        class_key:
            type: string
            content: default class name of cls_instance
                    it is used for the root node name of the returned dictionary
    Return:
        type: dictionary
        example:
            class PhysicalView(object):
                def __init__(self):
                    self.psnt = "123"
            return:
            {
                "PhysicalView":
                {
                    "psnt": "123"
                }
            }
    '''
    if isinstance(cls_instance, dict):
        data = {}
        for (k, v) in cls_instance.items():
            data[k] = instance_to_dict(v, class_key)
        return data
    elif hasattr(cls_instance, '_ast'):
        return instance_to_dict(cls_instance._ast())
    elif hasattr(cls_instance, "__iter__"):
        return [instance_to_dict(v, class_key) for v in cls_instance]
    elif hasattr(cls_instance, "__dict__"):
        data = dict([(key, instance_to_dict(value, class_key))
                     for key, value in cls_instance.__dict__.iteritems()
                     if not callable(value) and not key.startswith('_')])
        if class_key is not None and hasattr(cls_instance, "__class__"):
            data[class_key] = cls_instance.__class__.__name__
        return data
    else:
        return cls_instance


def exclude_str_root(raw_dict):
    new_dict = {}

    for k, v in raw_dict.items():
        if (k[:4] == "root"):
            new_k = k[4:]
        else:
            new_k = k

        if (isinstance(v, dict)):
            new_v = exclude_str_root(v)
            new_dict[new_k] = new_v
        else:
            new_dict[new_k] = v

    return new_dict


if __name__ == "__main__":
    raw_dict = {
        "values_changed": {
            "root['responseBody']['status']": {
                "actual_value": "COMPLETED",
                "expected_value": "NOT_STARTED"
            },
            "root['responseBody']['message']": {
                "actual_value": "",
                "expected_value": "No configuration job in progress."
            }
        }
    }
    print(exclude_str_root(raw_dict))


def change_dict_key_pattern(innestDict, value_tuple):
    new_innestDict = {}
    old_dex = value_tuple[0]
    new_dex = value_tuple[1]
    for k, v in innestDict.items():
        v_ = str(v)
        if old_dex in k:
            new_innestDict[k.replace(old_dex, new_dex)] = v_
        else:
            new_innestDict[k] = v_
    return new_innestDict


def change_dict_value_pattern(innestDict, old_value, new_value):
    new_innestDict = {}
    for k, v in innestDict.iteritems():
        if old_value == v:
            new_innestDict[k] = new_value
        else:
            new_innestDict[k] = v
    return new_innestDict


def change_statusCodeAndRequestBody_type_to_int(innestDict):
    for k, v in innestDict.iteritems():
        #         try:
        #             if isinstance(v,unicode):
        #                 str_dict = v.encode('ascii','ignore')#.replace("'","\"")
        #                 #print str_dict
        #                 innestDict[k] = json.loads(str_dict)
        #             elif isinstance(v,str):
        #                 innestDict[k] = json.loads(v)
        #         except:
        #             pass
        if "statuscode" in k.lower():
            innestDict[k] = int(v)
        if "responsebody" in k.lower() and v is None:
            innestDict[k] = ""
    return innestDict


def dict_format_for_requestBody(dic):
    pass


def dict_format_for_convert_xml(dic):
    def change_dict_key_pattern_for_convert2xml(innestDict, attribute_dex="_xmlAttribute_"):
        converted_dict = OrderedDict()
        for k, v in innestDict.iteritems():
            if attribute_dex not in k:
                if k == "#text":
                    converted_dict["$"] = v
                else:
                    converted_dict[k] = {'$': v}
            else:
                converted_dict[k.replace(attribute_dex, "@")] = v
        return converted_dict

    return dict_format(dic, change_dict_key_pattern_for_convert2xml)


def dict_format(dic, change_key_pattern_func, *args):
    orderedDict = OrderedDict(dic)
    format_dict = OrderedDict()
    if isinstance(orderedDict, list) and all(isinstance(item, dict) for item in orderedDict):
        for vIndex, vItem in enumerate(orderedDict):
            orderedDict[vIndex] = dict_format(vItem, change_key_pattern_func, *args)
        format_dict = orderedDict.deepcopy()
    else:
        for k, v in orderedDict.items():
            if isinstance(v, dict):
                new_v = dict_format(v, change_key_pattern_func, *args)
                format_dict[k] = new_v
            elif isinstance(v, list) and all(isinstance(item, dict) for item in v):
                for vIndex, vItem in enumerate(v):
                    v[vIndex] = dict_format(vItem, change_key_pattern_func, *args)
                format_dict = orderedDict
            else:
                new_v = change_key_pattern_func({k: v}, *args)
                format_dict.update(new_v)
    return format_dict


def iter_pop(dic_, *keys):
    for k, v in dic_.items():
        if isinstance(v, dict):
            for k_ in keys:
                if k_ in v.keys():
                    v.pop(k_)
                    if v == {}:
                        return {}
                else:
                    return iter_pop(v, *keys)
    return dic_
