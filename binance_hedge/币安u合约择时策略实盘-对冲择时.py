"""
《邢不行-2020新版|Python数字货币量化投资课程》
无需编程基础，助教答疑服务，专属策略网站，一旦加入，永续更新。
课程详细介绍：https://quantclass.cn/crypto/class
邢不行微信: xbx9025
本程序作者: 邢不行

# 课程内容
币安u本位择时策略实盘框架
"""
import pandas as pd
import ccxt
from program.Function import *
from program.Config import *
import json5

pd.set_option('display.max_rows', 1000)
pd.set_option('expand_frame_repr', False)  # 当列太多时不换行
pd.set_option('display.unicode.ambiguous_as_wide', True)  # 设置命令行输出时的列对齐功能
pd.set_option('display.unicode.east_asian_width', True)


# ==========配置运行相关参数==========
# 底层k线粒度
time_interval = '1m'  # 目前支持m（分钟），h（小时）为单位。得交易所支持的K线才行。
# k线周期(每个周期用来计算信号K线的周期，以及多久运行一次)
exec_interval = '1h'  # 目前支持m（分钟），h（小时）为单位。必须是time_interval的正整数倍，且换算为分钟必须能整除1440，或被1440整除。
# 以下是所有exec_interval的可取值
# 1m, 2m, 3m, 4m, 5m, 6m, 8m, 10m, 12m, 15m, 16m, 18m, 20m, 24m, 30m, 32m, 36m, 40m, 45m, 48m, 1h,
# 72m, 80m, 90m, 96m, 2h, 144m, 160m, 3h, 4h, 6h, 12h, 24h以及24h的整数倍。
# k线偏移的时间
offset_time = '-1m'  # 目前支持m（分钟），h（小时）为单位。必须是time_interval的整数倍。负数为提前执行，正数为延后执行。
# 每个周期用来计算信号K线的条数，建议至少是策略窗口参数的两倍
period_candle_num = 800

# 统一转化为m方便后续计算
if time_interval.endswith('h'):
    time_interval = str(int(time_interval[:-1]) * 60) + 'm'
if exec_interval.endswith('h'):
    exec_interval = str(int(exec_interval[:-1]) * 60) + 'm'
if offset_time.endswith('h'):
    offset_time = str(int(offset_time[:-1]) * 60) + 'm'

# =交易所配置
BINANCE_CONFIG = {
    'apiKey': 'flVn0RcPr4m4hrJ8fZHXEMJHDb7XDGEhvhqS48eOXYkQ1nMXHAZoo5LTK3fP7v5U',
    'secret': 'RoyBB2Uq4QCOvi4sFVlXboM5e5jpN2yWirCXaFMnbWE0W8wT1eGWmX1d3Wl7XhgK',
    'timeout': exchange_timeout,
    'rateLimit': 10,
    'verbose': False,
    'hostname': 'fapi.binance.com',
    'enableRateLimit': False}
exchange = ccxt.binance(BINANCE_CONFIG)  # 交易所api

# ==========配置策略相关参数==========
# =symbol_config，更新需要交易的合约、策略参数、下单量等配置信息。主键为u本位合约的symbol。比特币永续为BTCUSDT，交割为BTCUSDT_210625


def main():
    # =判断是否单向持仓，若不是程序退出
    if_oneway_mode(exchange)
    symbol_config_ori = json5.load(open('strategy_config'))['symbol_config']
    strategy_config_ori = json5.load(open('strategy_config'))['strategy_config']
    # usdt_future_exchange_info(exchange, symbol_config_ori)
    is_first = True
    # =进入每次的循环
    while True:
        symbol_config = json5.load(open('strategy_config'))['symbol_config']
        strategy_config = json5.load(open('strategy_config'))['strategy_config']
        print('symbol_config:', symbol_config)
        print('strategy_config:', strategy_config)
        if is_first or (symbol_config.keys() != symbol_config_ori.keys()) or (strategy_config != strategy_config_ori):
            if is_first:
                print('初次运行，获取K线')
            else:
                print('检测到参数变化，重新获取K线')
                print('symbol_config:', symbol_config)
                print('strategy_config:', strategy_config)
            is_first = False
            symbol_config_ori = symbol_config
            strategy_config_ori = strategy_config
            # ==========获取需要交易币种的历史数据==========
            # 获取K线数据
            max_candle_num = int(int(exec_interval[:-1]) / int(time_interval[:-1]) * period_candle_num)  # 每次获取的K线数量
            symbol_candle_data = get_binance_candle_data(exchange, symbol_config, time_interval, max_candle_num)
            # 用币对的K线，构造模拟K线
            symbol_candle_data = construct_strategy_symbol_candle(symbol_config, strategy_config, symbol_candle_data)
            # 模拟K线resample
            strategy_candle_data = binance_resample_candle_data(symbol_candle_data, exec_interval, offset_time, drop=-1)
            for strategy in strategy_config.keys():
                print('构造策略%s的模拟K线' % strategy)
                print(strategy_candle_data[strategy].tail())

        for symbol in symbol_config.keys():
            for strategy in strategy_config.keys():
                if strategy == symbol_config[symbol]['strategy_number']:
                    symbol_config[symbol]['position'] = float(strategy_config[strategy]['position']) / 2
                    symbol_config[symbol]['leverage'] = strategy_config[strategy]['leverage']

        usdt_future_exchange_info(exchange, symbol_config)

        # ==========获取持仓数据==========
        # 初始化symbol_info，在每次循环开始时都初始化，防止上次循环的内容污染本次循环的内容。
        symbol_info_columns = ['账户权益', '分配比例', '分配资金', '持仓方向', '持仓量', '持仓收益', '持仓均价', '当前价格']
        symbol_info = pd.DataFrame(index=symbol_config.keys(), columns=symbol_info_columns)  # 转化为dataframe
        symbol_info['分配比例'] = pd.DataFrame(symbol_config).T['position']

        # 更新账户信息symbol_info
        symbol_info = binance_update_account(exchange, symbol_config, symbol_info)
        print('持仓信息\n', symbol_info)
        time.sleep(medium_sleep_time)

        # 初始化symbol_info，在每次循环开始时都初始化，防止上次循环的内容污染本次循环的内容。
        strategy_info_columns = ['策略币种', '分配比例', '持仓方向s', '持仓方向', '持仓量s', '持仓均价s', '持仓均价', '持仓收益s', '持仓收益']
        strategy_info = pd.DataFrame(index=strategy_config.keys(), columns=strategy_info_columns)  # 转化为dataframe
        strategy_info['分配比例'] = pd.DataFrame(strategy_config).T['position']

        # 更新账户信息symbol_info
        strategy_info = binance_update_account_strategy(exchange, strategy_config, strategy_info, symbol_config)
        print('持仓信息\n', strategy_info)

        # ==========根据当前时间，获取策略下次执行时间，例如16:15。并sleep至该时间==========
        run_time = sleep_until_run_time(exec_interval, offset_time=offset_time)

        # ==========获取最新的k线数据==========
        exchange.timeout = 1000  # 即将获取最新数据，临时将timeout设置为1s，加快获取数据速度
        # 获取数据
        recent_candle_num = int(int(exec_interval[:-1]) / int(time_interval[:-1]) * 5)
        recent_candle_data = get_binance_candle_data(exchange, symbol_config, time_interval, recent_candle_num,
                                                     False, symbol_info, run_time)
        recent_candle_data = construct_strategy_symbol_candle(symbol_config, strategy_config, recent_candle_data)
        # 模拟K线resample
        recent_candle_data = binance_resample_candle_data(recent_candle_data, exec_interval, offset_time)
        # 将最近的数据打印出
        for symbol in strategy_config.keys():
            print(recent_candle_data[symbol].tail(min(2, recent_candle_num)))

        # 将strategy_candle_data和最新获取的recent_candle_data数据合并
        strategy_candle_data = symbol_candle_data_append_recent_candle_data(strategy_candle_data, recent_candle_data,
                                                                            strategy_config, period_candle_num)

        # ==========计算每个币种的交易信号==========
        strategy_signal = calculate_strategy_signal(strategy_info, strategy_config, strategy_candle_data)
        print('\n策略信号时间:\n', strategy_info)
        print('\n本周期交易计划:', strategy_signal)
        symbol_signal = calculate_symbol_signal(strategy_signal, strategy_info)
        print('\n分解各币种信号:\n', symbol_info)
        print('\n本周期交易计划:', symbol_signal)

        # ==========下单==========
        exchange.timeout = exchange_timeout  # 下单时需要增加timeout的时间，将timout恢复正常
        # 计算下单信息
        symbol_order_params = cal_all_order_info(symbol_signal, symbol_info, symbol_config, exchange)
        print('\n订单参数\n', symbol_order_params)

        # 开始批量下单
        place_binance_batch_order(exchange, symbol_order_params)

        # 本次循环结束
        print('\n', '-' * 40, '本次循环结束，%d秒后进入下一次循环' % long_sleep_time, '-' * 40, '\n\n')
        time.sleep(long_sleep_time)


if __name__ == '__main__':
    while True:
        # try:
            main()
        # except Exception as e:
        #     print('系统出错，10s之后重新运行，出错原因：' + str(e))
        #     time.sleep(long_sleep_time)
