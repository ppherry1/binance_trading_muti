"""
《邢不行-2020新版|Python数字货币量化投资课程》
无需编程基础，助教答疑服务，专属策略网站，一旦加入，永续更新。
课程详细介绍：https://quantclass.cn/crypto/class
邢不行微信: xbx9025
本程序作者: 邢不行

# 课程内容
币安u本位择时策略实盘框架相关函数
"""
import ccxt
import math
import pandas as pd
from datetime import datetime, timedelta
import time
from binance_hedge.Config import *
from binance_hedge import Signals


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


# ===将最新数据和历史数据合并
def symbol_candle_data_append_recent_candle_data(symbol_candle_data, recent_candle_data, symbol_config, max_candle_num):

    for symbol in symbol_config.keys():
        df = symbol_candle_data[symbol].append(recent_candle_data[symbol], ignore_index=True, sort=False)
        df.drop_duplicates(subset=['candle_begin_time_GMT8'], keep='last', inplace=True)
        df.sort_values(by='candle_begin_time_GMT8', inplace=True)  # 排序，理论上这步应该可以省略，加快速度
        df = df.iloc[-max_candle_num:]  # 保持最大K线数量不会超过max_candle_num个
        df.reset_index(drop=True, inplace=True)
        symbol_candle_data[symbol] = df
        now = str(time.time())

    return symbol_candle_data


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

    for _ in range(retry_times):
        try:
            result = func(params=params)
            return result
        except Exception as e:
            print(act_name, '报错，报错内容：', str(e), '程序暂停(秒)：', sleep_seconds)
            time.sleep(sleep_seconds)
    else:
        # send_dingding_and_raise_error(output_info)
        raise ValueError(act_name, '报错重试次数超过上限，程序退出。')


# ==========交易所交互函数==========
# ===判断当前持仓模式
def if_oneway_mode(exchange):
    """
    判断当前合约持仓模式。必须得是单向模式。如果是双向模式，就报错。
    查询当前的持仓模式。使用函数：GET /fapi/v1/positionSide/dual (HMAC SHA256)
    判断持仓情况，False为单向持仓，True为单向持仓
    :param exchange:
    :return:
    """

    positionSide = retry_wrapper(exchange.fapiPrivateGetPositionSideDual, act_name='查看合约持仓模式')

    if positionSide['dualSidePosition']:
        raise ValueError("当前持仓模式为双向持仓，程序已停止运行。请去币安官网改为单向持仓。")
    else:
        print('当前持仓模式：单向持仓')


# ===获得币对精度
def usdt_future_exchange_info(exchange, symbol_config):
    """
    获取symbol_config中币种的最小下单价格、数量
    :param exchange:
    :return:
    使用接口：GET /fapi/v1/exchangeInfo
    文档：https://binance-docs.github.io/apidocs/futures/cn/#0f3f2d5ee7
    """

    # 获取u本为合约交易对的信息
    exchange_info = retry_wrapper(exchange.fapiPublic_get_exchangeinfo, act_name='查看合约基本信息')

    # 转化为dataframe
    df = pd.DataFrame(exchange_info['symbols'])
    # df['minPrice'] = df['filters'].apply(lambda x: x[0]['minPrice'])
    # df['minQty'] = df['filters'].apply(lambda x: x[1]['minQty'])
    df['tickSize'] = df['filters'].apply(lambda x: math.log(1/float(x[0]['tickSize']), 10))
    df['stepSize'] = df['filters'].apply(lambda x: math.log(1/float(x[1]['stepSize']), 10))
    df = df[['symbol', 'pricePrecision', 'quantityPrecision', 'tickSize', 'stepSize']]
    df.set_index('symbol', inplace=True)

    # 赋值
    for symbol in symbol_config.keys():
        symbol_config[symbol]['最小下单价精度'] = round(df.at[symbol, 'tickSize'])

        p = df.at[symbol, 'quantityPrecision']
        symbol_config[symbol]['最小下单量精度'] = None if int(p) == 0 else round(int(p))


# ===获取当前持仓信息
def binance_update_account(exchange, symbol_config, symbol_info):
    """
    获取u本位账户的持仓信息、账户余额信息
    :param exchange:
    :param symbol_config:
    :param symbol_info:
    :return:
    接口：GET /fapi/v2/account (HMAC SHA256)
    文档：https://binance-docs.github.io/apidocs/futures/cn/#v2-user_data-2
    币安的币本位合约，不管是交割，还是永续，共享一个账户。他们的symbol不一样。比如btc的永续合约是BTCUSDT，季度合约是BTCUSDT_210625
    """
    # ===获取持仓数据===
    # 获取账户信息
    # account_info = exchange.fapiPrivateGetAccount()
    account_info = retry_wrapper(exchange.fapiPrivateGetAccount, act_name='查看合约账户信息')

    # 将持仓信息转变成dataframe格式
    positions_df = pd.DataFrame(account_info['positions'], dtype=float)
    positions_df = positions_df.set_index('symbol')
    # 筛选交易的币对
    positions_df = positions_df[positions_df.index.isin(symbol_config.keys())]
    # 将账户信息转变成dataframe格式
    assets_df = pd.DataFrame(account_info['assets'], dtype=float)
    assets_df = assets_df.set_index('asset')

    # 根据持仓信息、账户信息中的值填充symbol_info
    balance = assets_df.loc['USDT', 'marginBalance']  # 保证金余额
    symbol_info['账户权益'] = balance

    symbol_info['持仓量'] = positions_df['positionAmt']
    symbol_info['持仓方向'] = symbol_info['持仓量'].apply(lambda x: 1 if float(x) > 0 else (-1 if float(x) < 0 else 0))

    symbol_info['持仓收益'] = positions_df['unrealizedProfit']
    symbol_info['持仓均价'] = positions_df['entryPrice']

    # 计算每个币种的分配资金（在无平仓的情况下）
    profit = symbol_info['持仓收益'].sum()
    symbol_info['分配资金'] = (balance - profit) * symbol_info['分配比例']

    return symbol_info


# ===获取当前持仓信息
def binance_update_account_strategy(exchange, strategy_config, strategy_info, symbol_config):
    """
    获取u本位账户的持仓信息、账户余额信息
    :param exchange:
    :param strategy_config:
    :param strategy_info:
    :return:
    接口：GET /fapi/v2/account (HMAC SHA256)
    文档：https://binance-docs.github.io/apidocs/futures/cn/#v2-user_data-2
    币安的币本位合约，不管是交割，还是永续，共享一个账户。他们的symbol不一样。比如btc的永续合约是BTCUSDT，季度合约是BTCUSDT_210625
    """

    # ===获取持仓数据===
    # 获取账户信息
    # account_info = exchange.fapiPrivateGetAccount()
    account_info = retry_wrapper(exchange.fapiPrivateGetAccount, act_name='查看合约账户信息')

    # 将持仓信息转变成dataframe格式
    positions_df = pd.DataFrame(account_info['positions'], dtype=float)
    positions_df = positions_df.set_index('symbol')
    # # 筛选交易的币对
    # positions_df = positions_df[positions_df.index.isin(strategy_config.keys())]
    # 将账户信息转变成dataframe格式
    assets_df = pd.DataFrame(account_info['assets'], dtype=float)
    assets_df = assets_df.set_index('asset')

    for strategy in strategy_info.index:
        strategy_info.loc[strategy].loc['策略币种'] = []
        strategy_info.loc[strategy].loc['持仓量s'] = []
        strategy_info.loc[strategy].loc['持仓方向s'] = []
        strategy_info.loc[strategy].loc['持仓均价s'] = []
        strategy_info.loc[strategy].loc['持仓收益s'] = []
        for symbol in symbol_config.keys():
            if strategy == symbol_config[symbol]['strategy_number']:
                strategy_info.loc[strategy].loc['策略币种'].append(symbol)
                p = positions_df['positionAmt'].loc[symbol]
                strategy_info.loc[strategy].loc['持仓量s'].append(p)
                strategy_info.loc[strategy].loc['持仓方向s'].append(1 if p > 0 else (-1 if p < 0 else 0))
                strategy_info.loc[strategy].loc['持仓均价s'].append(positions_df['entryPrice'].loc[symbol])
                strategy_info.loc[strategy].loc['持仓收益s'].append(positions_df['unrealizedProfit'].loc[symbol])

    # 根据持仓信息、账户信息中的值填充symbol_info
    balance = assets_df.loc['USDT', 'marginBalance']  # 保证金余额
    profit = positions_df['unrealizedProfit'].sum()
    strategy_info['分配资金'] = (balance - profit) * strategy_info['分配比例']

    strategy_info['持仓方向'] = strategy_info['持仓方向s'].apply(lambda x: x[0])
    strategy_info['持仓均价'] = strategy_info['持仓均价s'].apply(lambda x: x[0] / x[1])
    strategy_info['持仓收益'] = strategy_info['持仓收益s'].apply(lambda x: sum(x))

    return strategy_info


# ===通过ccxt获取K线数据
def ccxt_fetch_binance_candle_data(exchange, symbol, time_interval, limit):
    """
    获取指定币种的K线信息
    :param exchange:
    :param symbol:
    :param time_interval:
    :param limit:
    :return:
    """

    # 获取数据
    # data = exchange.fapiPublic_get_klines({'symbol': symbol, 'interval': time_interval, 'limit': limit})
    data = retry_wrapper(exchange.fapiPublic_get_klines, act_name='获取币种K线数据',
                         params={'symbol': symbol, 'interval': time_interval, 'limit': limit})

    # 整理数据
    df = pd.DataFrame(data, dtype=float)
    df.rename(columns={1: 'open', 2: 'high', 3: 'low', 4: 'close', 5: 'volume'}, inplace=True)
    df['candle_begin_time'] = pd.to_datetime(df[0], unit='ms')
    df['candle_begin_time_GMT8'] = df['candle_begin_time'] + timedelta(hours=8)
    df = df[['candle_begin_time_GMT8', 'open', 'high', 'low', 'close', 'volume']]

    return df


def ccxt_fetch_binance_more_candle_data(exchange, symbol, time_interval, limit):
    """
    获取某个币种在okex交易所所有能获取的历史数据，目前v3接口最多获取1440根
    :param exchange:
    :param symbol:
    :param time_interval:
    :param limit:
    :return:
    """
    # 获取当前时间
    now_milliseconds = int(time.time() * 1e3)

    # 每根K线的间隔时间
    time_interval_int = int(time_interval[:-1])  # 若15m，则time_interval_int = 15；若2h，则time_interval_int = 2
    time_segment = time_interval_int * 60 * 1000  # 15分钟 * 每分钟60s


    # 计算开始和结束的时间
    # end = now_milliseconds
    end = now_milliseconds - time_segment
    since = end - limit * time_segment

    # 循环获取历史数据
    all_kline_data = []
    while end - since >= time_segment:
        kline_data = retry_wrapper(exchange.fapiPublic_get_klines, act_name='获取币种K线数据',
                             params={'symbol': symbol, 'startTime': since, 'interval': time_interval, 'limit': min(1500, limit)})
        if kline_data:
            since = int(kline_data[-1][0]) + time_segment # 更新since，为下次循环做准备
            all_kline_data += kline_data
        else:
            break  # 抓取数据为空时，跳出循环

    # 对数据进行整理
    df = pd.DataFrame(all_kline_data, dtype=float)
    df.rename(columns={0: 'MTS', 1: 'open', 2: 'high', 3: 'low', 4: 'close', 5: 'volume'}, inplace=True)
    df['candle_begin_time'] = pd.to_datetime(df['MTS'], unit='ms')
    df['candle_begin_time_GMT8'] = df['candle_begin_time'] + timedelta(hours=8)
    df = df[['candle_begin_time_GMT8', 'open', 'high', 'low', 'close', 'volume']]

    # 删除重复的数据
    df.drop_duplicates(subset=['candle_begin_time_GMT8'], keep='last', inplace=True)
    df.reset_index(drop=True, inplace=True)

    # 为了保险起见，去掉最后一行最新的数据
    df = df[:-1]

    return df


# ===单线程获取需要的K线数据，并检测质量。
def single_threading_get_binance_candle_data(exchange, symbol_config, symbol_info, time_interval, run_time, candle_num, exec_interval, offset_time):

    symbol_candle_data = dict()  # 用于存储K线数据
    exec_interval = exec_interval.replace('m', 'T')
    offset_time = int(offset_time[:-1])

    print('开始获取K线数据')
    # 遍历每一个币种
    for symbol in symbol_config.keys():
        print(symbol, '开始时间：', datetime.now(), end=' ')

        # 获取symbol该品种最新的K线数据
        if candle_num <= 1500:
            df = ccxt_fetch_binance_candle_data(exchange, symbol, time_interval, limit=candle_num)
        else:
            df = ccxt_fetch_binance_more_candle_data(exchange, symbol, time_interval, limit=candle_num)

        # 重组K线
        df = df.resample(rule=exec_interval, base=offset_time, on='candle_begin_time_GMT8', label='left', closed='left').agg(
            {'open': 'first',
             'high': 'max',
             'low': 'min',
             'close': 'last',
             'volume': 'sum',
             }).reset_index(drop=False)

        # 如果获取数据为空，再次获取
        # if df.empty:
            # continue

        # 获取到了最新数据
        print('结束时间：', datetime.now())
        symbol_info.at[symbol, '当前价格'] = df.iloc[-1]['close']  # 该品种的最新价格
        symbol_candle_data[symbol] = df[df['candle_begin_time_GMT8'] < pd.to_datetime(run_time)]  # 去除run_time周期的数据

    return symbol_candle_data


# ===获取需要的币种的历史K线数据。
def get_binance_candle_data(exchange, symbol_config, time_interval, candle_num, is_history=True, symbol_info=None, run_time=None):

    symbol_candle_data = dict()  # 用于存储K线数据
    print('获取交易币种的历史K线数据')

    # 遍历每一个币种
    for symbol in symbol_config.keys():

        # 获取symbol该品种最新的K线数据
        if candle_num <= 1500:
            df = ccxt_fetch_binance_candle_data(exchange, symbol, time_interval, limit=candle_num)
        else:
            df = ccxt_fetch_binance_more_candle_data(exchange, symbol, time_interval, limit=candle_num)

        print(symbol, '获取历史数据行数：', len(df))

        symbol_candle_data[symbol] = df  # 去除run_time周期的数据
        time.sleep(medium_sleep_time)

        if is_history:
            print(symbol)
            print(symbol_candle_data[symbol].tail(3))
        else:
            print('结束时间：', datetime.now())
            symbol_info.at[symbol, '当前价格'] = df.iloc[-1]['close']  # 该品种的最新价格
            symbol_candle_data[symbol] = df[df['candle_begin_time_GMT8'] < pd.to_datetime(run_time)]  # 去除run_time周期的数据

    return symbol_candle_data


# ===获取需要的币种的历史K线数据。
def binance_resample_candle_data(symbol_candle_data, exec_interval, offset_time='0m', drop=0):
    offset_time = int(offset_time[:-1])
    exec_interval = exec_interval[:-1] + 'T'

    # 遍历每一个币种
    for symbol in symbol_candle_data.keys():

        # resampleK线
        symbol_candle_data[symbol] = symbol_candle_data[symbol].resample(rule=exec_interval, base=offset_time, on='candle_begin_time_GMT8', label='left', closed='left').agg(
            {'open': 'first',
             'high': 'max',
             'low': 'min',
             'close': 'last',
             # 'volume': 'sum',
             }).reset_index(drop=False)

        # 为了保险起见，去掉最后一行最新的数据
        if drop == 0:
            symbol_candle_data[symbol] = symbol_candle_data[symbol]
        else:
            symbol_candle_data[symbol] = symbol_candle_data[symbol][:drop]
        print(symbol, 'resample数据行数：', len(symbol_candle_data[symbol]))

        print(symbol_candle_data[symbol].tail(3))

    return symbol_candle_data


# ===批量下单
def place_binance_batch_order(exchange, symbol_order_params):

    num = 5  # 每个批量最多下单的数量
    for i in range(0, len(symbol_order_params), num):
        order_list = symbol_order_params[i:i + num]
        params = {'batchOrders': exchange.json(order_list),
                  'timestamp': int(time.time() * 1000)}
        # order_info = exchange.fapiPrivatePostBatchOrders(params)
        order_info = retry_wrapper(exchange.fapiPrivatePostBatchOrders, params=params, act_name='批量下单')

        print('\n成交订单信息\n', order_info)
        time.sleep(short_sleep_time)


# ==========趋势策略相关函数==========
def calculate_strategy_signal(strategy_info, strategy_config, strategy_candle_data):
    """
    计算交易信号
    :param strategy_info:
    :param strategy_config:
    :param strategy_candle_data:
    :return:
    """
    # return变量
    strategy_signal = {
        '平多': [],
        '平空': [],
        '开多': [],
        '开空': [],
        '平多开空': [],
        '平空开多': [],
    }

    # 逐个遍历交易对
    for strategy in strategy_config.keys():

        # 赋值相关数据
        df = strategy_candle_data[strategy].copy()  # 最新数据
        now_pos = strategy_info.at[strategy, '持仓方向']  # 当前持仓方向
        avg_price = strategy_info.at[strategy, '持仓均价']  # 当前持仓均价

        # 需要计算的目标仓位
        target_pos = None

        # 根据策略计算出目标交易信号。
        if not df.empty:  # 当原始数据不为空的时候
            target_pos = getattr(Signals, strategy_config[strategy]['strategy_name'])(df, now_pos, avg_price,
                                                                                    strategy_config[strategy]['para'])
            strategy_info.at[strategy, '目标持仓'] = target_pos

        # 根据目标仓位和实际仓位，计算实际操作
        if now_pos == 1 and target_pos == 0:  # 平多
            strategy_signal['平多'].append(strategy)
        elif now_pos == -1 and target_pos == 0:  # 平空
            strategy_signal['平空'].append(strategy)
        elif now_pos == 0 and target_pos == 1:  # 开多
            strategy_signal['开多'].append(strategy)
        elif now_pos == 0 and target_pos == -1:  # 开空
            strategy_signal['开空'].append(strategy)
        elif now_pos == 1 and target_pos == -1:  # 平多，开空
            strategy_signal['平多开空'].append(strategy)
        elif now_pos == -1 and target_pos == 1:  # 平空，开多
            strategy_signal['平空开多'].append(strategy)

        strategy_info.at[strategy, '信号时间'] = datetime.now()  # 计算产生信号的时间

    # 删除没有信号的操作
    for key in list(strategy_signal.keys()):
        if not strategy_signal.get(key):
            del strategy_signal[key]

    return strategy_signal


def calculate_symbol_signal(strategy_signal, strategy_info):

    symbol_signal = {
        '平多': [],
        '平空': [],
        '开多': [],
        '开空': [],
        '平多开空': [],
        '平空开多': [],
    }

    for signal in strategy_signal.keys():
        if signal == '平多':
            for strategy in strategy_signal[signal]:
                symbol_signal['平多'].append(strategy_info['策略币种'].loc[strategy][0])
                symbol_signal['平空'].append(strategy_info['策略币种'].loc[strategy][1])
        elif signal == '平空':
            for strategy in strategy_signal[signal]:
                symbol_signal['平空'].append(strategy_info['策略币种'].loc[strategy][0])
                symbol_signal['平多'].append(strategy_info['策略币种'].loc[strategy][1])
        elif signal == '开多':
            for strategy in strategy_signal[signal]:
                symbol_signal['开多'].append(strategy_info['策略币种'].loc[strategy][0])
                symbol_signal['开空'].append(strategy_info['策略币种'].loc[strategy][1])
        elif signal == '开空':
            for strategy in strategy_signal[signal]:
                symbol_signal['开空'].append(strategy_info['策略币种'].loc[strategy][0])
                symbol_signal['开多'].append(strategy_info['策略币种'].loc[strategy][1])
        elif signal == '平多开空':
            for strategy in strategy_signal[signal]:
                symbol_signal['平多开空'].append(strategy_info['策略币种'].loc[strategy][0])
                symbol_signal['平空开多'].append(strategy_info['策略币种'].loc[strategy][1])
        elif signal == '平空开多':
            for strategy in strategy_signal[signal]:
                symbol_signal['平空开多'].append(strategy_info['策略币种'].loc[strategy][0])
                symbol_signal['平多开空'].append(strategy_info['策略币种'].loc[strategy][1])

    # 删除没有信号的操作
    for key in list(symbol_signal.keys()):
        if not symbol_signal.get(key):
            del symbol_signal[key]

    return symbol_signal


# 根据交易所的限制（最小下单单位、量等），修改下单的数量和价格
def modify_order_quantity_and_price(symbol, symbol_config, params):
    """
    根据交易所的限制（最小下单单位、量等），修改下单的数量和价格
    :param symbol:
    :param symbol_config:
    :param params:
    :return:
    """

    # 根据每个币种的精度，修改下单数量的精度
    params['quantity'] = round(params['quantity'], symbol_config[symbol]['最小下单量精度'])

    # 买单加价2%，卖单降价2%
    params['price'] = params['price'] * 1.02 if params['side'] == 'BUY' else params['price'] * 0.98
    # 根据每个币种的精度，修改下单价格的精度
    params['price'] = round(params['price'], int(symbol_config[symbol]['最小下单价精度']))

    return params


# 针对某个类型订单，计算下单参数。供cal_all_order_info函数调用
def cal_order_params(signal_type, symbol, symbol_info, symbol_config):
    """
    针对某个类型订单，计算下单参数。供cal_all_order_info函数调用
    :param signal_type:
    :param symbol:
    :param symbol_info:
    :param symbol_config:
    :return:
    """

    params = {
        'symbol': symbol,
        'side': binance_order_type[signal_type],
        'price': symbol_info.at[symbol, '当前价格'],
        'type': 'LIMIT',
        'timeInForce': 'GTC',
    }

    if signal_type in ['平空', '平多']:
        params['quantity'] = abs(symbol_info.at[symbol, '持仓量'])

    elif signal_type in ['开多', '开空']:
        params['quantity'] = symbol_info.at[symbol, '分配资金'] * symbol_config[symbol]['leverage'] / \
                   symbol_info.at[symbol, '当前价格']

    else:
        close_quantity = abs(symbol_info.at[symbol, '持仓量'])
        open_quantity = symbol_info.at[symbol, '分配资金'] * symbol_config[symbol]['leverage'] / \
                        symbol_info.at[symbol, '当前价格']
        params['quantity'] = close_quantity + open_quantity

    # 修改精度
    print(symbol, '修改精度前', params)
    params = modify_order_quantity_and_price(symbol, symbol_config, params)
    print(symbol, '修改精度后', params)

    return params


# 计算所有币种的下单参数
def cal_all_order_info(symbol_signal, symbol_info, symbol_config, exchange):
    """

    :param symbol_signal:
    :param symbol_info:
    :param symbol_config:
    :param exchange:
    :return:
    """

    symbol_order_params = []

    # 如果没有信号，跳过
    if not symbol_signal:
        print('本周期无交易指令，不执行交易操作')
        return symbol_order_params

    # 如果只有平仓，或者只有开仓，无需重新更新持仓信息symbol_info
    if set(symbol_signal.keys()).issubset(['平空', '平多']) or set(symbol_signal.keys()).issubset(['开多', '开空']):
        print('本周期只有平仓或者只有开仓交易指令，无需再次更新账户信息，直接执行交易操作')

    # 如果有其他信号，需重新更新持仓信息symbol_info，然后据此重新计算下单量
    else:
        print('本周期有复杂交易指令（例如：平开、平和开、有平和平开、有开和平开），需重新更新账户信息，再执行交易操作')

        # 更新账户信息symbol_info
        symbol_info = binance_update_account(exchange, symbol_config, symbol_info)

        # 标记出需要把利润算作保证金的仓位。
        for signal in symbol_signal.keys():
            for symbol in symbol_signal[signal]:
                symbol_info.at[symbol, '利润参与保证金'] = 1

        # 计算分配资金
        all_profit = symbol_info['持仓收益'].sum()  # 所有利润
        profit = (symbol_info['持仓收益'] * symbol_info['利润参与保证金']).sum()  # 参与保证金的利润
        balance = symbol_info.iloc[0]['账户权益'] - all_profit  # 初始投入资金
        balance = balance + profit  # 平仓之后的利润或损失
        symbol_info['分配资金'] = balance * symbol_info['分配比例']
        print('\n更新持仓信息、分配资金信息\n', symbol_info)

    # 计算每个交易币种的各个下单参数
    for signal_type in symbol_signal.keys():
        for symbol in symbol_signal[signal_type]:
            params = cal_order_params(signal_type, symbol, symbol_info, symbol_config)

            if params['quantity'] == 0:  # 考察下单量是否为0
                print('\n', symbol, '下单量为0，忽略')
            elif params['price'] * params['quantity'] <= 5:  # 和最小下单额5美元比较
                print('\n', symbol, '下单金额小于5u，忽略')
            else:
                # 改成str
                params['price'] = str(params['price'])
                params['quantity'] = str(params['quantity'])
                symbol_order_params.append(params)

    return symbol_order_params


# ====新函数
def construct_strategy_symbol_candle(symbol_config, strategy_config, symbol_candle_data):
    # 用两币种K线，构造虚拟K线
    strategy_candle_data = dict()
    for strategy in strategy_config.keys():
        strategy_symbol_list = []
        for symbol in symbol_config.keys():
            if symbol_config[symbol]['strategy_number'] == strategy:
                strategy_symbol_list.append(symbol_candle_data[symbol].set_index('candle_begin_time_GMT8'))
        if len(strategy_symbol_list) == 2:
            strategy_symbol_candle = pd.DataFrame()
            strategy_symbol_candle['open'] = strategy_symbol_list[0]['open'] / strategy_symbol_list[1]['open']
            strategy_symbol_candle['close'] = strategy_symbol_list[0]['close'] / strategy_symbol_list[1]['close']
            strategy_symbol_candle['high'] = strategy_symbol_candle[['open', 'close']].max(axis=1)
            strategy_symbol_candle['low'] = strategy_symbol_candle[['open', 'close']].min(axis=1)
            # strategy_symbol_candle['volume'] = 1000
            strategy_candle_data[strategy] = strategy_symbol_candle.dropna().reset_index()
    return strategy_candle_data
