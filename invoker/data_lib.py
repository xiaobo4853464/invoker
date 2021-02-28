import inspect

from invoker.json_handler import json_get, jsonFile_get


def get_input_data(self):
    all_test_data = self.get_testdata()
    json_path_for_input = "$..input_values"
    return json_get(all_test_data, json_path_for_input) or all_test_data


def get_test_data(test_data_path, test_case_name):
    expr_with_test_case = "$..%s" % test_case_name
    test_data = jsonFile_get(test_data_path, expr_with_test_case)
    return test_data


def get_all_data(test_data_path):
    expr_with_test_case = "$"
    test_data = jsonFile_get(test_data_path, expr_with_test_case)
    return test_data
