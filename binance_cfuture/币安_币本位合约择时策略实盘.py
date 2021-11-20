"""
邢不行2021策略分享会
微信：xbx2626
币安币本位择时策略框架
"""
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

# ==========配置运行相关参数==========
# =交易模式设置
mode = 'u模式'  # u模式，币模式
deal_adl = False  #

# ===读取程序运行所需的子账号相关参数
if len(sys.argv) > 1:
    account_name = sys.argv[1]
else:
    print('未指定account_name参数，程序exit')
    exit()
print('子账户id：', account_name)

# ===配置运行相关参数
# =从config中读取相关配置信息
exchange = ccxt.binance(BINANCE_CONFIG_dict[account_name])
symbol_config = symbol_config_dict[account_name]['symbol_config']
print('交易信息：', symbol_config)
# =执行的时间间隔
exec_interval = symbol_config_dict[account_name]['time_interval']

# =k线周期
time_interval = '5m'  # 目前支持5m，15m，30m，1h，2h等。得交易所支持的K线才行。最好不要低于5m

# exec_interval = '1h'  # 目前支持m（分钟），h（小时）为单位。必须是time_interval的正整数倍，且换算为分钟必须能整除1440，或被1440整除。
# 以下是所有exec_interval的可取值
# 1m, 2m, 3m, 4m, 5m, 6m, 8m, 10m, 12m, 15m, 16m, 18m, 20m, 24m, 30m, 32m, 36m, 40m, 45m, 48m, 1h,
# 72m, 80m, 90m, 96m, 2h, 144m, 160m, 3h, 4h, 6h, 12h, 24h以及24h的整数倍。
# k线偏移的时间
offset_time = '-5m'  # 目前支持m（分钟），h（小时）为单位。必须是time_interval的整数倍。负数为提前执行，正数为延后执行。
# 每个周期用来计算信号K线的条数，建议至少是策略窗口参数的两倍

time_interval_re = str(int(time_interval[:-1]) * 60) + 'm' if time_interval.endswith('h') else time_interval
exec_interval_re = str(int(exec_interval[:-1]) * 60) + 'm' if exec_interval.endswith('h') else exec_interval
offset_time_re = str(int(offset_time[:-1]) * 60) + 'm' if offset_time.endswith('h') else offset_time

print('执行时间周期：', exec_interval, ',底层K线周期：', time_interval, '每执行周期偏移时间量：', offset_time)


# 设置初始资金来源相关参数
funding_config = {
    'funding_from_spot': True,  # 从现货中直接提取交易币种作为保证金，这里选True。注意！如果现货不足，则本参数会自动转为False，也就是直接买现货。
    'funding_coin': 'USDT',  # 用于买入现货的交易币种，目前仅能填USD等价币，如USDT，BUSD
    'r_threshold': 0.0007,  # 建仓的最小期现差阈值,可设定为-1，则为忽略阈值，直接建仓
    'execute_amount': 20,  # 每次建仓的美元价值，BTC最小为200，其他币最小为20。
    'fee_use_bnb': True  # 使用BNB支付手续费
}

# =获取交易精度
coin_future_exchange_info(exchange, symbol_config)
# {'DOGEUSD_PERP': {'leverage': 1.5, 'strategy_name': 'real_signal_random', 'para': [200, 2], 'face_value': 10,
#                   '币模式保证金': 10, '最小下单价精度': 6}}


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
                             'data_ready_%s_%s_%s' % (symbol, exec_interval, str(run_time).replace(':', '-')))
            print('获取数据地址：', p)
            while True:
                if os.path.exists(p):
                    print('数据已经存在：', datetime.now())
                    break
                if datetime.now() > run_time + timedelta(minutes=1):
                    print('时间超过1分钟，放弃从文件读取数据，返回空数据')
                    break
            symbol_candle_data[symbol] = pd.read_csv(os.path.join(data_save_dir, '%s_%s.csv' % (symbol, exec_interval)))
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
        place_binance_cfuture_batch_order(exchange, symbol_order_params)

        # ==========检测是否需要adl==========
        time.sleep(medium_sleep_time)
        if deal_adl:
            deal_with_binance_adl(exchange, symbol_info, symbol_config)

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
