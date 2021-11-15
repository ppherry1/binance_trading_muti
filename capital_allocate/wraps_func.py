import ccxt
import datetime
import time
import sys
import json
import pandas as pd
from capital_allocate.function import *
from functools import wraps, partial


def return_is_normal(func=None, use_bin_return=False):
    # 装饰函数，用于检查返回值是否正常，默认OK交易所，其他交易所需重写此方法,各类命令均可使用
    # 如果命令正常执行，返回二元值，use_bin_return则需设置为True，默认False，即返回原结果
    if func is None:
        return partial(return_is_normal, use_bin_return=use_bin_return)
    @wraps(func)
    def wrapfunc(self, *args, **kwargs):
        result = func(self, *args, **kwargs)
        if result['code'] == '0':
            print('命令%s执行成功,参数:' % func.__name__, args, kwargs)
            return True if use_bin_return else result
        else:
            print('命令%s执行失败,参数:' % func.__name__, args, kwargs)
            return False if use_bin_return else result
    return wrapfunc


def repeat(func):
    # 装饰函数，用于重试交易所的交互命令,一般用于GET类命令
    @wraps(func)
    def wrapfunc(self, *args, **kwargs):
        func_name = func.__name__
        for i in range(self.max_repeat_times):
            try:
                ret = func(self, *args, **kwargs)
                return ret
            except Exception as e:
                # 从交易所获取信息出错,网络等问题
                print(str(datetime.datetime.now()), func_name, '运行出错，错误信息：', e)
                print('1s后进行重试，已重试次数', i, '最大重试次数', self.max_repeat_times)
                time.sleep(0.5)
                if i == (self.max_repeat_times - 1):
                    print('已达最大重试次数，程序raise Exception!')
                    raise Exception
    return wrapfunc


def try_catch(func):
    # 装饰函数，捕捉交易所交互错误,一般用于POST类命令
    @wraps(func)
    def wrapfunc(self, *args, **kwargs):
        try:
            ret = func(self, *args, **kwargs)
            return ret
        except Exception as e:
            print(e)
            print('命令%s执行错误,raise Exception,参数:' % func.__name__, args, kwargs)
            raise Exception
    return wrapfunc


def convert_dataframe(func):
    # 装饰函数，用于将交易所返回的结果转为所需的格式,一般用于返回值有列表形式的命令
    @wraps(func)
    def wrapfunc(self, *args, **kwargs):
        func_name = func.__name__
        print(func_name)
        try:
            if self.exchange_name == 'OKEX':
                if func_name in ['get_account_balance']:
                    df = pd.DataFrame(func(self, *args, **kwargs)['data'][0]['details'])
                    # df = df[['ccy', 'availEq', 'availBal', 'notionalLever']].copy()
                    return df
                elif func_name in ['get_account_positions', 'get_asset_balance']:
                    df = pd.DataFrame(func(self, *args, **kwargs)['data'])
                    return df
                elif func_name == 'get_account_account_position_risk':
                    df1 = pd.DataFrame(func(self, *args, **kwargs)['data'][0]['balData'])
                    df2 = pd.DataFrame(func(self, *args, **kwargs)['data'][0]['posData'])
                    return df1, df2
                else:
                    print('==函数名未自定义格式，直接返回原结果==')
                    return func(self, *args, **kwargs)
        except Exception as e:
            print(e)
            print('结果转换格式出错，raise Exception')
            raise Exception
    return wrapfunc

