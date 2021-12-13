import ccxt
import datetime
import time
import sys
import json
import pandas as pd
from capital_allocate.function import *
from functools import wraps, partial
from trading_class.translate_contrast import *
import webbrowser
import os
_ = os.path.abspath(os.path.dirname(__file__))  # 返回当前文件路径
root_path = os.path.abspath(os.path.join(_, '.'))  # 返回根目录文件夹

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


def convert_dataframe1(func=None, use_filter=None):
    # 装饰函数，用于将交易所返回的结果转为所需的格式,一般用于返回值有列表形式的命令
    @wraps(func)
    def wrapfunc(self, *args, **kwargs):
        func_name = func.__name__
        print(func_name)
        try:
            if self.exchange_name == 'BINANCE':
                res = func(self, *args, **kwargs)
                if func_name in ['get_spot_account']:
                    res = res['balances']
                elif func_name in ['get_future_assets']:
                    res = res['assets']
                elif func_name in ['get_future_positions']:
                    res = res['positions']

                if type(res) == list:
                    res = pd.DataFrame(res)
                elif type(res) == dict:
                    res = pd.DataFrame([res])
                else:
                    print('未识别，返回原结果')
                    return res
                if use_filter:
                    if 'values' not in use_filter.keys():
                        res = res.loc[res[use_filter['col']].notna()]
                    elif (type(use_filter['values']) == list) and 'is_white' not in use_filter.keys():
                        res = res.loc[~res[use_filter['col']].isin(use_filter['values'])]
                    elif (type(use_filter['values']) == list) and 'is_white' in use_filter.keys():
                        res = res.loc[res[use_filter['col']].isin(use_filter['values'])]
                return pd.DataFrame(res)
        except Exception as e:
            print(e)
            print('结果转换格式出错，raise Exception')
            raise Exception
    return wrapfunc


def convert_dataframe(use_filter=None):
    # 装饰函数，用于将交易所返回的结果转为所需的格式,一般用于返回值有列表形式的命令
    def wrapfunc1(func):
        @wraps(func)
        def wrapfunc(self, *args, **kwargs):
            func_name = func.__name__
            print(func_name)
            try:
                if self.exchange_name == 'BINANCE':
                    res = func(self, *args, **kwargs)
                    if func_name in ['get_spot_account']:
                        res = res['balances']
                        for item in res:
                            item['total_assets'] = float(item['free']) + float(item['locked'])
                    elif func_name in ['get_future_assets']:
                        res = res['assets']
                    elif func_name in ['get_future_positions']:
                        res = res['positions']
                    elif func_name in ['get_positionRisk']:
                        for item in res:
                            if 'USDT' not in item['symbol']:
                                face_value = 100 if 'BTC' in item['symbol'] else 10
                                item['usd_profit'] = float(item['positionAmt']) * face_value * (
                                        float(item['markPrice']) / float(item['entryPrice']) - 1) if float(
                                    item['entryPrice']) != 0 else 0
                    if type(res) == list:
                        res = pd.DataFrame(res)
                    elif type(res) == dict:
                        res = pd.DataFrame([res])
                    else:
                        print('未识别，返回原结果')
                        return res
                    if use_filter:
                        if 'values' not in use_filter.keys():
                            res = res.loc[res[use_filter['col']].notna()]
                        elif 'big_than' in use_filter.keys():
                            res = res.loc[res[use_filter['col']].astype(float) > use_filter['values'][0]]
                        elif 'not_equal' in use_filter.keys():
                            res = res.loc[res[use_filter['col']].astype(float) != use_filter['values'][0]]
                        elif 'small_than' in use_filter.keys():
                            res = res.loc[res[use_filter['col']].astype(float) < use_filter['values'][0]]
                        elif (type(use_filter['values']) == list) and 'is_white' not in use_filter.keys():
                            res = res.loc[~res[use_filter['col']].isin(use_filter['values'])]
                        elif (type(use_filter['values']) == list) and 'is_white' in use_filter.keys():
                            res = res.loc[res[use_filter['col']].isin(use_filter['values'])]

                    return pd.DataFrame(res)
            except Exception as e:
                print(e)
                print('结果转换格式出错，raise Exception')
                raise Exception
        return wrapfunc
    return wrapfunc1


def translate_dataframe(func):
    # 装饰函数，用于将交易所返回的结果转为所需的格式,一般用于返回值有列表形式的命令
    @wraps(func)
    def wrapfunc(self, *args, **kwargs):
        # try:
            res = func(self, *args, **kwargs)
            if type(res) == pd.DataFrame:
                res.rename(columns=translate_dict, inplace=True)
                for col in res.columns.to_list():
                    if '时间' in col:
                        res[col] = pd.to_datetime(res[col], unit='ms') + datetime.timedelta(hours=8)
                print(res)
                return res
        # except Exception as e:
        #     print(e)
        #     print('结果转换格式出错，raise Exception')
        #     raise Exception
    return wrapfunc


def webbrowser_show(func):
    # 装饰函数，用于将交易所返回的结果转为所需的格式,一般用于返回值有列表形式的命令
    @wraps(func)
    def wrapfunc(self, *args, **kwargs):
        # try:
        res = func(self, *args, **kwargs)
        # res.to_html('.\\data\\tmp_shower.html', encoding='gb18030')
        # webbrowser.open(root_path + '\\data\\tmp_shower.html')
        return res
        # except Exception as e:
        #     print(e)
        #     print('结果转换格式出错，raise Exception')
        #     raise Exception
    return wrapfunc