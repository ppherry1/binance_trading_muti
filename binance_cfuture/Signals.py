
import pandas as pd
import random
import talib as ta


# 将None作为信号返回
def real_signal_none(df, now_pos, avg_price, para):
    """
    发出空交易信号
    :param df:
    :param now_pos:
    :param avg_price:
    :param para:
    :return:
    """

    return None

def real_signal_para(df, now_pos, avg_price, para):
    """
    发出空交易信号
    :param df:
    :param now_pos:
    :param avg_price:
    :param para:
    :return:
    """

    return para[0]


# 随机生成交易信号
def real_signal_random(df, now_pos, avg_price, para):
    """
    随机发出交易信号
    :param df:
    :param now_pos:
    :param avg_price:
    :param para:
    :return:
    """

    r = random.random()
    if r <= 0.2:
        return 1
    elif r <= 0.6:
        return 0
    elif r <= 0.7:
        return -1
    else:
        return None


# 布林策略实盘交易信号
def real_signal_simple_bolling(df, now_pos, avg_price, para=[200, 2]):
    """
    实盘产生布林线策略信号的函数，和历史回测函数相比，计算速度更快。
    布林线中轨：n天收盘价的移动平均线
    布林线上轨：n天收盘价的移动平均线 + m * n天收盘价的标准差
    布林线上轨：n天收盘价的移动平均线 - m * n天收盘价的标准差
    当收盘价由下向上穿过上轨的时候，做多；然后由上向下穿过中轨的时候，平仓。
    当收盘价由上向下穿过下轨的时候，做空；然后由下向上穿过中轨的时候，平仓。
    :param df:  原始数据
    :param para:  参数，[n, m]
    :return:
    """

    # ===策略参数
    # n代表取平均线和标准差的参数
    # m代表标准差的倍数
    n = int(para[0])
    m = para[1]

    # ===计算指标
    # 计算均线
    df['median'] = df['close'].rolling(n).mean()  # 此处只计算最后几行的均线值，因为没有加min_period参数
    median = df.iloc[-1]['median']
    median2 = df.iloc[-2]['median']
    # 计算标准差
    df['std'] = df['close'].rolling(n).std(ddof=0)  # ddof代表标准差自由度，只计算最后几行的均线值，因为没有加min_period参数
    std = df.iloc[-1]['std']
    std2 = df.iloc[-2]['std']
    # 计算上轨、下轨道
    upper = median + m * std
    lower = median - m * std
    upper2 = median2 + m * std2
    lower2 = median2 - m * std2

    # ===寻找交易信号
    signal = None
    close = df.iloc[-1]['close']
    close2 = df.iloc[-2]['close']
    # 找出做多信号
    if (close > upper) and (close2 <= upper2):
        signal = 1
    # 找出做空信号
    elif (close < lower) and (close2 >= lower2):
        signal = -1
    # 找出做多平仓信号
    elif (close < median) and (close2 >= median2):
        signal = 0
    # 找出做空平仓信号
    elif (close > median) and (close2 <= median2):
        signal = 0

    return signal

def real_signal_simple_bolling_we(df, now_pos, avg_price, para=[200, 2]):
    """
    real_signal_simple_bolling_we
    平均差布林+均线回归W+PC平仓+AR过滤
    """

    # ===策略参数
    n = int(para[0])
    m = para[1]
    # 固定参数
    a = 13
    # ===计算指标
    # 计算均线
    df['median'] = ta.LINEARREG(df['close'], timeperiod=a)
    df['median'] = ta.WMA(df['median'], timeperiod=n)
    # 平仓均线
    df['pc'] = ta.TEMA(df['close'], timeperiod=a)
    # ar过滤
    df['arh'] = ta.EMA(df['high'], timeperiod=a) - ta.EMA(df['open'], timeperiod=a)
    df['arl'] = ta.EMA(df['open'], timeperiod=a) - ta.EMA(df['low'], timeperiod=a)
    df['ar'] = df['arh'] / df['arl']
    df['guolv_duo'] = df['ar'] > 0.5
    df['guolv_kong'] = df['ar'] < 0.5
    df['cha'] = abs(df['close'] - df['median'])
    # 计算平均差
    df['ping_jun_cha'] = df['cha'].rolling(n, min_periods=1).mean()
    # 计算上轨、下轨道
    df['upper'] = df['median'] + m * df['ping_jun_cha']
    df['lower'] = df['median'] - m * df['ping_jun_cha']
    # ===计算信号
    # 找出做多信号
    condition1 = df['close'] > df['upper']  # 当前K线的收盘价 > 上轨
    condition2 = df['close'].shift(1) <= df['upper'].shift(1)  # 之前K线的收盘价 <= 上轨
    condition3 = df['pc'] > df['median']
    df.loc[condition1 & condition2 & condition3 & df['guolv_duo'], 'signal_long'] = 1  # 将产生做多信号的那根K线的signal设置为1，1代表做多

    # 找出做多平仓信号
    condition1 = df['pc'] < df['median']  # 当前K线的收盘价 < 中轨
    condition2 = df['pc'].shift(1) >= df['median'].shift(1)  # 之前K线的收盘价 >= 中轨
    df.loc[condition1 & condition2, 'signal_long'] = 0  # 将产生平仓信号当天的signal设置为0，0代表平仓

    # 找出做空信号
    condition1 = df['close'] < df['lower']  # 当前K线的收盘价 < 下轨
    condition2 = df['close'].shift(1) >= df['lower'].shift(1)  # 之前K线的收盘价 >= 下轨
    condition3 = df['pc'] < df['median']
    df.loc[
        condition1 & condition2 & condition3 & df['guolv_kong'], 'signal_short'] = -1  # 将产生做空信号的那根K线的signal设置为-1，-1代表做空

    # 找出做空平仓信号
    condition1 = df['pc'] > df['median']  # 当前K线的收盘价 > 中轨
    condition2 = df['pc'].shift(1) <= df['median'].shift(1)  # 之前K线的收盘价 <= 中轨
    df.loc[condition1 & condition2, 'signal_short'] = 0  # 将产生平仓信号当天的signal设置为0，0代表平仓

    # 合并做多做空信号，去除重复信号
    df['signal'] = df[['signal_long', 'signal_short']].sum(axis=1, min_count=1,
                                                           skipna=True)  # 若你的pandas版本是最新的，请使用本行代码代替上面一行
    temp = df[df['signal'].notnull()][['signal']]
    temp = temp[temp['signal'] != temp['signal'].shift(1)]
    df['signal'] = temp['signal']

    # ===删除无关变量
    # df.drop(['median', 'std', 'upper', 'lower', 'signal_long', 'signal_short'], axis=1, inplace=True)
    df.drop(['signal_long', 'signal_short'], axis=1, inplace=True)

    return df.iloc[-1]['signal']
