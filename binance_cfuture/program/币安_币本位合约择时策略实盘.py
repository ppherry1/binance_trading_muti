"""
邢不行2021策略分享会
微信：xbx2626
币安币本位择时策略框架
"""
import pandas as pd
import ccxt
from binance_cfuture.program.Function import *
from binance_cfuture.program.Config import *
pd.set_option('display.max_rows', 1000)
pd.set_option('expand_frame_repr', False)  # 当列太多时不换行
pd.set_option('display.unicode.ambiguous_as_wide', True)  # 设置命令行输出时的列对齐功能
pd.set_option('display.unicode.east_asian_width', True)


# ==========配置运行相关参数==========
# =交易模式设置
mode = 'u模式'  # u模式，币模式

# =k线周期
time_interval = '5m'  # 目前支持5m，15m，30m，1h，2h等。得交易所支持的K线才行。最好不要低于5m

# 设置初始资金来源相关参数
funding_config = {
    'funding_from_spot': True,  # 从现货中直接提取交易币种作为保证金，这里选True。注意！如果现货不足，则本参数会自动转为False，也就是直接买现货。
    'funding_coin': 'USDT',  # 用于买入现货的交易币种，目前仅能填USD等价币，如USDT，BUSD
    'r_threshold': 0.01,  # 建仓的最小期现差阈值,可设定为-1，则为忽略阈值，直接建仓
    'execute_amount': 10,  # 每次建仓的美元价值，BTC最小为100，其他币最小为10。
    'fee_use_bnb': True  # 使用BNB支付手续费
}


# =交易所配置
BINANCE_CONFIG = {
    'apiKey': 'A3sgiz5hLZ2vGn3uYMm43pFzrrkSCsXR2cPTmZ801MG20Bz91Bve8UuxI6iPLPLj',
    'secret': 'OhLkUu99HDKqOhujQEqDvp0Yqi049z5qGe3RqaapGQfWEo91VoR6w5xwd4Tpq2GC',
    'timeout': exchange_timeout,
    'rateLimit': 10,
    'verbose': False,
    'hostname': 'fapi.binance.com',
    'enableRateLimit': False}
exchange = ccxt.binance(BINANCE_CONFIG)  # 交易所api

# ==========配置策略相关参数==========
# =symbol_config，更新需要交易的合约、策略参数、下单量等配置信息。
# 本程序同时适用币本位的永续合约、交割合约。在symbol_config中设置不同的symbol即可，例如比特币永续为BTCUSD_PERP，交割为BTCUSD_210625。
# 往每个币种的账户里面放不同的钱，就代表了每个币种的仓位
symbol_config = {
    'DOGEUSD_PERP': {'leverage': 1.5,
                     'strategy_name': 'real_signal_simple_bolling_we',  # 使用的策略的名称
                     'para': [100, 1.6],  # 参数
                     'initial_funds': True,  # 这里填True，则运行时按照下面所设置的initial_usd进行到等值套保状态，如有多余的币会转到现货账户，币不足的话则会购买
                     # 如果initial_funds写True且仓位大于预设会平掉已开的套保以外的多余仓位；如果小于预设，则会平掉所有仓位重新初始化！
                     # 相当于一次强制RESTART！所以，如果是非初始化状态运行，这里一定要写False。
                     # 如果监测合约账户未开仓，将强制初始化
                     'initial_usd': 20,  # u模式初始投入的资金美元价值initial_usd
                     '币模式保证金': 10,  # 每次开仓开多少仓位，单位为美金
                     },
    'BNBUSD_PERP': {'leverage': 1.5,
                    'strategy_name': 'real_signal_simple_bolling_we',
                    'para': [100, 1.7],
                    'initial_funds': True,
                    'initial_usd_funds': 20,
                    '币模式保证金': 10,
                    },
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
    max_candle_num = 5  # 每次获取的K线数量
    symbol_candle_data = get_binance_coin_future_history_candle_data(exchange, symbol_config, time_interval,
                                                                     max_candle_num, if_print=True)
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
        run_time = sleep_until_run_time(time_interval, if_sleep=False)

        # ==========获取最新的k线数据==========
        exchange.timeout = 1000  # 即将获取最新数据，临时将timeout设置为1s，加快获取数据速度
        # 获取数据
        recent_candle_num = 5
        recent_candle_data = single_thread_get_binance_coin_future_candle_data(exchange, symbol_config, symbol_info,
                                                                               time_interval, run_time,
                                                                               recent_candle_num)
        # 将最近的数据打印出
        for symbol in symbol_config.keys():
            print(recent_candle_data[symbol].tail(min(2, recent_candle_num)))

        # 将symbol_candle_data和最新获取的recent_candle_data数据合并
        symbol_candle_data = symbol_candle_data_append_recent_candle_data(symbol_candle_data, recent_candle_data,
                                                                          symbol_config, max_candle_num)

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
        # place_binance_cfuture_batch_order(exchange, symbol_order_params)

        # ==========检测是否需要adl==========
        time.sleep(medium_sleep_time)
        deal_with_binance_adl(exchange, symbol_info, symbol_config)

        # 本次循环结束
        print('\n', '-' * 20, '本次循环结束，%f秒后进入下一次循环' % long_sleep_time, '-' * 20, '\n\n')
        time.sleep(long_sleep_time)


if __name__ == '__main__':
    while True:
        try:
            main()
        except Exception as err:
            print('系统出错，10s之后重新运行，出错原因：' + str(err))
            time.sleep(long_sleep_time)
