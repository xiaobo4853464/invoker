from pytz import timezone
import datetime
import operator


class GenerateTime(object):
    _CN_TIME_ZONE = timezone('Asia/Shanghai')

    @staticmethod
    def generate_now():
        """
        Y-%m-%d %H:%M:%S
        :return: 返回中国上海地区时间
        """
        return datetime.datetime.now().replace(tzinfo=GenerateTime._CN_TIME_ZONE)

    @staticmethod
    def get_specified_time(start_time=None, years=0, months=0, days=0, hours=0, minutes=0, seconds=0,
                           microseconds=0, weeks=0, add=None, sub=None):
        """
        Do not remove gray background parameters
        :return: 返回当前时间往前/后的一个指定的时间
        """
        if add:
            operate = operator.add
        else:
            operate = operator.sub

        if add and sub:
            raise Exception("Only choice 'add' or 'sub'")

        # special handle
        days = days + (years * 365)
        days = days + (months * 30)

        if start_time:
            start_time = start_time
        else:
            start_time = GenerateTime.generate_now()

        value = datetime.timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds, microseconds=microseconds,
                                   weeks=weeks)

        return operate(start_time, value)


if __name__ == '__main__':
    now = GenerateTime.generate_now()
    a = GenerateTime.get_specified_time(weeks=1, add=True).strftime("%Y-%m-%d %H:%M:%S")
    print(a)
