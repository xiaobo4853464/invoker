import log


def keywords_data_driven_inspect(test_data, function_name, test_module_path):
    json_path = test_module_path.replace(".py", ".json").split("/")[-1]
    if not isinstance(test_data, list):
        raise KeywordsDataDrivenException(
            "Test data must be a list, please check your case. '{}'".format(function_name), json_path)
    all_are_dic = all(list((isinstance(dic, dict)) for dic in test_data))
    if not all_are_dic:
        raise KeywordsDataDrivenException(
            "Test data in the list must be a dict, please check your case. '{}'".format(function_name), json_path)


def case_factors_inspect(test_data, function_name, test_module_path):
    json_path = test_module_path.replace(".py", ".json").split("/")[-1]
    policy = ["basic_factors", "test_data", "expect_values"]
    sub_policy = ['case_id', 'priority']
    accord = [all(list(p in dic.keys() for dic in test_data)) for p in policy]

    if not all(accord):
        raise KeywordsDataDrivenException(("Test data missing one or all factor of {policy},"
                                           " please check your case. '{func_name}'".format(policy=policy,
                                                                                           func_name=function_name)),
                                          json_path)

    for index, dic in enumerate(test_data):
        case_basic_factors = dic["basic_factors"].keys()

        accord = [p in case_basic_factors for p in sub_policy]

        if not all(accord):
            index += 1
            raise KeywordsDataDrivenException(("Test data in the list missing one or all factor of {sub_policy}, "
                                               "please check your case '{func_name}',"
                                               "The index is :{index}".format(sub_policy=sub_policy,
                                                                              func_name=function_name,
                                                                              index=index)), json_path)

        if not dic['basic_factors']["priority"].isdigit():
            raise KeywordsDataDrivenException(("The [priority] must be a str_num, please check your case '{func_name}',"
                                               "The index is :{index}".format(sub_policy=sub_policy,
                                                                              func_name=function_name,
                                                                              index=index)), json_path)
        if dic['basic_factors']["case_id"]:
            if not dic['basic_factors']["case_id"].isdigit():
                raise KeywordsDataDrivenException(
                    ("The [case_id] must be a str_num, please check your case '{func_name}',"
                     "The index is :{index}".format(sub_policy=sub_policy,
                                                    func_name=function_name,
                                                    index=index)), json_path)

        # expect_values = dic["expect_values"].keys()
        # if len(expect_values) == 0:
        #     raise KeywordsDataDrivenException(
        #         ("'expect_values' length is 0, please check your case. '{func_name}' "
        #          "The index is :{index}".format(func_name=function_name, index=index)), json_path)


def duplicate_case_id_inspect(check_id_dict: dict):
    for id_, cases in check_id_dict.items():
        if len(cases) > 1:
            for case in cases:
                log.LOGGER.warning(
                    ("\n[Warning] Duplicated case id:{case_id}\n"
                     "function_name:{f_name}\n"
                     "test_data_path:{json_path}\n"
                     "data_index:{index}".format(case_id=case.id, f_name=case.function_name,
                                                 json_path=case.test_data_path,
                                                 index=case.index)))


class KeywordsDataDrivenException(Exception):
    def __init__(self, msg, json_path):
        self.msg = "\n[OOPS]{msg}\n[Test data path]: {json_path}".format(msg=msg, json_path=json_path)
        super(KeywordsDataDrivenException, self).__init__(self.msg)


class Case(object):
    """为了检查重复cases id"""
    def __init__(self, id_, function_name, priority, test_module_path, index, desc=""):
        self.id = id_
        self.function_name = function_name
        self.priority = priority
        self.test_module_path = test_module_path
        self.desc = desc
        self.index = index

    @property
    def test_data_path(self):
        return self.test_module_path.replace(".py", ".json").split("/")[-1]

    def __repr__(self):
        return "Case_<{func_name}>".format(func_name=self.function_name)
