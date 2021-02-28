import simplejson as json
from deepdiff import DeepDiff

from invoker.const import RespCode
from invoker.decorators import checkpoint
from invoker.dict_format import (change_dict_key_pattern, dict_format,
                              exclude_str_root)


class BaseTestCase(object):

    @classmethod
    def setup_class(cls):
        pass

    @classmethod
    def teardown_class(cls):
        pass

    def setup_method(self, method):
        pass

    def teardown_method(self, method):
        pass

    @classmethod
    def _error_msg(cls, expect, actual, error_msg=None):
        if error_msg:
            output_err_msg = "\n[Expect]: {}\n[Actual]: {}\n{}".format(expect, actual, error_msg)
        else:
            output_err_msg = "\n[Expect]: {}\n[Actual]: {}".format(expect, actual)

        return output_err_msg

    @classmethod
    @checkpoint
    def assert_in(cls, expect, actual, err_msg=None):
        assert expect in actual, cls._error_msg(expect, actual, err_msg)

    @classmethod
    @checkpoint
    def assert_iter_equal(cls,
                          expect,
                          actual,
                          error_msg="",
                          ignore_missed_expect_values=False,
                          ignore_compare_order=True):

        diff = DeepDiff(expect, actual, ignore_order=ignore_compare_order, verbose_level=2)
        if ignore_missed_expect_values:
            print("[Ignore expect values]: {}".format(diff.pop("dictionary_item_added")))
        if diff != {}:
            compared_detail = dict_format(diff, change_dict_key_pattern,
                                          ("new_value", "actual_value"))
            compared_detail = dict_format(compared_detail, change_dict_key_pattern,
                                          ("old_value", "expected_value"))
            compared_detail = dict_format(compared_detail, change_dict_key_pattern,
                                          ("new_type", "actual_type"))
            compared_detail = dict_format(compared_detail, change_dict_key_pattern,
                                          ("old_type", "expected_type"))
            compared_detail = exclude_str_root(compared_detail)
        else:
            compared_detail = diff

        compared_detail_str = json.dumps(compared_detail, indent=4)
        err_msg = "\n{}\n\n{}".format(compared_detail_str, error_msg)

        assert compared_detail == {}, err_msg

    @classmethod
    def assert_dic_type(cls, expect, actual, error_msg="", ignore_missed_expect_values=False):
        expect_ = {
            k: type(v) if type(v).__base__.__name__ == "object" else type(v).__base__
            for k, v in expect.items()
        }
        actual_ = {
            k: type(v) if type(v).__base__.__name__ == "object" else type(v).__base__
            for k, v in actual.items()
        }
        cls.assert_iter_equal(expect_,
                              actual_,
                              error_msg=error_msg,
                              ignore_missed_expect_values=ignore_missed_expect_values)

    @classmethod
    @checkpoint
    def assert_equal(cls, expect, actual, error_msg=""):
        assert expect == actual, cls._error_msg(expect, actual, error_msg)

    @classmethod
    @checkpoint
    def assert_not_equal(cls, expect, actual, error_msg=""):
        assert expect != actual, cls._error_msg(expect, actual, error_msg)

    @classmethod
    @checkpoint
    def assert_not_in(cls, expect, actual, error_msg=None):
        assert expect not in actual, cls._error_msg(expect, actual, error_msg)

    @classmethod
    @checkpoint
    def assert_true(cls, actual, error_msg=""):
        assert actual is True, cls._error_msg("True", actual, error_msg)

    @classmethod
    @checkpoint
    def assert_false(cls, actual, error_msg=""):
        assert actual is False, cls._error_msg("False", actual, error_msg)

    @classmethod
    @checkpoint
    def assert_is_none(cls, actual, error_msg=""):
        assert actual is None, cls._error_msg("None", actual, error_msg)

    @classmethod
    @checkpoint
    def assert_is_not_none(cls, actual, error_msg=""):
        assert actual is not None, cls._error_msg("Not None", actual, error_msg)

    @classmethod
    @checkpoint
    def assert_response(cls, resp):
        error_info = "[Error response]: \n{}".format(repr(resp))
        resp_code = resp.get('code')
        assert resp_code == RespCode.SUCCESS, cls._error_msg(RespCode.SUCCESS, resp_code,
                                                             error_info)

    @classmethod
    @checkpoint
    def assert_null(cls, actual, error_msg=""):
        assert not actual, "{}\n{}".format(str(actual), error_msg)

    @classmethod
    @checkpoint
    def assert_not_null(cls, actual, error_msg=""):
        assert actual, "{}\n{}".format(str(actual), error_msg)
