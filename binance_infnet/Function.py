"""
网格策略实盘需要的相关函数
"""
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
from multiprocessing import Pool
from functools import partial
from binance_infnet.Config import *
from binance_infnet.Signals import *
from binance_infnet import Signals


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


# =====binance交互函数
# ===通过ccxt、交易所接口获取现货账户信息
def ccxt_fetch_spot_account(exchange, max_try_amount=5):
    """
    :param exchange:
    :param max_try_amount:
    :return:

    """
    for _ in range(max_try_amount):
        try:
            spot_info = exchange.private_get_account({
                'timestamp': int(time.time() * 1000)
            })
            df = pd.DataFrame(spot_info['balances'], dtype=float)  # 将数据转化为df格式
            return df
        except Exception as e:
            print('通过ccxt的通过private_get_accoun获取所有现货账户信息，失败，稍后重试：\n', e)
            time.sleep(medium_sleep_time)

    _ = '通过ccxt的通过private_get_accoun获取所有现货账户信息，失败次数过多，程序Raise Error'
    send_dingding_and_raise_error(_)


# ===通过ccxt获取K线数据
def ccxt_fetch_candle_data(exchange, symbol, time_interval, limit, max_try_amount=5):
    """
    本程序使用ccxt的私有函数public_get_klines，获取最新的K线数据，用于实盘
    :param exchange:
    :param symbol:
    :param time_interval:
    :param limit:
    :param max_try_amount:
    :return:
    """
    for _ in range(max_try_amount):
        try:
            # 获取当前时间
            now_milliseconds = int(time.time() * 1e3)

            # 每根K线的间隔时间
            time_interval_int = int(time_interval[:-1])  # 若15m，则time_interval_int = 15；若2h，则time_interval_int = 2
            if time_interval.endswith('m'):
                time_segment = time_interval_int * 60 * 1000  # 15分钟 * 每分钟60s
            elif time_interval.endswith('h'):
                time_segment = time_interval_int * 60 * 60 * 1000  # 2小时 * 每小时60分钟 * 每分钟60s

            # 计算开始和结束的时间
            end = now_milliseconds - time_segment
            since = end - limit * time_segment
            data = exchange.public_get_klines({
                "symbol": str(symbol).replace('-', ''),
                "interval": time_interval,
                "startTime": since,
                "endTime": end
            })
            # 整理数据
            df = pd.DataFrame(data, dtype=float)
            df.rename(columns={0: 'MTS', 1: 'open', 2: 'high',
                               3: 'low', 4: 'close', 5: 'volume'}, inplace=True)
            df['candle_begin_time'] = pd.to_datetime(df['MTS'], unit='ms')
            df['candle_begin_time_GMT8'] = df['candle_begin_time'] + timedelta(hours=8)
            df = df[['candle_begin_time_GMT8', 'open', 'high', 'low', 'close', 'volume']]
            df.sort_values(by=['candle_begin_time_GMT8'], inplace=True)
            return df
        except Exception as e:
            print('获取exchange.public_get_klines获取现货K线数据，失败，稍后重试。失败原因：\n', e)
            time.sleep(short_sleep_time)

        _ = '获取exchange.public_get_klines现货K线数据，失败次数过多，程序Raise Error'
        send_dingding_and_raise_error(_)


# =====趋势策略相关函数
# 根据账户信息、持仓信息，更新symbol_info
def update_symbol_info(exchange, symbol_info, symbol_config):
    """
    本函数通过ccxt_fetch_spot_account()获取现货账户信息，ccxt_fetch_spot_position()获取现货账户持仓信息，并用这些信息更新symbol_config
    :param exchange:
    :param symbol_info:
    :param symbol_config:
    :return:
    """

    # 通过交易所接口获取现货账户信息
    spot_account = ccxt_fetch_spot_account(exchange)
    # 将账户信息和symbol_info合并
    for symbol in symbol_config.keys():
        coins_list = symbol.split('-')
        # 交易币种
        base_currency = coins_list[0]
        # 计价币种
        quote_currency = coins_list[1]
        if quote_currency in spot_account['asset'].to_list():
            symbol_info.loc[symbol, '计价币种持仓量'] = \
                spot_account.loc[spot_account['asset'] == quote_currency, 'free'].to_list()[0]
        else:
            symbol_info.loc[symbol, '计价币种持仓量'] = 0.0
        if base_currency in spot_account['asset'].to_list():
            symbol_info.loc[symbol, '交易币种持仓量'] = \
                spot_account.loc[spot_account['asset'] == base_currency, 'free'].to_list()[0]
        else:
            symbol_info.loc[symbol, '交易币种持仓量'] = 0.0
    return symbol_info


# 获取需要的K线数据，并检测质量。
def get_candle_data(exchange, symbol_config, time_interval, run_time, max_try_amount, candle_num, symbol):
    """
    使用ccxt_fetch_candle_data(函数)，获取指定交易对最新的K线数据，并且监测数据质量，用于实盘。
    :param exchange:
    :param symbol_config:
    :param time_interval:
    :param run_time:
    :param max_try_amount:
    :param symbol:
    :param candle_num:
    :return:
    尝试获取K线数据，并检验质量
    """
    # 标记开始时间
    start_time = datetime.now()
    print('开始获取K线数据：', symbol, '开始时间：', start_time)

    # 获取数据现货的相关参数
    instrument_id = symbol_config[symbol]["instrument_id"]  # 现货id
    signal_price = None

    # 尝试获取数据
    for i in range(max_try_amount):
        # 获取symbol该品种最新的K线数据
        df = ccxt_fetch_candle_data(exchange, instrument_id, time_interval, limit=candle_num)
        if df.empty:
            continue  # 再次获取

        # 判断是否包含最新一根的K线数据。例如当time_interval为15分钟，run_time为14:15时，即判断当前获取到的数据中是否包含14:15这根K线
        # 【其实这段代码可以省略】
        if time_interval.endswith('m'):
            _ = df[df['candle_begin_time_GMT8'] == (run_time - timedelta(minutes=int(time_interval[:-1])))]
        elif time_interval.endswith('h'):
            _ = df[df['candle_begin_time_GMT8'] == (run_time - timedelta(hours=int(time_interval[:-1])))]
        else:
            print('time_interval不以m或者h结尾，出错，程序exit')
            exit()
        if _.empty:
            print('获取数据不包含最新的数据，重新获取')
            time.sleep(short_sleep_time)
            continue  # 再次获取

        else:  # 获取到了最新数据
            signal_price = df.iloc[-1]['close']  # 该品种的最新价格
            df = df[df['candle_begin_time_GMT8'] < pd.to_datetime(run_time)]  # 去除run_time周期的数据
            print('结束获取K线数据', symbol, '结束时间：', datetime.now())
            return symbol, df, signal_price

    print('获取candle_data数据次数超过max_try_amount，数据返回空值')
    print('信号价格：', signal_price)
    return symbol, pd.DataFrame(), signal_price


# 串行获取K线数据
def single_threading_get_data(exchange, symbol_info, symbol_config, time_interval, run_time, candle_num,
                              max_try_amount=5):
    """
    串行逐个获取所有交易对的K线数据，速度较慢。和multi_threading_get_data()对应
    若获取数据失败，返回空的dataframe。
    :param exchange:
    :param symbol_info:
    :param symbol_config:
    :param time_interval:
    :param run_time:
    :param candle_num:
    :param max_try_amount:
    :return:
    """
    # 函数返回的变量
    symbol_candle_data = {}
    for symbol in symbol_config.keys():
        symbol_candle_data[symbol] = pd.DataFrame()

    # 逐个获取symbol对应的K线数据
    for symbol in symbol_config.keys():
        _, symbol_candle_data[symbol], symbol_info.at[symbol, '信号价格'] = get_candle_data(exchange, symbol_config,
                                                                                        time_interval, run_time,
                                                                                        max_try_amount, candle_num,
                                                                                        symbol)

    return symbol_candle_data


# 根据最新数据，计算本次交易量
def calculate_trade_vol(symbol_info, symbol_config, symbol_candle_data):
    """
    计算本次交易量
    :param symbol_info:
    :param symbol_config:
    :param symbol_candle_data:
    :return:
    """

    # 输出变量
    symbol_signal = {}

    # 逐个遍历交易对
    for symbol in symbol_config.keys():

        # 赋值相关数据
        df = symbol_candle_data[symbol].copy()  # 最新数据
        now_pos = symbol_info.loc[symbol, '交易币种持仓量']  # 当前持仓量
        base_invest_val = symbol_config[symbol]['base_invest_val']  # 当前持仓均价
        invested_times = symbol_config[symbol]['invested_times']
        para = symbol_config[symbol]['para']
        # 需要计算的交易量
        trade_val = None

        # 根据策略计算出目标交易量。
        if not df.empty:  # 当原始数据不为空的时候
            trade_val = getattr(Signals, symbol_config[symbol]['strategy_name'])(df, now_pos, base_invest_val,
                                                                                 invested_times, para)
        symbol_info.at[symbol, '本次计划交易额'] = trade_val
        trade_vol = trade_val / df.iloc[-1]['close']
        symbol_info.at[symbol, '本次计划交易量'] = trade_vol

    return symbol_info


# 获取现货精度
def get_spot_exchange_Info(exchange, symbol_config):
    exchange_info = retry_wrapper(exchange.public_get_exchangeinfo, act_name='查看现货精度')
    df = pd.DataFrame(exchange_info['symbols'])
    df['tickSize'] = df['filters'].apply(lambda x: math.log(1 / float(x[0]['tickSize']), 10))
    df['stepSize'] = df['filters'].apply(lambda x: math.log(1 / float(x[2]['stepSize']), 10))
    df = df[['symbol', 'tickSize', 'stepSize']]
    df.set_index('symbol', inplace=True)
    # 赋值
    for symbol in symbol_config.keys():
        exchange_symbol = symbol.replace('-', '')
        symbol_config[symbol]['最小下单价精度'] = int(df.at[exchange_symbol, 'tickSize'])

        p = int(df.at[exchange_symbol, 'stepSize'])
        symbol_config[symbol]['最小下单量精度'] = None if p == 0 else p


# 在现货市场下单
def binance_spot_place_order(exchange, symbol_info, symbol_config, trade_side, trade_vol, max_try_amount, symbol):
    """
    :param exchange:
    :param symbol_info:
    :param symbol_config:
    :param max_try_amount:
    :param symbol:
    :return:
    """
    # 下单参数
    params = {
        'instrument_id': symbol_config[symbol]["instrument_id"],
        'side': trade_side,
    }
    base_currency = symbol.split('-')[0]
    quote_currency = symbol.split('-')[1]
    order_id_list = []
    order_info = {}
    # 按照交易信号下单
    for i in range(max_try_amount):
        try:
            # 确定下单参数
            symbol_info = update_symbol_info(exchange, symbol_info, symbol_config)  # 更新持仓
            print(symbol_info)
            # 交易价格
            params['price'] = str(round(float(cal_order_price(symbol_info.at[symbol, "信号价格"], trade_side)),
                                        symbol_config[symbol]['最小下单价精度']))
            # 交易量
            params['size'] = str(round(abs(trade_vol), symbol_config[symbol]['最小下单量精度']))
            if trade_side == 'buy' and symbol_info.at[symbol, "计价币种持仓量"] < float(params['price']) * float(
                    params['size']):
                msg = '%s计划定投的计价币种%s余额不足支付本次定投，差额%d%s，请及时划转！' % (symbol, quote_currency,
                                                                 float(params['price']) * float(params['size']) -
                                                                 symbol_info.at[symbol, "计价币种持仓量"],
                                                                 quote_currency)
                print(msg)
                send_dingding_msg(msg)
                break
            if trade_side == 'sell' and symbol_info.at[symbol, "交易币种持仓量"] < float(params['size']):
                msg = '%s的本次计划定投为出售%s，但交易币种%s余额已不足以完成本次出售，交易取消！' % (symbol, base_currency, base_currency)
                print(msg)
                send_dingding_msg(msg)
                break
            print('本次定投下单:%s %s %s' % (trade_side, params['size'], base_currency), datetime.now())
            print('开始下单：', datetime.now())
            print('下单参数：', symbol.replace('-', '/'), params['size'], params['price'])
            print('下单方向：', trade_side)
            # 买
            if trade_side == 'buy':
                order_info = exchange.create_limit_buy_order(symbol.replace('-', '/'), params['size'],
                                                             params['price'])  # 买单
            # 卖
            elif trade_side == 'sell':
                order_info = exchange.create_limit_sell_order(symbol.replace('-', '/'), params['size'],
                                                              params['price'])  # 卖单
            else:
                raise ValueError('long_or_short只能是：`买入`或者`卖出`')
            if order_info:
                order_id_list.append(order_info['info']['orderId'])
            break

        except Exception as e:
            print(e)
            print(symbol, '下单失败，稍等后继续尝试')
            time.sleep(short_sleep_time)

            if i == (max_try_amount - 1):
                print('下单失败次数超过max_try_amount，终止下单')
                send_dingding_msg('下单失败次数超过max_try_amount，终止下单，程序不退出')
    return symbol, order_id_list


# 串行下单
def single_threading_place_order(exchange, symbol_info, symbol_config, max_try_amount=5):
    """
    :param exchange:
    :param symbol_info:
    :param symbol_config:
    :param max_try_amount:
    :return:
    串行使用binance_spot_place_order()函数，下单
    """
    # 函数输出变量
    symbol_order = pd.DataFrame()

    # 遍历交易对
    for symbol, row in symbol_info.iterrows():
        trade_vol = row['本次计划交易量']
        trade_account = row['本次计划交易额']
        trade_side = ''

        symbol_config[symbol]['invested_times'] += 1  # 不管是否交易，投资次数+1

        # 交易额大于最小交易额
        if abs(trade_account) > float(min_trade_account):
            if trade_vol > 0:
                trade_side = 'buy'
            elif trade_vol < 0:
                trade_side = 'sell'
        else:
            msg = '%s本次计划定投交易额%f u，小于交易所规定的最小交易额%d u,本次交易计划取消' % (
                symbol, trade_account, min_trade_account)
            print(msg)
            # send_dingding_msg(msg)

        # 下单
        if trade_side != '':
            _, order_id_list = binance_spot_place_order(exchange, symbol_info, symbol_config, trade_side, trade_vol,
                                                        max_try_amount, symbol)

            # 记录
            for order_id in order_id_list:
                symbol_order.loc[order_id, 'symbol'] = symbol
                # 从symbol_info记录下单相关信息
                symbol_order.loc[order_id, '信号价格'] = symbol_info.loc[symbol, '信号价格']

    return symbol_order


# 获取成交数据
def update_order_info(exchange, symbol_config, symbol_order, max_try_amount=5):
    """
    根据订单号，检查订单信息，获得相关数据
    :param exchange:
    :param symbol_config:
    :param symbol_order:
    :param max_try_amount:
    :return:

    """

    # 下单数据不为空
    if symbol_order.empty is False:
        # 这个遍历下单id
        for order_id in symbol_order.index:
            time.sleep(medium_sleep_time)  # 每次获取下单数据时sleep一段时间
            order_info = None
            # 根据下单id获取数据
            for i in range(max_try_amount):
                try:
                    para = {
                        'symbol': symbol_config[symbol_order.at[order_id, 'symbol']]["instrument_id"].replace('-', ''),
                        'orderId': order_id
                    }
                    order_info = exchange.private_get_order(para)
                    break
                except Exception as e:
                    print(e)
                    print('根据订单号获取订单信息失败，稍后重试')
                    time.sleep(medium_sleep_time)
                    if i == max_try_amount - 1:
                        send_dingding_msg("重试次数过多，获取订单信息失败，程序退出")
                        raise ValueError('重试次数过多，获取订单信息失败，程序退出')

            if order_info:
                symbol_order.at[order_id, "订单状态"] = binance_order_state[order_info["status"]]
                if binance_order_state[order_info["status"]] == 'REJECTED' or binance_order_state[
                    order_info["status"]] == 'EXPIRED':
                    print('下单失败')
                symbol_order.at[order_id, "交易方向"] = order_info["side"]
                symbol_order.at[order_id, "委托数量"] = order_info["origQty"]
                symbol_order.at[order_id, "成交数量"] = order_info["executedQty"]
                symbol_order.at[order_id, "委托价格"] = order_info["price"]
                symbol_order.at[order_id, "委托时间"] = time.strftime("%Y-%m-%d %H:%M:%S",
                                                                  time.localtime(int(order_info["time"]) / 1000))
                # symbol_order.at[order_id, "成交均价"] = order_info["price_avg"]
                # symbol_order.at[order_id, "手续费"] = order_info["fee"]
                # symbol_order.at[order_id, "手续费币种"] = order_info["fee_currency"]
            else:
                print('根据订单号获取订单信息失败次数超过max_try_amount，发送钉钉')

    return symbol_order


# =====辅助功能函数
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

    5m  当前时间为：12:34:51  返回时间为：12:40:00

    30m  当前时间为：21日的23:33:51  返回时间为：22日的00:00:00

    30m  当前时间为：14:37:51  返回时间为：14:56:00

    1h  当前时间为：14:37:51  返回时间为：15:00:00

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
    # now_time = datetime(2019, 5, 9, 23, 50, 30)  # 修改now_time，可用于测试
    this_midnight = now_time.replace(hour=0, minute=0, second=0, microsecond=0)
    min_step = timedelta(minutes=1)

    target_time = now_time.replace(second=0, microsecond=0)

    while True:
        target_time = target_time + min_step
        delta = target_time - this_midnight
        if delta.seconds % ti.seconds == 0 and (target_time - now_time).seconds >= ahead_seconds:
            # 当符合运行周期，并且目标时间有足够大的余地，默认为60s
            break

    print('程序下次运行的时间：', target_time, '\n')
    return target_time


# ===获取全部历史数据
def fetch_binance_symbol_history_candle_data(exchange, symbol, time_interval, max_len, max_try_amount=5):
    """
    获取某个币种在binance交易所的历史数据。
    :param exchange:
    :param symbol:
    :param time_interval:
    :param max_len:
    :param max_try_amount:
    :return:
    """

    # 循环获取历史数据
    kline_data = []
    for i in range(max_try_amount):
        try:
            kline_data = exchange.public_get_klines({
                "symbol": str(symbol).replace('-', ''),
                "limit": max_len,
                "interval": time_interval
            })
            break
        except Exception as e:
            print(e)
            time.sleep(medium_sleep_time)
            if i == (max_try_amount - 1):
                _ = '【获取需要交易币种的历史数据】阶段，fetch_binance_symbol_history_candle_data，' \
                    '使用ccxt的public_get_klines获取K线数据失败，程序Raise Error'
                send_dingding_and_raise_error(_)

    # 对数据进行整理
    df = pd.DataFrame(kline_data, dtype=float)
    df.rename(columns={0: 'MTS', 1: 'open', 2: 'high', 3: 'low', 4: 'close', 5: 'volume'}, inplace=True)
    df['candle_begin_time'] = pd.to_datetime(df['MTS'], unit='ms')
    df['candle_begin_time_GMT8'] = df['candle_begin_time'] + timedelta(hours=8)
    df = df[['candle_begin_time_GMT8', 'open', 'high', 'low', 'close', 'volume']]

    # 删除重复的数据
    df.drop_duplicates(subset=['candle_begin_time_GMT8'], keep='last', inplace=True)
    df.reset_index(drop=True, inplace=True)
    df.sort_values(by=['candle_begin_time_GMT8'], inplace=True)
    # 为了保险起见，去掉最后一行最新的数据
    df = df[:-1]
    print(symbol, '获取历史数据行数：', len(df))
    return df


# ===依据时间间隔, 自动计算并休眠到指定时间
def sleep_until_run_time(time_interval, offset_time='0m', ahead_time=5, if_sleep=True, show_time_tips=True):
    """"
    根据next_run_time()函数计算出下次程序运行的时候，然后sleep至该时间
    :param show_time_tips:
    :param offset_time:
    :param if_sleep:
    :param time_interval:
    :param ahead_time:
    :return:
    """
    # 计算下次运行时间
    run_time = next_run_time(time_interval, offset_time, ahead_time, show_time_tips)

    if if_sleep:
        # sleep
        time.sleep(max(0, (run_time - datetime.now()).seconds))
        while True:  # 在靠近目标时间时
            if datetime.now() > run_time:
                break

        return run_time
    else:
        return run_time


# ===下次运行时间
def next_run_time(time_interval, offset_time='0m', ahead_seconds=5, show_time_tips=True):
    """
    根据time_interval，计算下次运行的时间，下一个整点时刻。
    目前只支持分钟和小时。
    :param show_time_tips: 是否提示程序下次运行时间
    :param offset_time: 相对于整点，偏离的分钟数，正整数或负整数均可
    :param time_interval: 运行的周期，15m，1h
    :param ahead_seconds: 预留的目标时间和当前时间的间隙
    :return: 下次运行的时间
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
    offset = pd.to_timedelta(offset_time)
    now_time = datetime.now()
    # now_time = datetime(2021, 8, 28, 10, 39, 30)  # 修改now_time，可用于测试
    # print(now_time)
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

    if show_time_tips:
        print('\n', '程序下次运行的时间：', target_time)

    return target_time


# ===在每个循环的末尾，编写报告并且通过订订发送
def dingding_report_every_loop(symbol_info, symbol_order, run_time, robot_id_secret, symbol_config):
    """
    :param symbol_info:
    :param symbol_signal:
    :param symbol_order:
    :param run_time:
    :param robot_id_secret:
    :return:
    """
    content = ''

    # 订单信息
    symbol_order_str = ['\n\n' + y.to_string() for x, y in symbol_order.iterrows()]  # 持仓信息
    content += '# =====订单信息' + ''.join(symbol_order_str) + '\n\n'

    # 持仓信息
    symbol_info_str = ['\n\n' + str(x) + '\n' + y.to_string() for x, y in symbol_info.iterrows()]
    content += '# =====持仓信息' + ''.join(symbol_info_str) + '\n\n'

    # for symbol in symbol_config.keys():
    #     invested_times = symbol + ' invested_times:' + str(symbol_config[symbol]['invested_times'])
    #     content += '# =====定投次数' + ''.join(invested_times) + '\n'
    #     print('# =====定投次数' + ''.join(invested_times) + '\n')

    # 发送，每间隔30分钟或者有交易的时候，发送一次
    if run_time.minute % 1 == 0:
        # if symbol_order_str:
        send_dingding_msg(content, robot_id=robot_id_secret[0], secret=robot_id_secret[1])


# ===为了达到成交的目的，计算实际委托价格会向上或者向下浮动一定比例默认为0.02
def cal_order_price(price, trade_side, ratio=0.02):
    if trade_side == 'buy':
        return price * (1 + ratio)
    elif trade_side == 'sell':
        return price * (1 - ratio)


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
def send_dingding_msg(content, robot_id=robot_id_secret[0],
                      secret=robot_id_secret[1]):
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


def send_dingding_and_raise_error(content):
    print(content)
    send_dingding_msg(content, robot_id_secret, robot_id_secret)
    raise ValueError(content)


# 获取按照资金分组的币对信息
def get_capital_group_list(symbol_config):
    result = dict()
    for symbol, config in symbol_config.items():
        capital = config['para'][0]
        if capital in result.keys():
            result[capital].append(symbol)
        else:
            result[capital] = [symbol]
    return result


# 获取所有的offsetTime
def order_capital_offset_time(offset_config):
    result = []
    all_offset_time = []
    for offset in offset_config:
        offset_int = int(offset[:-1])
        if offset.endswith('m') and offset_int < 55:
            all_offset_time.append(offset_int)
        else:
            all_offset_time.append(-55)
    all_offset_time.sort()
    for offset_int in all_offset_time:
        result.append(str(offset_int) + 'm')
    return result


# 获取与指定资金相关的交易对
def get_special_capital_symbol_config(symbol_config, capital):
    new_symbol_config = dict()
    for symbol, config in symbol_config.items():
        if int(capital) in config['para']:
            new_symbol_config[symbol] = config
    return new_symbol_config


# 获取资金分组后，首次运行的offset_time,获取距离当前时间点最近的时间
def get_capital_next_offset_time(all_offset, execution_interval):
    latest_offset_time = all_offset[0]
    latest_offset_diff_now_seconds = (sleep_until_run_time(execution_interval, offset_time=all_offset[0], if_sleep=False, show_time_tips=False) - datetime.now()).seconds
    for index in range(0, len(all_offset)):
        run_time = sleep_until_run_time(execution_interval, offset_time=all_offset[index], if_sleep=False, show_time_tips=False)
        current_diff_offset_time = (run_time - datetime.now()).seconds
        if current_diff_offset_time < latest_offset_diff_now_seconds:
            latest_offset_time = all_offset[index]
            latest_offset_diff_now_seconds = current_diff_offset_time
    return latest_offset_time
