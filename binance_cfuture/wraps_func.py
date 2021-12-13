import datetime
import time
import pandas as pd
from functools import wraps, partial

recent_k = dict()
recent_k['used'] = 1


def record_signal(func):
    # 装饰函数，用于记录K线和信号
    @wraps(func)
    def wrapfunc(*args, **kwargs):
        global recent_k
        recent_k['k_line'] = args[0].iloc[-1]
        ret = func(*args, **kwargs)
        recent_k['k_line']['signal'] = ret
        recent_k['used'] = 0
        return ret
    return wrapfunc
