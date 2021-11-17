"""
币安网格策略实盘
"""
import ccxt
from time import sleep
import pandas as pd
from datetime import datetime
from binance_infnet.Function import *
from binance_infnet.Config import *

pd.set_option('display.max_rows', 1000)
pd.set_option('expand_frame_repr', False)  # 当列太多时不换行
# 设置命令行输出时的列对齐功能
pd.set_option('display.unicode.ambiguous_as_wide', True)
pd.set_option('display.unicode.east_asian_width', True)

account_name = [key for key in api_dict.keys()][0]

# =交易所配置
BINANCE_CONFIG = BINANCE_CONFIG_dict[account_name]
exchange = ccxt.binance(BINANCE_CONFIG)

# 更新需要交易的合约、策略参数、下单量等配置信息
symbol_config = symbol_config_dict[account_name]['symbol_config']
# 获取所有交易币对的精度
get_spot_exchange_Info(exchange, symbol_config)
print(symbol_config)
offset_time = offset_time

def main():
    global offset_time
    if is_use_capital_group:
        symbol_group_by_capital = get_capital_group_list(symbol_config)
        print('资金分组情况：', symbol_group_by_capital)
        all_offset_list = order_capital_offset_time(capital_offset_time)
        # 获取距离当前时间最近的运行时间
        offset_time = get_capital_next_offset_time(all_offset_list, execution_interval)
    # =====获取需要交易币种的历史数据=====
    symbol_candle_data = dict()  # 用于存储K线数据
    # 遍历获取币种历史数据
    for symbol in symbol_config.keys():
        # 获取币种的历史数据，会删除最新一行的数据
        symbol_candle_data[symbol] = fetch_binance_symbol_history_candle_data(exchange,
                                                                              symbol_config[symbol]['instrument_id'],
                                                                              time_interval, max_len=max_len)
        time.sleep(medium_sleep_time)

    # ===进入每次的循环
    while True:
        # 记录本次循环交易的币对信息
        current_symbol_config = symbol_config
        if is_use_capital_group:
            # 计算当前需要交易的币对
            # 计算当前offset对应的金额信息
            current_trade_capital = capital_offset_time[offset_time]
            print('当前分组金额:', current_trade_capital)
            # 根据金额过滤出本次需要交易的币对
            current_symbol_config = get_special_capital_symbol_config(symbol_config, current_trade_capital)
            print('按照资金分组，当前需要交易的币对信息:', current_symbol_config)
        # =获取持仓数据
        # 初始化symbol_info，在每次循环开始时都初始化
        symbol_info_columns = ['计价币种持仓量', '交易币种持仓量']
        symbol_info = pd.DataFrame(index=current_symbol_config.keys(), columns=symbol_info_columns)  # 转化为dataframe

        # 更新账户信息symbol_info
        symbol_info = update_symbol_info(exchange, symbol_info, current_symbol_config)
        print('\nsymbol_info:\n', symbol_info, '\n')

        # =获取策略执行时间，并sleep至该时间
        run_time = sleep_until_run_time(execution_interval, offset_time=offset_time)

        # =并行获取所有币种最近数据
        exchange.timeout = 1000  # 即将获取最新数据，临时将timeout设置为1s，加快获取数据速度
        candle_num = int(int(execution_interval[:-1]) / int(time_interval[:-1])) + 10  # 获取从上次运行开始未获取的K线
        # 获取数据
        recent_candle_data = single_threading_get_data(exchange, symbol_info, current_symbol_config, time_interval,
                                                       run_time,
                                                       candle_num)
        for symbol in current_symbol_config.keys():
            print(symbol + '最新k线数据：')
            print(recent_candle_data[symbol].tail(2))

        # 将symbol_candle_data和最新获取的recent_candle_data数据合并
        for symbol in current_symbol_config.keys():
            df = symbol_candle_data[symbol].append(recent_candle_data[symbol], ignore_index=True)
            df.drop_duplicates(subset=['candle_begin_time_GMT8'], keep='last', inplace=True)
            df.sort_values(by='candle_begin_time_GMT8', inplace=True)  # 排序，理论上这步应该可以省略，加快速度
            df = df.iloc[-max_len:]  # 保持最大K线数量不会超过max_len个
            df.reset_index(drop=True, inplace=True)
            symbol_candle_data[symbol] = df
        # =计算每个币种的交易信号
        symbol_info = calculate_trade_vol(symbol_info, current_symbol_config, symbol_candle_data)
        print('\n现货持仓与本次定投计划:\n', symbol_info)
        # =下单
        exchange.timeout = exchange_timeout  # 下单时需要增加timeout的时间，将timout恢复正常

        symbol_order = single_threading_place_order(exchange, symbol_info, current_symbol_config)  # 单线程下单
        print('下单记录：\n', symbol_order)

        # 更新订单信息，查看是否完全成交
        time.sleep(short_sleep_time)  # 休息一段时间再更新订单信息
        symbol_order = update_order_info(exchange, current_symbol_config, symbol_order)
        print('更新下单记录：', '\n', symbol_order)

        # 重新更新账户信息symbol_info，获取最新的交易币对持仓信息
        time.sleep(long_sleep_time)  # 休息一段时间再更新
        symbol_info = pd.DataFrame(index=symbol_config.keys(), columns=symbol_info_columns)
        symbol_info = update_symbol_info(exchange, symbol_info, symbol_config)
        print('\nsymbol_info:\n', symbol_info, '\n')

        # 开启了资金分组，获取下一次的offset
        if is_use_capital_group:
            current_offset_time_index = all_offset_list.index(offset_time)
            if current_offset_time_index + 1 < len(all_offset_list):
                offset_time = all_offset_list[current_offset_time_index + 1]
            else:
                offset_time = all_offset_list[0]
        # 发送钉钉
        dingding_report_every_loop(symbol_info, symbol_order, run_time, robot_id_secret, symbol_config)

        # 本次循环结束
        print('\n', '-' * 20, '本次循环结束，%f秒后进入下一次循环' % long_sleep_time, '-' * 20, '\n\n')
        time.sleep(long_sleep_time)


if __name__ == '__main__':
    while True:
        try:
            main()
        except Exception as e:
            send_dingding_msg('系统出错，10s之后重新运行，出错原因：' + str(e))
            print(e)
            sleep(long_sleep_time)
