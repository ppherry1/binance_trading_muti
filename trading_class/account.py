from trading_class.wraps_func import *
from datetime import datetime
pd.set_option('display.max_rows', 1000)
pd.set_option('expand_frame_repr', False)  # 当列太多时不换行
# 设置命令行输出时的列对齐功能
pd.set_option('display.unicode.ambiguous_as_wide', True)
pd.set_option('display.unicode.east_asian_width', True)


class Account:
    def __init__(self, account_info: dict):
        # account_info包含apiKey, secret, passphrase, config, id, password。condig是策略配置。
        # apiKey, secret, passphrase是API，id是注册账户的邮箱或手机号(站内转账用)，password是资金密码
        self.exchange_name = 'BINANCE'
        self.exchange = ccxt.binance({
            'timeout': 3000,
            'rateLimit': 10,
            'apiKey': account_info['apiKey'],
            'secret': account_info['secret'],
        })
        if 'id' in account_info.keys():
            self.id = account_info['id']
        if 'password' in account_info.keys():
            self.password = account_info['password']
        self.max_repeat_times = 10  # 重试交易所的交互命令最大重试次数

    @webbrowser_show
    @translate_dataframe
    @convert_dataframe(use_filter=None)
    @try_catch
    def post_order(self, params: dict):
        # 下单
        func_params = dict()
        func_params['symbol'] = params['symbol']
        func_params['side'] = params['side']
        func_params['type'] = params['order_type']
        if 'quantity' in params.keys() and params['quantity'] is not None:
            func_params['quantity'] = float(params['quantity'])
        if 'quoteOrderQty' in params.keys() and params['quoteOrderQty'] is not None:
            func_params['quoteOrderQty'] = float(params['quoteOrderQty'])
        if func_params['type'] == 'LIMIT':
            func_params['price'] = float(params['price'])
        if 'newClientOrderId' in params.keys():
            func_params['newClientOrderId'] = params['newClientOrderId']
        # func_params['timeInForce'] = params['timeInForce'] if 'timeInForce' in params.keys() else 'GTC'

        func_dict = {'spot': self.exchange.privatePostOrder,
                     'ufuture': self.exchange.fapiPrivatePostOrder,
                     'cfuture': self.exchange.dapiPrivatePostOrder,
                     }
        info = func_dict[params['ins_type']](params=func_params)
        return info

    @webbrowser_show
    @translate_dataframe
    @convert_dataframe(use_filter=None)
    @try_catch
    def get_openOrders(self, params: dict):
        # 获取挂单
        func_params = dict()
        if 'symbol' in params.keys():
            func_params['symbol'] = params['symbol']
        func_dict = {'spot': self.exchange.privateGetOpenOrders,
                     'ufuture': self.exchange.fapiPrivateGetOpenOrders,
                     'cfuture': self.exchange.dapiPrivateGetOpenOrders,
                     }
        if func_params:
            info = func_dict[params['ins_type']](params=func_params)
        else:
            info = func_dict[params['ins_type']]()
        return info

    @webbrowser_show
    @translate_dataframe
    @convert_dataframe(use_filter={'col': 'total_assets', 'not_equal': True, 'values': [0]})
    @try_catch
    def get_spot_account(self, params: dict):
        # 获取账户信息
        func_dict = {'spot': self.exchange.privateGetAccount,
                     }
        info = func_dict[params['ins_type']]()
        return info

    @webbrowser_show
    @translate_dataframe
    @convert_dataframe(use_filter={'col': 'walletBalance', 'not_equal': True, 'values': [0]})
    @try_catch
    def get_future_assets(self, params: dict):
        # 获取账户信息
        func_dict = {
                     'ufuture': self.exchange.fapiPrivateGetAccount,
                     'cfuture': self.exchange.dapiPrivateGetAccount,
                     }
        info = func_dict[params['ins_type']]()
        return info

    @webbrowser_show
    @translate_dataframe
    @convert_dataframe(use_filter={'col': 'positionAmt', 'not_equal': True, 'values': [0]})
    @try_catch
    def get_future_positions(self, params: dict):
        # 获取账户信息
        func_dict = {
                     'ufuture': self.exchange.fapiPrivateGetAccount,
                     'cfuture': self.exchange.dapiPrivateGetAccount,
                     }
        info = func_dict[params['ins_type']]()
        return info

    @webbrowser_show
    @translate_dataframe
    @convert_dataframe(use_filter=None)
    @try_catch
    def get_balance(self, params: dict):
        # 获取账户余额
        func_dict = {'spot': self.exchange.privateGetBalance,
                     'ufuture': self.exchange.fapiPrivateGetBalance,
                     'cfuture': self.exchange.dapiPrivateGetBalance,
                     }
        info = func_dict[params['ins_type']]()
        return info

    @webbrowser_show
    @translate_dataframe
    @convert_dataframe(use_filter={'col': 'positionAmt', 'not_equal': True, 'values': [0], 'real_leverage': 2})
    @try_catch
    def get_positionRisk(self, params: dict):
        # 获取账户持仓风险
        func_dict = {
                     'ufuture': self.exchange.fapiPrivateGetPositionRisk,
                     'cfuture': self.exchange.dapiPrivateGetPositionRisk,
                     }
        info = func_dict[params['ins_type']]()
        return info

    @webbrowser_show
    @translate_dataframe
    @convert_dataframe(use_filter=None)
    @try_catch
    def get_allOrders(self, params: dict):
        # 获取历史挂单记录
        func_params = dict()
        func_params['symbol'] = params['symbol']
        func_params['limit'] = 100
        if 'startTime' in params.keys():
            dt_obj = datetime.strptime(params['startTime'], '%Y-%m-%d')
            func_params['startTime'] = int(dt_obj.timestamp() * 1000)
        if 'endTime' in params.keys():
            dt_obj = datetime.strptime(params['endTime'], '%Y-%m-%d')
            func_params['endTime'] = int(dt_obj.timestamp() * 1000)

        func_dict = {'spot': self.exchange.privateGetAllOrders,
                     'ufuture': self.exchange.fapiPrivateGetAllOrders,
                     'cfuture': self.exchange.dapiPrivateGetAllOrders,
                     }
        info = func_dict[params['ins_type']](params=func_params)
        return info

    @webbrowser_show
    @translate_dataframe
    @convert_dataframe(use_filter=None)
    @try_catch
    def delete_allOpenOrders(self, params: dict):
        # 撤销挂单
        func_params = dict()
        func_params['symbol'] = params['symbol']
        func_dict = {'spot': self.exchange.privateDeleteOpenOrders,
                     'ufuture': self.exchange.fapiPrivateDeleteAllOpenOrders,
                     'cfuture': self.exchange.dapiPrivateDeleteAllOpenOrders,
                     }
        info = func_dict[params['ins_type']](params=func_params)
        return info

    @webbrowser_show
    @translate_dataframe
    @convert_dataframe(use_filter=None)
    @try_catch
    def get_userTrades(self, params: dict):
        # 获取历史成交记录
        func_params = dict()
        func_params['symbol'] = params['symbol']
        func_params['limit'] = 100
        if 'startTime' in params.keys():
            dt_obj = datetime.strptime(params['startTime'], '%Y-%m-%d')
            func_params['startTime'] = int(dt_obj.timestamp() * 1000)
        if 'endTime' in params.keys():
            dt_obj = datetime.strptime(params['endTime'], '%Y-%m-%d')
            func_params['endTime'] = int(dt_obj.timestamp() * 1000)

        func_dict = {'spot': self.exchange.privateGetMyTrades,
                     'ufuture': self.exchange.fapiPrivateGetUserTrades,
                     'cfuture': self.exchange.dapiPrivateGetUserTrades,
                     }
        info = func_dict[params['ins_type']](params=func_params)
        return info

    @webbrowser_show
    @translate_dataframe
    @convert_dataframe(use_filter=None)
    @try_catch
    def get_forceOrders(self, params: dict):
        # 获取历史强平或ADL记录
        func_params = dict()
        func_params['symbol'] = params['symbol']
        if 'autoCloseType' in params.keys():
            func_params['autoCloseType'] = params['autoCloseType']
        func_params['limit'] = 100
        if 'startTime' in params.keys():
            dt_obj = datetime.strptime(params['startTime'], '%Y-%m-%d')
            func_params['startTime'] = int(dt_obj.timestamp() * 1000)
        if 'endTime' in params.keys():
            dt_obj = datetime.strptime(params['endTime'], '%Y-%m-%d')
            func_params['endTime'] = int(dt_obj.timestamp() * 1000)

        func_dict = {
                     'ufuture': self.exchange.fapiPrivateGetForceOrders,
                     'cfuture': self.exchange.dapiPrivateGetForceOrders,
                     }
        info = func_dict[params['ins_type']](params=func_params)
        return info


