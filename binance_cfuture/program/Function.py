"""
邢不行2021策略分享会
微信：xbx2626
币安币本位择时策略框架
"""
import ccxt
import math
import time
import pandas as pd
from datetime import datetime, timedelta
import time
from binance_cfuture.program.Config import *
from binance_cfuture.program import Signals
pd.set_option('display.max_rows', 1000)
pd.set_option('expand_frame_repr', False)  # 当列太多时不换行
pd.set_option('display.unicode.ambiguous_as_wide', True)  # 设置命令行输出时的列对齐功能
pd.set_option('display.unicode.east_asian_width', True)


# ==========辅助功能函数==========
# ===下次运行时间，和课程里面讲的函数是一样的
def next_run_time(time_interval, ahead_seconds=5):
    """
    根据time_interval，计算下次运行的时间，下一个整点时刻。
    目前只支持分钟和小时。
    :param time_interval: 运行的周期，15m，1h
    :param ahead_seconds: 预留的目标时间和当前时间的间隙
    :return: 下次运行的时间
    案例：
    15m  当前时间为：12:50:51  返回时间为：13:00:00
    15m  当前时间为：12:39:51  返回时间为：12:45:00
    10m  当前时间为：12:38:51  返回时间为：12:40:00
    5m  当前时间为：12:33:51  返回时间为：12:35:00
    5m  当前时间为：12:34:51  返回时间为：12:35:00

    1h  当前时间为：14:37:51  返回时间为：15:00:00
    2h  当前时间为：00:37:51  返回时间为：02:00:00

    30m  当前时间为：21日的23:33:51  返回时间为：22日的00:00:00
    5m  当前时间为：21日的23:57:51  返回时间为：22日的00:00:00

    ahead_seconds = 5
    15m  当前时间为：12:59:57  返回时间为：13:15:00，而不是 13:00:00
    """
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
    now_time = datetime.now()
    # now_time = datetime(2019, 5, 9, 23, 50, 30)  # 指定now_time，可用于测试
    this_midnight = now_time.replace(hour=0, minute=0, second=0, microsecond=0)
    min_step = timedelta(minutes=1)

    target_time = now_time.replace(second=0, microsecond=0)

    while True:
        target_time = target_time + min_step
        delta = target_time - this_midnight
        if delta.seconds % ti.seconds == 0 and (target_time - now_time).seconds >= ahead_seconds:
            # 当符合运行周期，并且目标时间有足够大的余地，默认为60s
            break

    print('\n程序下次运行的时间：', target_time, '\n')
    return target_time


# ===依据时间间隔, 自动计算并休眠到指定时间
def sleep_until_run_time(time_interval, ahead_time=1, if_sleep=True):
    """
    根据next_run_time()函数计算出下次程序运行的时候，然后sleep至该时间
    :param time_interval:
    :param ahead_time:
    :param if_sleep:
    :return:
    """

    # 计算下次运行时间
    run_time = next_run_time(time_interval, ahead_time)

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
    df = df[df['adl'] >= 0]  # 筛选出大于等于4的币种
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
    df['tickSize'] = df['filters'].apply(lambda x: math.log(1/float(x[0]['tickSize']), 10))
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
def single_thread_get_binance_coin_future_candle_data(exchange, symbol_config, symbol_info, time_interval, run_time, candle_num):
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
    symbol_info['币模式保证金'] = t['币模式保证金']

    # 根据持仓信息、账户信息中的值填充symbol_info
    symbol_info['未实现盈亏'] = positions_df['unrealizedProfit']  # 使用标记价格计算
    symbol_info['持仓均价'] = positions_df['entryPrice']
    symbol_info['合约币数'] = positions_df['notionalValue']  # 开仓张数 * 合约面值 / 标记价格  https://www.binance.com/zh-CN/support/faq/d33f37e2c7fe4da3b35ffc904e8fbab5
    for symbol in symbol_config.keys():
        coin = symbol.split('USD')[0]  # 币安之后如果不用USD计价了，这个地方需要改。
        symbol_info.at[symbol, '原始币数'] = assets_df.at[coin, 'walletBalance']  # https://www.binance.com/zh-CN/support/faq/5d62f8be18d24544b5b6156094c16bf7
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
        symbol_info.loc[abs(symbol_info['期现仓差']) < symbol_info['合约面值'], '持仓方向_'+mode] = 0
        # 现货多头占优，相当于做多
        symbol_info.loc[symbol_info['期现仓差'] >= symbol_info['合约面值'], '持仓方向_'+mode] = 1
        # 期货空头占优，相当于做空
        symbol_info.loc[symbol_info['期现仓差'] <= -symbol_info['合约面值'], '持仓方向_'+mode] = -1
        # 例外情况
        symbol_info.loc[symbol_info['合约张数'] == 0, '持仓方向_'+mode] = 1  # 当没有持仓时，持仓均价为0，现货多头为0；期货头寸为0，整体为0。
        symbol_info.loc[symbol_info['原始币数'] == 0, '持仓方向_'+mode] = None  # 账户中没有币
        # 删除数据
        for i in ['现货多头', '期货头寸', '期现仓差', '合约币数']:
            del symbol_info[i]

    # ===判断币模式的持仓方向：
    elif mode == '币模式':
        symbol_info.loc[symbol_info['合约张数'] == 0, '持仓方向_'+mode] = 0  # 相当于屯币状态
        symbol_info.loc[symbol_info['合约张数'] > 0, '持仓方向_'+mode] = 1  # 用屯币做保证金做多
        symbol_info.loc[symbol_info['合约张数'] < 0, '持仓方向_'+mode] = -1  # 用屯币做保证金做空

    return symbol_info


# ===批量下单
def place_binance_cfuture_batch_order(exchange, symbol_order_params):
    num = 5  # 每个批量最多下单的数量
    for i in range(0, len(symbol_order_params), num):
        order_list = symbol_order_params[i:i + num]
        params = {'batchOrders': exchange.json(order_list),
                  'timestamp': int(time.time() * 1000)}
        order_info = retry_wrapper(exchange.dapiPrivatePostBatchOrders, params=params, act_name='批量下单')

        print('\n成交订单信息\n', order_info)
        time.sleep(short_sleep_time)


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

    # 逐个遍历交易对
    for symbol in symbol_config.keys():

        # 赋值相关数据
        df = symbol_candle_data[symbol].copy()  # 最新数据
        now_pos = symbol_info.at[symbol, '持仓方向_'+mode]  # 当前持仓方向
        avg_price = symbol_info.at[symbol, '持仓均价']  # 当前持仓均价

        # 需要计算的目标仓位
        target_pos = None

        # 根据策略计算出目标交易信号。
        if not df.empty:  # 当原始数据不为空的时候
            target_pos = getattr(Signals, symbol_config[symbol]['strategy_name'])(df, now_pos, avg_price, symbol_config[symbol]['para'])
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

    return symbol_signal


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

# 建立初始状态
def trading_initialization(funding_cofig, symbol_config):
    for symbol in symbol_config.keys():
        symbol_spot = symbol[:symbol.find('USD')] + '/' + funding_cofig['funding_coin'].upper()
        symbol_config[symbol]

        # if funding_from_spot:

    return


# 'BNBUSD_PERP': {'leverage': 1.5,
#                     'strategy_name': 'real_signal_simple_bolling_we',
#                     'para': [100, 1.7],
#                     'face_value': 10,
#                     'initial_usd_funds': 20,
#                     '币模式保证金': 10,
#                     },