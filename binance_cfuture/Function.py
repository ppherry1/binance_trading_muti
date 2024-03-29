import json5

from binance_cfuture import Signals
from binance_cfuture.Config import *
from binance_cfuture.Signals import *
import ccxt
import math
import pandas as pd
from datetime import datetime, timedelta
import json
import requests
import time
import hmac
import hashlib
import base64
from urllib import parse
import os


pd.set_option('display.max_rows', 1000)
pd.set_option('expand_frame_repr', False)  # 当列太多时不换行
pd.set_option('display.unicode.ambiguous_as_wide', True)  # 设置命令行输出时的列对齐功能
pd.set_option('display.unicode.east_asian_width', True)


# ==========辅助功能函数==========
# ===下次运行时间，和课程里面讲的函数是一样的
def next_run_time(time_interval, ahead_seconds=5, offset_time='0m'):
    '''
    根据time_interval，计算下次运行的时间，下一个整点时刻。
    目前只支持分钟和小时。
    :param offset_time: 相对于整点，偏离的分钟数，正整数或负整数均可
    :param time_interval: 运行的周期，15m，1h
    :param ahead_seconds: 预留的目标时间和当前时间的间隙
    :return: 下次运行的时间
    '''
    if time_interval.endswith('m') or time_interval.endswith('h'):
        pass
    elif time_interval.endswith('T'):
        time_interval = time_interval.replace('T', 'm')
    elif time_interval.endswith('H'):
        time_interval = time_interval.replace('H', 'h')
    else:
        print('time_interval格式不符合规范。程序exit')
        exit()

    ti = pd.to_timedelta(time_interval)
    offset = pd.to_timedelta(offset_time)
    now_time = datetime.now()
    # now_time = datetime(2019, 5, 9, 23, 50, 30)  # 修改now_time，可用于测试
    this_midnight = now_time.replace(hour=0, minute=0, second=0, microsecond=0)
    min_step = timedelta(minutes=1)

    target_time = now_time.replace(second=0, microsecond=0)

    while True:
        target_time = target_time + min_step
        delta = target_time - this_midnight
        if (delta.seconds - offset.seconds) % ti.seconds == 0 and (
                target_time - now_time).seconds >= ahead_seconds:
            # 当符合运行周期，并且目标时间有足够大的余地，默认为60s
            break

    print('\n', '程序下次运行的时间：', target_time)

    return target_time


# ===依据时间间隔, 自动计算并休眠到指定时间
def sleep_until_run_time(time_interval, ahead_time=1, if_sleep=True, offset_time='0m'):
    """
    根据next_run_time()函数计算出下次程序运行的时候，然后sleep至该时间
    :param time_interval:
    :param ahead_time:
    :param if_sleep:
    :return:
    """

    # 计算下次运行时间
    run_time = next_run_time(time_interval, ahead_time, offset_time=offset_time)

    # sleep
    if if_sleep:
        time.sleep(max(0, (run_time - datetime.now()).seconds))
        # 可以考察：print(run_time - n)、print((run_time - n).seconds)
        while True:  # 在靠近目标时间时
            if datetime.now() > run_time:
                break

    return run_time


# ===重试机制
def retry_wrapper(func, params={}, act_name='', sleep_seconds=3, retry_times=5):
    """
    需要在出错时不断重试的函数，例如和交易所交互，可以使用本函数调用。
    :param func: 需要重试的函数名
    :param params: func的参数
    :param act_name: 本次动作的名称
    :param sleep_seconds: 报错后的sleep时间
    :param retry_times: 为最大的出错重试次数
    :return:
    """

    # for _ in range(retry_times):
    #     try:
    result = func(params=params)
    return result
    #     except Exception as e:
    #         print(act_name, '报错，报错内容：', str(e), '程序暂停(秒)：', sleep_seconds)
    #         time.sleep(sleep_seconds)
    # else:
    #     # send_dingding_and_raise_error(output_info)
    #     raise ValueError(act_name, '报错重试次数超过上限，程序退出。')


# ===将最新数据和历史数据合并
def symbol_candle_data_append_recent_candle_data(symbol_candle_data, recent_candle_data, symbol_config, max_candle_num):
    for symbol in symbol_config.keys():
        df = symbol_candle_data[symbol].append(recent_candle_data[symbol], ignore_index=True)
        df.drop_duplicates(subset=['candle_begin_time_GMT8'], keep='last', inplace=True)
        df.sort_values(by='candle_begin_time_GMT8', inplace=True)  # 排序，理论上这步应该可以省略，加快速度
        df = df.iloc[-max_candle_num:]  # 保持最大K线数量不会超过max_candle_num个
        df.reset_index(drop=True, inplace=True)
        symbol_candle_data[symbol] = df

    return symbol_candle_data


# ===处理adl
def deal_with_binance_adl(exchange, symbol_info, symbol_config):
    # 获取持仓的adl数据
    adl = retry_wrapper(exchange.dapiPrivateGetAdlQuantile, params={'timestamp': int(time.time() * 1000)},
                        act_name='查看合约ADL状态')

    # 将数据转换为DataFrame
    df = pd.DataFrame(adl, dtype=float)

    if df.empty:
        print('has no pos, so no adl..')
        return

    df['adl'] = df['adlQuantile'].apply(lambda x: x['BOTH'])

    # 删选需要处理的持仓
    df = df[df['adl'].astype(float) >= 0]  # 筛选出大于等于4的币种
    adl_symbol = list(df['symbol'])
    adl_symbol = set(adl_symbol) & set(symbol_config.keys())  # 求需要adl仓位和symbol_config中币种的交集

    if not adl_symbol:
        print('\n没有处于adl风险的仓位')
        return None

    print('\n有处于adl风险的仓位，需要处理', adl_symbol)

    # 计算下单参数
    symbol_order_params = []
    for symbol in adl_symbol:
        params = {
            'symbol': symbol,
            'price': symbol_info.at[symbol, '当前价格'],
            'type': 'LIMIT',
            'timeInForce': 'GTC',
        }
        quantity = abs(symbol_info.at[symbol, '合约张数']) / 5  # 每次更换20%的仓位
        quantity = round(quantity, None)  # 取整
        quantity = max(1, quantity)  # 至少更换1一张
        params['quantity'] = quantity

        for side in ['BUY', 'SELL']:
            p = params.copy()
            p['side'] = side
            # 修改下单价格、数量精度
            p = modify_order_quantity_and_price(symbol, symbol_config, p)
            p['price'] = str(p['price'])
            p['quantity'] = str(p['quantity'])
            symbol_order_params.append(p)

    print('adl下单参数\n', symbol_order_params)

    # 下单
    place_binance_cfuture_batch_order(exchange, symbol_order_params)


# ==========交易所交互函数==========
# ===判断当前持仓模式
def if_coin_future_oneway_mode(exchange):
    """
    判断当前合约持仓模式。必须得是单向模式。如果是双向模式，就报错。
    查询当前的持仓模式。使用函数：GET /dapi/v1/positionSide/dual (HMAC SHA256)
    判断持仓情况，False为单向持仓，True为单向持仓
    :param exchange:
    :return:
    api文档：https://binance-docs.github.io/apidocs/delivery/cn/#user_data
    """
    positionSide = retry_wrapper(exchange.dapiPrivateGetPositionSideDual, params={'timestamp': int(time.time() * 1000)},
                                 act_name='查看合约持仓模式')

    if positionSide['dualSidePosition']:
        raise ValueError("当前持仓模式为双向持仓，程序已停止运行。请去币安官网改为单向持仓。")
    else:
        print('当前持仓模式：单向持仓')


# ===获得币对精度
def coin_future_exchange_info(exchange, symbol_config):
    """
    获取symbol_config中币种的最小下单价格
    :param exchange:交易所变量
    :param symbol_config:合约配置信息
    :return:合约对应的币对精度

    api文档：https://binance-docs.github.io/apidocs/delivery/cn/#0f3f2d5ee7
    """

    # 获取u本为合约交易对的信息
    # exchange_info = exchange.dapiPublic_get_exchangeinfo()
    exchange_info = retry_wrapper(exchange.dapiPublic_get_exchangeinfo, act_name='查看合约基本信息')

    # 转化为DataFrame
    df = pd.DataFrame(exchange_info['symbols'])
    df['tickSize'] = df['filters'].apply(lambda x: math.log(1 / float(x[0]['tickSize']), 10))
    df = df[['symbol', 'pricePrecision', 'tickSize']]
    df.set_index('symbol', inplace=True)

    # 赋值
    for symbol in symbol_config.keys():
        symbol_config[symbol]['最小下单价精度'] = round(df.at[symbol, 'tickSize'])


# ===通过ccxt获取K线数据
def ccxt_fetch_binance_coin_future_candle_data(exchange, symbol, time_interval, limit):
    """
    :param exchange:
    :param symbol:
    :param time_interval:
    :param limit:
    :return:
    """
    # 获取数据
    data = retry_wrapper(exchange.dapiPublic_get_klines, act_name='获取币种K线数据',
                         params={'symbol': symbol, 'interval': time_interval, 'limit': limit})

    # 整理数据
    df = pd.DataFrame(data, dtype=float)
    df.rename(columns={1: 'open', 2: 'high', 3: 'low', 4: 'close', 5: 'volume'}, inplace=True)
    df['candle_begin_time'] = pd.to_datetime(df[0], unit='ms')
    df['candle_begin_time_GMT8'] = df['candle_begin_time'] + timedelta(hours=8)
    df = df[['candle_begin_time_GMT8', 'open', 'high', 'low', 'close', 'volume']]

    return df


# ===串行获取一些币种的数据
def single_thread_get_binance_coin_future_candle_data(exchange, symbol_config, symbol_info, time_interval, run_time,
                                                      candle_num):
    """
    获取所有币种的k线数据，并初步处理
    :param exchange:
    :param symbol_config:
    :param symbol_info:
    :param time_interval:
    :param run_time:
    :param candle_num:
    :return:
    """
    symbol_candle_data = dict()  # 用于存储K线数据

    print('开始获取K线数据')
    # 遍历每一个币种
    for symbol in symbol_config.keys():
        print(symbol, '开始时间：', datetime.now(), end=' ')

        # 获取symbol该品种最新的K线数据
        df = ccxt_fetch_binance_coin_future_candle_data(exchange, symbol, time_interval, limit=candle_num)

        # 获取到了最新数据
        print('结束时间：', datetime.now())
        symbol_info.at[symbol, '当前价格'] = df.iloc[-1]['close']  # 该品种的最新价格
        symbol_candle_data[symbol] = df[df['candle_begin_time_GMT8'] < pd.to_datetime(run_time)]  # 去除run_time周期的数据

    return symbol_candle_data


# ===获取需要的币种的历史K线数据。
def get_binance_coin_future_history_candle_data(exchange, symbol_config, time_interval, candle_num, if_print=True):
    symbol_candle_data = dict()  # 用于存储K线数据
    print('获取交易币种的历史K线数据')

    # 遍历每一个币种
    for symbol in symbol_config.keys():

        # 获取symbol该品种最新的K线数据
        df = ccxt_fetch_binance_coin_future_candle_data(exchange, symbol, time_interval, limit=candle_num)

        # 为了保险起见，去掉最后一行最新的数据
        df = df[:-1]

        symbol_candle_data[symbol] = df
        time.sleep(medium_sleep_time)

        if if_print:
            print(symbol)
            print(symbol_candle_data[symbol].tail(3))

    return symbol_candle_data


# ===获取当前币本位合约中币的总数
def binance_update_cfuture_balance(exchange, symbol_config, symbol_info):
    # 通过交易所接口获取合约账户信息
    # future_info = exchange.dapiPrivateGetAccount()
    future_info = retry_wrapper(exchange.dapiPrivateGetAccount, act_name='查看合约账户信息')

    # 将持仓信息转变成DataFrame格式
    positions_df = pd.DataFrame(future_info['positions'], dtype=float)
    positions_df = positions_df.set_index('symbol')
    # 筛选交易的币对
    positions_df = positions_df[positions_df.index.isin(symbol_config.keys())]

    # 将账户信息转变成DataFrame格式
    assets_df = pd.DataFrame(future_info['assets'], dtype=float)
    assets_df = assets_df.set_index('asset')

    # 根据持仓信息、账户信息中的值填充symbol_info
    symbol_info['未实现盈亏'] = positions_df['unrealizedProfit']  # 使用标记价格计算
    for symbol in symbol_config.keys():
        coin = symbol.split('USD')[0]  # 币安之后如果不用USD计价了，这个地方需要改。
        symbol_info.at[symbol, '原始币数'] = assets_df.at[coin, 'walletBalance']
    symbol_info['账户币数'] = symbol_info['原始币数'] + symbol_info['未实现盈亏']

    return symbol_info


# ===获取当前币本位合约的持仓信息
def binance_update_cfuture_account(exchange, symbol_config, symbol_info, mode):
    """
    :param exchange:
    :param symbol_config:
    :param symbol_info:
    :return:
    接口：GET /dapi/v2/account (HMAC SHA256)
    文档：https://binance-docs.github.io/apidocs/delivery/cn/#user_data-7
    币安的币本位合约，不管是交割，还是永续，共享一个账户。他们的symbol不一样。比如btc的永续合约是BTCUSD，季度合约是BTCUSD_210625

                         账户币数   原始币数 持仓方向_u模式  合约张数   持仓均价  未实现盈亏 合约面值 leverage 币模式保证金
    DOGEUSD_PERP     30.5115    30.5115              1       0.0    0.00000    0.000000       10      1.5           10
    ADAUSD_210625          0          0           None       0.0    0.00000    0.000000       10      1.5           10
    XRPUSD_PERP      13.4522    14.2444              0      -1.0    0.85650   -0.792167       10      1.5           10
    BNBUSD_PERP    0.0893242  0.0981505              0      -3.0  294.76800   -0.008826       10      1.5           10
    TRXUSD_PERP      177.651    187.925              0      -1.0    0.06853  -10.273941       10      1.5           10
    """

    # 通过交易所接口获取合约账户信息
    # future_info = exchange.dapiPrivateGetAccount()
    future_info = retry_wrapper(exchange.dapiPrivateGetAccount, act_name='查看合约账户信息')

    # 将持仓信息转变成DataFrame格式
    positions_df = pd.DataFrame(future_info['positions'], dtype=float)
    positions_df = positions_df.set_index('symbol')
    # 筛选交易的币对
    positions_df = positions_df[positions_df.index.isin(symbol_config.keys())]

    # 将账户信息转变成DataFrame格式
    assets_df = pd.DataFrame(future_info['assets'], dtype=float)
    assets_df = assets_df.set_index('asset')

    # 根据symbol_config的信息，填充symbol_info
    t = pd.DataFrame(symbol_config).T
    symbol_info['合约面值'] = t['face_value']
    symbol_info['leverage'] = t['leverage']
    # symbol_info['币模式保证金'] = t['币模式保证金']

    # 根据持仓信息、账户信息中的值填充symbol_info
    symbol_info['未实现盈亏'] = positions_df['unrealizedProfit']  # 使用标记价格计算
    symbol_info['持仓均价'] = positions_df['entryPrice']
    symbol_info['合约币数'] = positions_df[
        'notionalValue']  # 开仓张数 * 合约面值 / 标记价格  https://www.binance.com/zh-CN/support/faq/d33f37e2c7fe4da3b35ffc904e8fbab5
    for symbol in symbol_config.keys():
        coin = symbol.split('USD')[0]  # 币安之后如果不用USD计价了，这个地方需要改。
        symbol_info.at[symbol, '原始币数'] = assets_df.at[
            coin, 'walletBalance']  # https://www.binance.com/zh-CN/support/faq/5d62f8be18d24544b5b6156094c16bf7
    symbol_info['账户币数'] = symbol_info['原始币数'] + symbol_info['未实现盈亏']

    # 计算合约张数：合约张数 =（未实现盈亏 + 合约币数）x 持仓均价 / 合约面值
    # 注意：计算出来的合约张数可能为负，在做空的时候
    symbol_info['合约张数'] = (symbol_info['未实现盈亏'] + symbol_info['合约币数']) * symbol_info['持仓均价'] / symbol_info['合约面值']
    symbol_info['合约张数'] = symbol_info['合约张数'].apply(lambda x: round(x, 0))  # 计算出来的张数可能是4.999，取整

    # ===判断u模式的持仓方向：
    if mode == 'u模式':
        # 现货多头 = 原始持币 x 持仓均价
        # 期货空头 = 合约张数 x 面值
        # 多空仓差 = 现货多头 - 期货空头
        symbol_info['现货多头'] = symbol_info['原始币数'] * symbol_info['持仓均价']
        symbol_info['期货头寸'] = symbol_info['合约张数'] * symbol_info['合约面值']  # 可能为负
        symbol_info['期现仓差'] = symbol_info['现货多头'] + symbol_info['期货头寸']

        # 期现仓差在合约面值之内，相当于期现套利平衡状态，相当于持有现金
        symbol_info.loc[abs(symbol_info['期现仓差']) < symbol_info['合约面值'], '持仓方向_' + mode] = 0
        # 现货多头占优，相当于做多
        symbol_info.loc[symbol_info['期现仓差'] >= symbol_info['合约面值'], '持仓方向_' + mode] = 1
        # 期货空头占优，相当于做空
        symbol_info.loc[symbol_info['期现仓差'] <= -symbol_info['合约面值'], '持仓方向_' + mode] = -1
        # 例外情况
        symbol_info.loc[symbol_info['合约张数'] == 0, '持仓方向_' + mode] = 1  # 当没有持仓时，持仓均价为0，现货多头为0；期货头寸为0，整体为0。
        symbol_info.loc[symbol_info['原始币数'] == 0, '持仓方向_' + mode] = None  # 账户中没有币
        # 删除数据
        for i in ['现货多头', '期货头寸', '期现仓差', '合约币数']:
            del symbol_info[i]

    # ===判断币模式的持仓方向：
    elif mode == '币模式':
        symbol_info.loc[symbol_info['合约张数'] == 0, '持仓方向_' + mode] = 0  # 相当于屯币状态
        symbol_info.loc[symbol_info['合约张数'] > 0, '持仓方向_' + mode] = 1  # 用屯币做保证金做多
        symbol_info.loc[symbol_info['合约张数'] < 0, '持仓方向_' + mode] = -1  # 用屯币做保证金做空

    symbol_info['asset'] = symbol_info.index
    symbol_info['asset'] = symbol_info['asset'].str.split('USD', expand=True)[0] + 'USDT'

    price_df = pd.DataFrame(retry_wrapper(exchange.publicGetTickerBookTicker, act_name='spot_ticker'), dtype=float)
    price_df = price_df[['symbol', 'bidPrice']]
    price_df.set_index('symbol', inplace=True)
    symbol_info = symbol_info.join(price_df, on='asset')
    symbol_info['实际美元价值'] = symbol_info['账户币数'] * symbol_info['bidPrice']
    symbol_info.drop(['asset', 'bidPrice'], inplace=True, axis=1)
    return symbol_info


# ===批量下单
def place_binance_cfuture_batch_order(exchange, symbol_order_params):
    num = 5  # 每个批量最多下单的数量
    order_info_list = []
    for i in range(0, len(symbol_order_params), num):
        order_list = symbol_order_params[i:i + num]
        params = {'batchOrders': exchange.json(order_list),
                  'timestamp': int(time.time() * 1000)}
        order_info = retry_wrapper(exchange.dapiPrivatePostBatchOrders, params=params, act_name='批量下单')
        order_info = pd.DataFrame(order_info)
        order_info_list.append(order_info)
        print('\n成交订单信息\n', order_info)
        time.sleep(short_sleep_time)
    return order_info_list


# ==========趋势策略相关函数==========
# 根据交易所的限制（最小下单单位、量等），修改下单的数量和价格
def modify_order_quantity_and_price(symbol, symbol_config, params):
    """
    根据交易所的限制（最小下单单位、量等），修改下单的数量和价格
    :param symbol:
    :param symbol_config:
    :param params:
    :return:
    """

    # 将下单进度调整为整数
    params['quantity'] = round(params['quantity'], None)

    # 买单加价2%，卖单降价2%
    params['price'] = params['price'] * 1.02 if params['side'] == 'BUY' else params['price'] * 0.98
    # params['price'] = params['price'] * 0.8 if params['side'] == 'BUY' else params['price'] * 1.2
    # 根据每个币种的精度，修改下单价格的精度
    params['price'] = round(params['price'], symbol_config[symbol]['最小下单价精度'])

    return params


# 根据最新数据，计算最新的signal
def calculate_signal(symbol_info, symbol_config, symbol_candle_data, mode):
    """
    计算交易信号
    :param symbol_info:
    :param symbol_config:
    :param symbol_candle_data:
    :return:

    输出案例：
    {'BNBUSD_PERP': '开空'}
    {'DOGEUSD_PERP': '平多，开空', 'TRXUSD_PERP': '开空'}
    """

    # 输出变量
    symbol_signal = {}
    save_dict = dict()

    # 逐个遍历交易对
    for symbol in symbol_config.keys():

        # 赋值相关数据
        df = symbol_candle_data[symbol].copy()  # 最新数据
        now_pos = symbol_info.at[symbol, '持仓方向_' + mode]  # 当前持仓方向
        avg_price = symbol_info.at[symbol, '持仓均价']  # 当前持仓均价

        # 需要计算的目标仓位
        target_pos = None

        # 根据策略计算出目标交易信号。
        if not df.empty:  # 当原始数据不为空的时候
            target_pos = getattr(Signals, symbol_config[symbol]['strategy_name'])(df, now_pos, avg_price,
                                                                                  symbol_config[symbol]['para'])
        if recent_k['used'] == 0:
            save_dict[symbol] = recent_k['k_line'].copy()
            del recent_k['k_line']
            recent_k['used'] = 1
            save_dict[symbol]['strategy_name'] = symbol_config[symbol]['strategy_name']
            save_dict[symbol]['para'] = symbol_config[symbol]['para']

        symbol_info.at[symbol, '目标持仓'] = target_pos  # 这行代码似乎可以删除

        symbol_info.at[symbol, '信号'] = 'NaN'
        # 根据目标仓位和实际仓
        if now_pos == 1 and target_pos == 0:  # 平多
            symbol_signal[symbol] = '平多'
            symbol_info.at[symbol, '信号'] = '平多'
        elif now_pos == -1 and target_pos == 0:  # 平空
            symbol_signal[symbol] = '平空'
            symbol_info.at[symbol, '信号'] = '平空'
        elif now_pos == 0 and target_pos == 1:  # 开多
            symbol_signal[symbol] = '开多'
            symbol_info.at[symbol, '信号'] = '开多'
        elif now_pos == 0 and target_pos == -1:  # 开空
            symbol_signal[symbol] = '开空'
            symbol_info.at[symbol, '信号'] = '开空'
        elif now_pos == 1 and target_pos == -1:  # 平多，开空
            symbol_signal[symbol] = '平多，开空'
            symbol_info.at[symbol, '信号'] = '平多，开空'
        elif now_pos == -1 and target_pos == 1:  # 平空，开多
            symbol_signal[symbol] = '平空，开多'
            symbol_info.at[symbol, '信号'] = '平空，开多'

        symbol_info.at[symbol, '信号时间'] = datetime.now()  # 计算产生信号的时间

    return symbol_signal, save_dict


# 针对某个类型订单，计算下单参数。供cal_all_order_info函数调用
def cal_all_order_info(symbol_signal, symbol_info, symbol_config, exchange, mode):
    """
    :param symbol_signal:
    :param symbol_info:
    :param symbol_config:
    :param exchange:
    :param mode:
    :return:
    输出案例
     [{'symbol': 'BNBUSD_PERP', 'side': 'BUY', 'price': '363.347', 'type': 'LIMIT', 'timeInForce': 'GTC', 'quantity': '4'}]

     [
     {'symbol': 'DOGEUSD_PERP', 'side': 'SELL', 'price': '0.353466', 'type': 'LIMIT', 'timeInForce': 'GTC', 'quantity': '3'},
     {'symbol': 'XRPUSD_PERP', 'side': 'SELL', 'price': '0.9984', 'type': 'LIMIT', 'timeInForce': 'GTC', 'quantity': '2'}
     ]
    """

    symbol_order_params = []

    # 如果没有信号，跳过
    if not symbol_signal:
        print('本周期无交易指令，不执行交易操作')
        return symbol_order_params

    # 有信号
    if mode == 'u模式':
        # 更新每个币的balance信息
        symbol_info = binance_update_cfuture_balance(exchange, symbol_config, symbol_info)
        print('更新账户币总数')
        print(symbol_info)

    # 遍历有交易信号的交易对
    for symbol in symbol_signal.keys():  # {'eth-usdt': '开空', 'eos-usdt': '平多，开空'}
        signal_type = symbol_signal[symbol]
        print(symbol, signal_type)

        params = {
            'symbol': symbol,
            'side': binance_order_type[signal_type],
            'price': symbol_info.at[symbol, '当前价格'],
            'type': 'LIMIT',
            'timeInForce': 'GTC',
        }
        if mode == 'u模式':
            if signal_type in ['平空', '平多']:
                # 平空：原来是-200张，希望变成-100张
                # 平多：原来是（-50、0、100、200张），希望变成-100张
                target_future_num = symbol_info.at[symbol, '账户币数'] * symbol_info.at[symbol, '当前价格'] / symbol_info.at[
                    symbol, '合约面值']
                target_future_num *= -1

            elif signal_type in ['开空', '平多，开空']:
                # 开空：原来是-100张，希望变成-200张
                # 平多，开空：原来是（-50、0、100、200张），希望变成-200张
                target_future_num = symbol_info.at[symbol, '账户币数'] * (symbol_info.at[symbol, 'leverage'] + 1) * \
                                    symbol_info.at[symbol, '当前价格'] / symbol_info.at[symbol, '合约面值']
                target_future_num *= -1

            elif signal_type in ['开多', '平空，开多']:
                # 开多：原来是-100张，希望变成(-50、0、100、200张)
                # 平空，开多：原来是-200张，希望变成(-50、0、100、200张)
                target_future_num = symbol_info.at[symbol, '账户币数'] * (symbol_info.at[symbol, 'leverage'] - 1) * \
                                    symbol_info.at[symbol, '当前价格'] / symbol_info.at[symbol, '合约面值']

            params['quantity'] = symbol_info.at[symbol, '合约张数'] - target_future_num
            params['quantity'] = abs(params['quantity'])

        elif mode == '币模式':
            if signal_type in ['平空', '平多']:
                params['quantity'] = abs(symbol_info.at[symbol, '合约张数'])
            elif signal_type in ['开空', '开多']:
                params['quantity'] = symbol_info.at[symbol, '币模式保证金'] / symbol_info.at[symbol, '合约面值']
            elif signal_type in ['平多，开空', '平空，开多']:
                open_quantity = symbol_info.at[symbol, '币模式保证金'] / symbol_info.at[symbol, '合约面值']
                close_quantity = abs(symbol_info.at[symbol, '合约张数'])
                params['quantity'] = open_quantity + close_quantity

        # 修改下单价格、数量精度
        params = modify_order_quantity_and_price(symbol, symbol_config, params)

        if params['quantity'] == 0:  # 考察下单量是否为0
            print('\n', symbol, '下单量为0，忽略')
        else:
            # 改成str
            params['price'] = str(params['price'])
            params['quantity'] = str(params['quantity'])
            symbol_order_params.append(params)

    return symbol_order_params


# 建立初始状态,合约账户未开仓,合约账户币种余额为0
def trading_initialization(exchange, account_name, funding_config, symbol_config, main_acc_ex):
    for symbol in symbol_config.keys():
        symbol_spot = symbol[:symbol.find('USD')].upper()
        market = exchange.dapiPublicGetExchangeInfo()
        df_market = pd.DataFrame(market['symbols']).set_index('symbol')
        coin_precision = int(df_market.loc[symbol, 'pricePrecision'])
        contract_size = int(df_market.loc[symbol, 'contractSize'])
        symbol_config[symbol]['face_value'] = contract_size
        df_balance = pd.DataFrame(exchange.dapiPrivateGetAccount()['assets'])
        hold_margin_num = float(df_balance.loc[df_balance['asset'] == symbol_spot, 'walletBalance'].values[0]) + float(
            df_balance.loc[df_balance['asset'] == symbol_spot, 'unrealizedProfit'].values[0])

        symbol_spot_qr = symbol_spot + funding_config['funding_coin'].upper()
        symbol_spot_tr = symbol_spot + funding_config['funding_coin'].upper()
        spot_sell1_price = float(exchange.publicGetTickerBookTicker(params={'symbol': symbol_spot_qr})['askPrice'])
        symbol_usd_value = hold_margin_num * spot_sell1_price
        print('币本位账户现有保证金%f，美元价值%f' % (hold_margin_num, symbol_usd_value))
        if symbol_config[symbol]['initial_funds'] or symbol_usd_value - 5.000001 <= 0:
            exchange.dapiPrivatePostLeverage(params={'symbol': symbol, 'leverage': 20})
            if symbol_config[symbol]['initial_funds'] is False and symbol_usd_value - 5.000001 <= 0:
                print('%s币本位保证金%f个， 美元价值$%f，不足$5，强制初始化' % (symbol_spot,hold_margin_num, symbol_usd_value))
            # 如果保证金为0，将强制初始化
            expect_amt = symbol_config[symbol]['initial_usd_funds']/contract_size
            expect_margin_num = symbol_config[symbol]['initial_usd_funds'] / spot_sell1_price
            print('币本位账户期望保证金%f，美元价值%f' % (expect_margin_num, expect_margin_num * spot_sell1_price))
            df_position = pd.DataFrame(exchange.dapiPrivateGetPositionRisk())
            position_amt = float(df_position.loc[(df_position['symbol'] == symbol) & (df_position['positionSide'] == 'BOTH'), 'positionAmt'].values[0])
            if (hold_margin_num - expect_margin_num) * spot_sell1_price > 0.1:
                surplus_num = hold_margin_num - expect_margin_num
                print('%s划转多余保证金%s%f到现货账户' % (symbol, symbol_spot, surplus_num))
                binance_account_transfer(exchange=exchange, currency=symbol_spot, amount=surplus_num,
                                         from_account='合约',
                                         to_account='币币')
                time.sleep(3)
                if funding_config['surplus_spot_deal'] == 'TO_MAIN':
                    print('多余现货%s划转母账户，数量%f!注意，母账户需手动卖出!!' % (symbol_spot, surplus_num))
                    info = binance_main_sub_transfer(main_acc_ex, symbol_spot, surplus_num * 0.999,
                                                     from_email=api_dict[account_name]['email'])
                    print(info)
            else:
                if ((expect_margin_num - hold_margin_num) * spot_sell1_price > contract_size * 0.9) or symbol_usd_value - 5.000001 <= 0:
                    buy_absence_spot_to_margin(exchange, main_acc_ex, expect_margin_num - hold_margin_num, symbol_spot, symbol_spot_qr,
                                               symbol_spot_tr, account_name)
                else:
                    print('现有%s保证金与期望保证金相差的美元价值小于合约面值%f，不必补充保证金！' % (symbol_spot, (contract_size)))

            deal_amt = expect_amt + position_amt
            print('开始初始化套保仓位！')
            if deal_amt != 0:
                long_or_short = '开多' if deal_amt < 0 else '开空'
                future_buy1_price = exchange.dapiPublicGetTickerBookTicker(params={'symbol': symbol})[0]['bidPrice']
                price = float(future_buy1_price) * 1.02 if deal_amt < 0 else float(future_buy1_price) * 0.98
                price = round(price, coin_precision)
                deal_amt = abs(int(deal_amt))
                future_order_info = binance_future_place_order(exchange=exchange, symbol=symbol,
                                                               long_or_short=long_or_short, price=price,
                                                               amount=deal_amt)
                print('合约%s成交%f张，方向%s，信息如下：' % (symbol, deal_amt, long_or_short))
                print(future_order_info)

            print('%s初始化完成！' % symbol)
        else:
            print('%s用户设置不进行初始化建仓，且账户保证金价值>$5，初始化完成！' % symbol)
    return True


def buy_absence_spot_to_margin(exchange, main_acc_ex, absence_num, symbol_spot, symbol_spot_qr, symbol_spot_tr, account_name):

    print('尝试从现货账户提取保证金......')
    df_spot = pd.DataFrame(exchange.privateGetAccount()['balances'])
    spot_num = float(df_spot.loc[df_spot['asset'] == symbol_spot, 'free'].values[0])
    still_absence_num = 0
    df_main_spot = pd.DataFrame(main_acc_ex.privateGetAccount()['balances'])
    main_spot_num = float(df_main_spot.loc[df_main_spot['asset'] == symbol_spot, 'free'].values[0])
    if spot_num >= absence_num:
        print('现货账户有%s数量：%f，尚需求保证金数量%f，数量足够，故从现货提取保证金' % (symbol_spot, spot_num, absence_num))
    else:
        still_absence_num = absence_num - spot_num
        if funding_config['spot_from_main_acc']:
            print('现货账户有%s数量：%f，尚需求保证金数量%f，数量不足，尝试从母账户划转现货...' % (symbol_spot, spot_num, absence_num))
            if main_spot_num >= still_absence_num:
                print('母账户有%s数量：%f，尚需求保证金数量%f，数量足够，故从母账户现货提取全额保证金' % (symbol_spot, main_spot_num, still_absence_num))
            else:
                print('母账户有%s数量：%f，尚需求保证金数量%f，数量不足，故从母账户现货提取保证金%f,剩余缺口:%f' % (symbol_spot, main_spot_num, still_absence_num, main_spot_num, still_absence_num - main_spot_num))
            transfer_num = min(main_spot_num, still_absence_num)
            if transfer_num > 0:
                info = binance_main_sub_transfer(main_acc_ex, symbol_spot, transfer_num, to_email=api_dict[account_name]['email'])
                print('现货%s从母账户转入成功...数量%f,transfer_id:' % (symbol_spot, transfer_num))
                print(info)
                still_absence_num = still_absence_num - main_spot_num
    if still_absence_num > 0:
        spot_sell1_price = float(exchange.publicGetTickerBookTicker(params={'symbol': symbol_spot_qr})['askPrice'])
        buy_num = max((15 / float(spot_sell1_price)), still_absence_num)
        print('现货余额不足，尚需保证金以计价币%s购买，购买所需计价币约为：%f' % (funding_config['funding_coin'], still_absence_num * spot_sell1_price))
        if still_absence_num < (15 / float(spot_sell1_price)):
            print('购买金额过小，使用预设最低购买金额$15购买!')
        price = float(spot_sell1_price) * 1.02
        absence_amount = buy_num * price - float(df_spot.loc[df_spot['asset'] == funding_config['funding_coin'], 'free'].values[0])
        print('子账户现货账户计价币%s余额：%f' % (funding_config['funding_coin'], float(df_spot.loc[df_spot['asset'] == funding_config['funding_coin'], 'free'].values[0])))
        if absence_amount > 0.01:
            print('子账户计价币%s不足，缺口:%f' % (funding_config['funding_coin'], absence_amount))
            if funding_config['funding_coin_from_main_acc'] is True:
                print('尝试从母账户转入计价币%s...数量%f' % (funding_config['funding_coin'], absence_amount))
                main_funding_amount = float(df_main_spot.loc[df_main_spot['asset'] == funding_config['funding_coin'], 'free'].values[0])
                if main_funding_amount >= absence_amount:
                    info = binance_main_sub_transfer(main_acc_ex, funding_config['funding_coin'], absence_amount,
                                                     to_email=api_dict[account_name]['email'])
                    print('计价币%s转入成功...数量%f,transfer_id:' % (funding_config['funding_coin'], absence_amount))
                    print(info)
                    time.sleep(5)
                else:
                    print('母账户计价币不足，脚本退出')
                    exit()
            else:
                print('设置为不从母账户提取计价币，计价币不足，脚本退出')
                exit()
        spot_order_info = binance_spot_place_order(exchange=exchange, symbol=symbol_spot_tr,
                                                   long_or_short='买入', price=price, amount=buy_num)
        print('买入%s现货: %f,' % (symbol_spot, buy_num))
        print(spot_order_info)

    df_spot = pd.DataFrame(exchange.privateGetAccount()['balances'])
    spot_num = float(df_spot.loc[df_spot['asset'] == symbol_spot, 'free'].values[0])
    transfer_num = min(spot_num, absence_num)
    binance_account_transfer(exchange=exchange, currency=symbol_spot, amount=transfer_num,
                             from_account='币币',
                             to_account='合约')
    print('%s币币至合约划转成功！数量%f' % (symbol_spot, absence_num))
    time.sleep(3)
    df_spot = pd.DataFrame(exchange.privateGetAccount()['balances'])
    spot_num = float(df_spot.loc[df_spot['asset'] == symbol_spot, 'free'].values[0])
    if (funding_config['surplus_spot_deal'] == 'TO_MAIN') and (spot_num > 0):
        print('多余现货%s划转母账户，数量%f!注意，母账户需手动卖出!!' % (symbol_spot, spot_num))
        info = binance_main_sub_transfer(main_acc_ex, symbol_spot, spot_num,
                                         from_email=api_dict[account_name]['email'])
        print(info)


# def diff_future_spot(exchange, spot_symbol, future_symbol, r_threshold, sleep_time=2):
#     while True:
#         # spot_sell1_price = exchange.fapiPublicGetTickerBookTicker(params={'symbol': spot_symbol})['askPrice']  # 原
#         spot_sell1_price = exchange.publicGetTickerBookTicker(params={'symbol': spot_symbol})['askPrice']  # 改
#         # 获取期货买一数据。因为期货是卖出，取买一。
#         # noinspection PyUnresolvedReferences
#         future_buy1_price = exchange.dapiPublicGetTickerBookTicker(params={'symbol': future_symbol})[0][
#             'bidPrice']
#
#         # 计算价差
#         r = float(future_buy1_price) / float(spot_sell1_price) - 1
#         print('现货价格：%.4f，期货价格：%.4f，价差：%.4f%%' % (float(spot_sell1_price), float(future_buy1_price), r * 100))
#
#         # ===判断价差是否满足要求
#         if r < r_threshold:
#             print('利差小于目标阀值，不入金')
#             time.sleep(sleep_time)
#         else:
#             print('利差大于目标阀值，开始入金')
#             return spot_sell1_price, future_buy1_price
#
# # 'BNBUSD_PERP': {'leverage': 1.5,
# #                     'strategy_name': 'real_signal_simple_bolling_we',
# #                     'para': [100, 1.7],
# #                     'face_value': 10,
# #                     'initial_usd_funds': 20,
# #                     '币模式保证金': 10,
# #                     },


# 在币币账户下单
def binance_spot_place_order(exchange, symbol, long_or_short, price, amount):
    """
    :param exchange:  ccxt交易所
    :param symbol: 币币交易对代码，例如'BTC/USDT'
    :param long_or_short:  两种类型：买入、卖出
    :param price:  下单价格
    :param amount:  下单数量
    :return:
    """

    for i in range(5):
        try:
            # 买
            if long_or_short == '买入':
                order_info = exchange.create_limit_buy_order(symbol, amount, price)  # 买单
            # 卖
            elif long_or_short == '卖出':
                order_info = exchange.create_limit_sell_order(symbol, amount, price)  # 卖单
            else:
                raise ValueError('long_or_short只能是：`买入`或者`卖出`')

            print('binance币币交易下单成功：', symbol, long_or_short, price, amount)
            # print('下单信息：', order_info, '\n')
            return order_info

        except Exception as e:
            print('binance币币交易下单报错，1s后重试', e)
            time.sleep(1)

    print('binance币币交易下单报错次数过多，程序终止')
    exit()


# 在期货合约账户下限价单
def binance_future_place_order(exchange, symbol, long_or_short, price, amount):
    """
    :param exchange:  ccxt交易所
    :param symbol: 合约代码，例如'BTCUSD_210625'
    :param long_or_short:  四种类型：开多、开空、平多、平空
    :param price: 开仓价格
    :param amount: 开仓数量，这里的amount是合约张数
    :return:

    timeInForce参数的几种类型
    GTC - Good Till Cancel 成交为止
    IOC - Immediate or Cancel 无法立即成交(吃单)的部分就撤销
    FOK - Fill or Kill 无法全部立即成交就撤销
    GTX - Good Till Crossing 无法成为挂单方就撤销

    """

    if long_or_short == '开空':
        side = 'SELL'
    elif long_or_short == '开多':
        side = 'BUY'
    # 确定下单参数
    # 开空
    params = {
        'side': side,
        # 'positionSide': 'SHORT',
        'symbol': symbol,
        'type': 'LIMIT',
        'price': price,  # 下单价格
        'quantity': amount,  # 下单数量，注意此处是合约张数,
        'timeInForce': 'GTC',  # 含义见本函数注释部分
    }
    # 尝试下单
    for i in range(5):
        try:
            params['timestamp'] = int(time.time() * 1000)
            order_info = exchange.dapiPrivatePostOrder(params)
            print('币安合约交易下单成功：', symbol, long_or_short, price, amount)
            # print('下单信息：', order_info, '\n')
            return order_info
        except Exception as e:
            print('币安合约交易下单报错，1s后重试...', e)
            time.sleep(1)

    print('币安合约交易下单报错次数过多，程序终止')
    exit()


#
def binance_main_sub_transfer(main_acc_ex, asset, amount, from_email=None, to_email=None, fromAccountType='SPOT', toAccountType='SPOT'):
    params = {'fromAccountType': fromAccountType,
              'toAccountType': toAccountType,
              'asset': asset,
              'amount': amount, }
    if from_email:
        params['fromEmail'] = from_email
    if to_email:
        params['toEmail'] = to_email
    info = main_acc_ex.sapiPostSubAccountUniversalTransfer(params=params)
    return info


# binance各个账户间转钱
def binance_account_transfer(exchange, currency, amount, from_account='币币', to_account='合约'):
    """
    """

    if from_account == '币币' and to_account == '合约':
        transfer_type = 'MAIN_CMFUTURE'
    elif from_account == '合约' and to_account == '币币':
        transfer_type = 'CMFUTURE_MAIN'
    else:
        raise ValueError('未能识别`from_account`和`to_account`的组合，请参考官方文档')

    # 构建参数
    params = {
        'type': transfer_type,
        'asset': currency,
        'amount': amount,
    }

    # 开始转账
    for i in range(5):
        try:
            params['timestamp'] = int(time.time() * 1000)
            transfer_info = exchange.sapiPostAssetTransfer(params=params)
            print('转账成功：', from_account, 'to', to_account, amount)
            print('转账信息：', transfer_info, '\n')
            return transfer_info
        except Exception as e:
            print('转账报错，1s后重试', e)
            time.sleep(1)

    print('转账报错次数过多，程序终止')
    exit()

# ===发送钉钉相关函数
# 计算钉钉时间戳
def cal_timestamp_sign(secret):
    # 根据钉钉开发文档，修改推送消息的安全设置https://ding-doc.dingtalk.com/doc#/serverapi2/qf2nxq
    # 也就是根据这个方法，不只是要有robot_id，还要有secret
    # 当前时间戳，单位是毫秒，与请求调用时间误差不能超过1小时
    # python3用int取整
    timestamp = int(round(time.time() * 1000))
    # 密钥，机器人安全设置页面，加签一栏下面显示的SEC开头的字符串
    secret_enc = bytes(secret.encode('utf-8'))
    string_to_sign = '{}\n{}'.format(timestamp, secret)
    string_to_sign_enc = bytes(string_to_sign.encode('utf-8'))
    hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
    # 得到最终的签名值
    sign = parse.quote_plus(base64.b64encode(hmac_code))
    return str(timestamp), str(sign)


# 发送钉钉消息
def send_dingding_msg(content, robot_id=robot_id_secret[0], secret=robot_id_secret[1]):
    """
    :param content:
    :param robot_id:  你的access_token，即webhook地址中那段access_token。例如如下地址：https://oapi.dingtalk.com/robot/
n    :param secret: 你的secret，即安全设置加签当中的那个密钥
    :return:
    """
    try:
        msg = {
            "msgtype": "text",
            "text": {"content": content + '\n' + datetime.now().strftime("%m-%d %H:%M:%S")}}
        headers = {"Content-Type": "application/json;charset=utf-8"}
        # https://oapi.dingtalk.com/robot/send?access_token=XXXXXX&timestamp=XXX&sign=XXX
        timestamp, sign_str = cal_timestamp_sign(secret)
        url = 'https://oapi.dingtalk.com/robot/send?access_token=' + robot_id + \
              '&timestamp=' + timestamp + '&sign=' + sign_str
        body = json.dumps(msg)
        requests.post(url, data=body, headers=headers, timeout=10)
        print('成功发送钉钉')
    except Exception as e:
        print("发送钉钉失败:", e)


# price 价格 money 资金量 leverage 杠杆 ratio 最小变动单位
def calculate_max_size(price, money, leverage, ratio):
    return math.floor(money * leverage / price / ratio)


def send_dingding_and_raise_error(content):
    print(content)
    send_dingding_msg(content)
    raise ValueError(content)


def dingding_report_every_loop(symbol_info, symbol_signal, symbol_order, run_time, robot_id_secret, account_name):
    """
    :param symbol_info:
    :param symbol_signal:
    :param symbol_order:
    :param run_time:
    :param robot_id_secret:
    :return:
    """
    content = ''
    content += '# =====账户：' + str(account_name) + '\n\n'
    # 订单信息
    if symbol_signal:
        symbol_order_str = ['\n\n' + y.to_string() for x, y in symbol_order.iterrows()]  # 持仓信息
        content += '# =====订单信息' + ''.join(symbol_order_str) + '\n\n'

    # 持仓信息
    symbol_info_str = ['\n\n' + str(x) + '\n' + y.to_string() for x, y in symbol_info.iterrows()]
    content += '# =====持仓信息' + ''.join(symbol_info_str) + '\n\n'

    # 发送，每间隔30分钟或者有交易的时候，发送一次
    if run_time.hour % 15 == 0 or symbol_signal:
        if run_time.hour % 15 == 0 and len(symbol_signal) == 0:
            content = '# ===本次为15时定时播报持仓周期,无交易===' + content + '\n\n'

        send_dingding_msg(content, robot_id=robot_id_secret[0], secret=robot_id_secret[1])


def dingding_take_profit_report(take_info, account_name):
    content = '====子账户%s利润提取通知===' % account_name + '\n'
    symbol_info_str = ['\n\n' + str(x) + '\n' + y.to_string() for x, y in take_info.iterrows()]
    content += '-----提取明细' + ''.join(symbol_info_str) + '\n\n'
    send_dingding_msg(content)

# ================其他附加功能函数==================

# 储存信号
def save_signal_data(save_signals_dict, time_interval, offset, account_name, root_path):
    for symbol in save_signals_dict.keys():
        save_signals_dict[symbol]['time_interval'] = time_interval
        save_signals_dict[symbol]['offset_time'] = offset
        save_signals_dict[symbol]['account_name'] = account_name
        save_signals_dict[symbol]['symbol'] = symbol
        signal_file = os.path.join(root_path, 'data', 'save_signals', 'cfuture_cta',
                                   '%s_%s.csv' % (account_name, symbol))
        header = False if os.path.exists(signal_file) else True
        save_mode = 'a' if os.path.exists(signal_file) else 'w'
        pd.DataFrame(save_signals_dict[symbol]).T.to_csv(signal_file, mode=save_mode, index=False, header=header,
                                                         encoding='gb18030')
        print('已储存%s信号日志，路径%s' % (symbol, signal_file))


# 利润提取(按照阈值take_rate自动提取)
def take_profit(exchange, account_name, symbol_config, main_acc_ex, symbol_info, take_rate):
    take_list = []
    for symbol in symbol_info.index:
        position_side = symbol_info.at[symbol, '持仓方向_u模式']
        symbol_spot = symbol[:symbol.find('USD')].upper()
        margin_usd_value = symbol_info.at[symbol, '实际美元价值']
        initial_usd_funds = symbol_config[symbol]['initial_usd_funds']
        face_value = symbol_info.at[symbol, '合约面值']
        hold_margin_num = symbol_info.at[symbol, '账户币数']
        spot_sell1_price = margin_usd_value / hold_margin_num
        expect_amt = int(initial_usd_funds * take_rate / face_value)
        expect_margin_value = expect_amt * face_value
        surplus_num = (margin_usd_value - expect_margin_value) / spot_sell1_price
        if (surplus_num * spot_sell1_price > 1): # and (position_side == 0):
            print('%s符合提取利润条件，预计提取利润%f%s' % (symbol, surplus_num, symbol_spot))
            tmp_dict = dict()
            info = binance_main_sub_transfer(main_acc_ex, symbol_spot, surplus_num * 0.999,
                                             from_email=api_dict[account_name]['email'], fromAccountType='COIN_FUTURE')
            print('已提取利润到母账户，数量%f%s!注意，母账户需手动卖出!!' % (surplus_num * 0.999, symbol_spot))
            print(info)
            position_amt = symbol_info.at[symbol, '合约张数']
            deal_amt = expect_amt + position_amt
            print('处理多余仓位，以达到套保状态！')
            long_or_short = ''
            if deal_amt != 0:
                long_or_short = '开多' if deal_amt < 0 else '开空'
                market = exchange.dapiPublicGetExchangeInfo()
                df_market = pd.DataFrame(market['symbols']).set_index('symbol')
                coin_precision = int(df_market.loc[symbol, 'pricePrecision'])
                future_buy1_price = exchange.dapiPublicGetTickerBookTicker(params={'symbol': symbol})[0]['bidPrice']
                price = float(future_buy1_price) * 1.02 if deal_amt < 0 else float(future_buy1_price) * 0.98
                price = round(price, coin_precision)
                deal_amt = abs(int(deal_amt))
                future_order_info = binance_future_place_order(exchange=exchange, symbol=symbol,
                                                               long_or_short=long_or_short, price=price,
                                                               amount=deal_amt)
                print('合约%s成交%f张，方向%s，信息如下：' % (symbol, deal_amt, long_or_short))
                print(future_order_info)
            tmp_dict['account'] = account_name
            tmp_dict['symbol'] = symbol
            tmp_dict['coin'] = symbol_spot
            tmp_dict['take_profit_num'] = surplus_num * 0.999
            tmp_dict['future_deal_side'] = long_or_short
            tmp_dict['future_deal_amt'] = deal_amt
            take_list.append(tmp_dict)
    return take_list


# ====================动态调参相关==============================
# 读取并更新参数
def check_symbol_config_update(exchange, account_name, symbol_config, symbol_info):
    print('开始检查symbol_config是否更新，目前仅支持修改策略和策略参数！')
    symbol_config_new = json5.load(open('Dynamic_Config'))['account_info'][account_name]['symbol_config']  # 读取参数
    coin_future_exchange_info(exchange, symbol_config_new)
    forced_modify = json5.load(open('Dynamic_Config'))['forced_modify']  # 强制修改，即如果被修改的币种已持仓则强制平仓
    symbol_config_change = False
    for symbol in set(list(symbol_config_new.keys()) + list(symbol_config.keys())):
        if symbol not in symbol_config_new.keys():
            print('监测到%s在新的symbol_config中已删除，暂不支持删除币种，脚本结束！' % symbol)
            send_dingding_and_raise_error('监测到%s在新的symbol_config中已删除，暂不支持删除币种，脚本结束！' % symbol)
            exit()
        elif symbol not in symbol_config.keys():
            print('监测到新的symbol_config币种%s，暂不支持新增币种，脚本结束！' % symbol)
            send_dingding_and_raise_error('监测到新的symbol_config币种%s，暂不支持新增币种，脚本结束！' % symbol)
            exit()
        else:
            if (symbol_config_new[symbol]["strategy_name"] != symbol_config[symbol]["strategy_name"]) or (symbol_config_new[symbol]["para"] != symbol_config[symbol]["para"]):
                if symbol_info.at[symbol, '持仓方向_u模式'] == 0:
                    print('监测到%s的symbol_config有更新，且目前处于空仓状态，更新symbol_config。\n原symbol_config：\n' % symbol,
                          symbol_config[symbol],
                          '\n更新后symbol_config：\n', symbol_config_new[symbol])
                    symbol_config[symbol]["strategy_name"] = symbol_config_new[symbol]["strategy_name"]
                    symbol_config[symbol]["para"] = symbol_config_new[symbol]["para"]
                    symbol_config_change = True
                else:
                    if forced_modify:
                        order_info = close_c_future_position(exchange, symbol_info, symbol=symbol)
                        print('监测到%s在新的symbol_config中已更新，用户设置强制套保，更新symbol_config！平仓订单信息：\n' % symbol)
                        symbol_config[symbol]["strategy_name"] = symbol_config_new[symbol]["strategy_name"]
                        symbol_config[symbol]["para"] = symbol_config_new[symbol]["para"]
                        symbol_config_change = True
                        print(order_info)
                    else:
                        print('监测到%s的symbol_config有更新，但目前处于持仓状态，暂不更新symbol_config。' % symbol)

    if symbol_config_change:
        # 如果参数有变化，重新初始化并更新symbol_info
        symbol_info_columns = ['账户币数', '原始币数', '持仓方向_' + mode, '合约张数', '持仓均价', '未实现盈亏', '实际美元价值']
        symbol_info = pd.DataFrame(index=symbol_config.keys(), columns=symbol_info_columns)

        # 更新账户信息symbol_info
        symbol_info = binance_update_cfuture_account(exchange, symbol_config, symbol_info, mode)
        print('参数有更新，更新持仓信息\n', symbol_info)
        print('最新的symbol_config\n', pd.DataFrame(symbol_config))
    else:
        print('symbol_config无更新!')
    return symbol_config, symbol_info


# 平掉指定币种coin本位仓位
def close_c_future_position(exchange, symbol_info, symbol):
    symbol_spot = symbol[:symbol.find('USD')].upper()
    market = exchange.dapiPublicGetExchangeInfo()
    df_market = pd.DataFrame(market['symbols']).set_index('symbol')
    coin_precision = int(df_market.loc[symbol, 'pricePrecision'])
    contract_size = int(df_market.loc[symbol, 'contractSize'])
    df_balance = pd.DataFrame(exchange.dapiPrivateGetAccount()['assets'])
    hold_margin_num = float(df_balance.loc[df_balance['asset'] == symbol_spot, 'walletBalance'].values[0]) + float(
        df_balance.loc[df_balance['asset'] == symbol_spot, 'unrealizedProfit'].values[0])
    symbol_spot_qr = symbol_spot + funding_config['funding_coin'].upper()
    spot_sell1_price = float(exchange.publicGetTickerBookTicker(params={'symbol': symbol_spot_qr})['askPrice'])
    symbol_usd_value = hold_margin_num * spot_sell1_price
    print('币本位账户现有保证金%f，美元价值%f' % (hold_margin_num, symbol_usd_value))
    expect_amt = round(symbol_usd_value / contract_size)
    position_amt = symbol_info.at[symbol, '合约张数']
    deal_amt = expect_amt + position_amt

    if deal_amt != 0:
        print('开始套保仓位！')
        long_or_short = '开多' if deal_amt < 0 else '开空'
        future_buy1_price = exchange.dapiPublicGetTickerBookTicker(params={'symbol': symbol})[0]['bidPrice']
        price = float(future_buy1_price) * 1.02 if deal_amt < 0 else float(future_buy1_price) * 0.98
        price = round(price, coin_precision)
        deal_amt = abs(int(deal_amt))
        future_order_info = binance_future_place_order(exchange=exchange, symbol=symbol,
                                                       long_or_short=long_or_short, price=price,
                                                       amount=deal_amt)
        print('合约%s成交%f张，方向%s，信息如下：' % (symbol, deal_amt, long_or_short))
        print(future_order_info)
    else:
        print('特殊持仓，请联系little squirrel!')

