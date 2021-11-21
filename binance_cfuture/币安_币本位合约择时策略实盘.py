
import pandas as pd
import ccxt
from binance_cfuture.Config import *
from binance_cfuture.Function import *
import sys
import os

pd.set_option('display.max_rows', 1000)
pd.set_option('expand_frame_repr', False)  # 当列太多时不换行
pd.set_option('display.unicode.ambiguous_as_wide', True)  # 设置命令行输出时的列对齐功能
pd.set_option('display.unicode.east_asian_width', True)
# =====常规config信息
# 获取项目根目录
_ = os.path.abspath(os.path.dirname(__file__))  # 返回当前文件路径
root_path = os.path.abspath(os.path.join(_, '..'))  # 返回根目录文件夹
data_save_dir = os.path.join(root_path, 'data', 'binance_trading_data')

# ===读取程序运行所需的子账号相关参数
if len(sys.argv) > 1:
    account_name = sys.argv[1]
else:
    print('未指定account_name参数，程序exit')
    exit()
print('子账户id：', account_name)

# =获取执行的时间间隔
time_interval = symbol_config_dict[account_name]['time_interval']
time_interval_re = str(int(kline_interval[:-1]) * 60) + 'm' if kline_interval.endswith('h') else kline_interval
exec_interval_re = str(int(time_interval[:-1]) * 60) + 'm' if time_interval.endswith('h') else time_interval
offset_time_re = str(int(offset_time[:-1]) * 60) + 'm' if offset_time.endswith('h') else offset_time
print('执行时间周期：', time_interval, ',底层K线周期：', kline_interval, '每执行周期偏移时间量：', offset_time)

# =从config中读取相关配置信息
exchange = ccxt.binance(BINANCE_CONFIG_dict[account_name])
symbol_config = symbol_config_dict[account_name]['symbol_config']
print('交易信息：', symbol_config)

# =获取交易精度
coin_future_exchange_info(exchange, symbol_config)

def main():
    # =判断是否单向持仓，若不是程序退出。币安的持仓模式介绍。双向持仓、单向持仓
    if_coin_future_oneway_mode(exchange)

    # ==========获取需要交易币种的历史数据==========
    # 获取数据
    # max_candle_num = 5  # 每次获取的K线数量
    # symbol_candle_data = get_binance_coin_future_history_candle_data(exchange, symbol_config, time_interval_re,
    #                                                                  max_candle_num, if_print=True)
    trading_initialization(exchange, funding_config, symbol_config)
    # =进入每次的循环
    while True:
        # ==========获取持仓数据==========
        # 初始化symbol_info，在每次循环开始时都初始化，防止上次循环的内容污染本次循环的内容。
        symbol_info_columns = ['账户币数', '原始币数', '持仓方向_'+mode, '合约张数', '持仓均价', '未实现盈亏']
        symbol_info = pd.DataFrame(index=symbol_config.keys(), columns=symbol_info_columns)

        # 更新账户信息symbol_info
        symbol_info = binance_update_cfuture_account(exchange, symbol_config, symbol_info, mode)
        print('\nsymbol_info:\n', symbol_info, '\n')

        # ==========根据当前时间，获取策略下次执行时间，例如16:15。并sleep至该时间==========
        run_time = sleep_until_run_time(exec_interval_re, if_sleep=False, offset_time=offset_time_re)
        # ==========获取最新的k线数据==========

        symbol_candle_data = {}
        for symbol in symbol_config.keys():
            p = os.path.join(data_save_dir,
                             'data_ready_%s_%s_%s' % (symbol, time_interval, str(run_time).replace(':', '-')))
            print('获取数据地址：', p)
            while True:
                if os.path.exists(p):
                    print('数据已经存在：', datetime.now())
                    break
                if datetime.now() > run_time + timedelta(minutes=1):
                    print('时间超过1分钟，放弃从文件读取数据，返回空数据')
                    break
            symbol_candle_data[symbol] = pd.read_csv(os.path.join(data_save_dir, '%s_%s.csv' % (symbol, time_interval)))
            symbol_info.loc[symbol, '当前价格'] = symbol_candle_data[symbol].iloc[-1]['close']  # 该品种的最新价格
            print(symbol_candle_data[symbol].tail(5))

        # 将symbol_candle_data和最新获取的recent_candle_data数据合并
        # symbol_candle_data = symbol_candle_data_append_recent_candle_data(symbol_candle_data, recent_candle_data,
        #                                                                   symbol_config, max_candle_num)

        # ==========计算每个币种的交易信号==========
        symbol_signal = calculate_signal(symbol_info, symbol_config, symbol_candle_data, mode)
        print('\n产生信号时间:\n', symbol_info[['持仓方向_'+mode, '目标持仓', '信号', '信号时间']])
        print('\n本周期交易计划:', symbol_signal)

        # ==========下单==========
        exchange.timeout = exchange_timeout  # 下单时需要增加timeout的时间，将timout恢复正常
        # 计算下单信息
        symbol_order_params = cal_all_order_info(symbol_signal, symbol_info, symbol_config, exchange, mode)
        print('\n订单参数\n', symbol_order_params)

        # 开始批量下单
        order_info_list = place_binance_cfuture_batch_order(exchange, symbol_order_params)
        if len(order_info_list) == 0:
            symbol_order = pd.DataFrame()
        else:
            symbol_order = pd.concat(order_info_list)

        # ==========检测是否需要adl==========
        time.sleep(medium_sleep_time)
        if deal_adl:
            deal_with_binance_adl(exchange, symbol_info, symbol_config)
        # 更新账户信息symbol_info
        symbol_info = pd.DataFrame(index=symbol_config.keys(), columns=symbol_info_columns)
        symbol_info = binance_update_cfuture_account(exchange, symbol_config, symbol_info, mode)
        print('\nsymbol_info:\n', symbol_info, '\n')

        # 发送钉钉
        dingding_report_every_loop(symbol_info, symbol_signal, symbol_order, run_time, robot_id_secret)

        # 本次循环结束
        print('\n', '-' * 20, '本次循环结束，%f秒后进入下一次循环' % long_sleep_time, '-' * 20, '\n\n')
        time.sleep(long_sleep_time)


if __name__ == '__main__':
    while True:
        # try:
            main()
        # except Exception as err:
        #     print('系统出错，10s之后重新运行，出错原因：' + str(err))
        #     time.sleep(long_sleep_time)
