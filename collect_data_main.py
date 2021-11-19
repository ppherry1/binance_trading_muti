"""
邢不行2020策略分享会
0607OKEx合约择时策略【多账户】实盘交易框架，版本1.0
邢不行微信：xbx9025
"""
import ccxt
from time import sleep
import os
import pandas as pd
from datetime import datetime
import glob
import binance_cfuture.Config as cfuture
import binance_infnet.Config as infnet
pd.set_option('display.max_rows', 1000)
pd.set_option('expand_frame_repr', False)  # 当列太多时不换行
# 设置命令行输出时的列对齐功能
pd.set_option('display.unicode.ambiguous_as_wide', True)
pd.set_option('display.unicode.east_asian_width', True)
import os
from collect_data_function import *
from collect_data_config import *


# =====常规config信息
# 获取项目根目录
_ = os.path.abspath(os.path.dirname(__file__))  # 返回当前文件路径
root_path = os.path.abspath(os.path.join(_, '.'))  # 返回根目录文件夹
data_save_dir = os.path.join(root_path, 'data', 'binance_trading_data')

"""
程序思路：
1. 整体思路仍然和原来的单账户程序相同，都是通过while True来让程序按照固定时间间隔运行。

2. 使用要获取数据周期中，最小的周期，作为每次循环的时间间隔。
例如共要获取['5m', '15m', '30m', '1h', '2h']周期的数据，那就以5m作为每次循环的时间间隔

3. 每个循环只收集最小周期的数据，其他数据使用最小周期数据resample合成。加快运行速度
例如共要获取['5m', '15m', '30m', '1h', '2h']周期的数据，但只会向okex请求5min数据，其余数据用5分钟数据合成。
"""


# =====从config中读取配置信息
# =需要抓取数据的时间周期
# 在config.py中，请把最小的时间周期放在最前面。保证time_interval_list从小到到排序、min_time_interval是最小时间周期
# time_interval_list = []
# for account_name in symbol_config_dict.keys():
#     time_interval = symbol_config_dict[account_name]['time_interval']
#     if time_interval not in time_interval_list:
#         time_interval_list.append(time_interval)
deal_type = ['infnet', 'cfuture']
time_interval_list = ['5m', '15m', '30m', '1h', '2h']
offset_time = '-5m'
min_time_interval = time_interval_list[0]
candle_num = 30  # 每次获取K线的数量。必须保证candle_num的数量足够大，可以保证min_time_interval可以resample出最大的时间周期
print('需要抓取的时间周期：', time_interval_list)
print('最小的时间周期是：', min_time_interval)  # 其他时间周期必须是最小时间周期的整数倍。

offset_time_re = offset_time.replace('m', 'T') if 'm' in offset_time else str(int(offset_time[:-1]) * 60) + 'T'
agg_dict = {
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum',
                'quote_volume': 'sum',
                'num': 'sum',
                'initiative_vol': 'sum',
                'initiative_quote_vol': 'sum'

            }

# =需要抓取的币种
symbol_config = {}
for strategy_type in deal_type:
    for account_name in eval(strategy_type).symbol_config_dict.keys():
        for symbol in eval(strategy_type).symbol_config_dict[account_name]['symbol_config']:
            symbol_config[symbol] = {
                'instrument_id': eval(strategy_type).symbol_config_dict[account_name]['symbol_config'][symbol]['instrument_id'],
                'instrument_type': eval(strategy_type).symbol_config_dict[account_name]['symbol_config'][symbol]['instrument_type'] if 'instrument_type' in eval(strategy_type).symbol_config_dict[account_name]['symbol_config'][symbol].keys() else 'ufuture'
            }
print('需要抓取的币种：', symbol_config)
# symbol_config更适合list，将symbol_config做成dict，只是为了和之前的程序兼容

# =====其他配置信息
# =exchange
BINANCE_CONFIG = {
    # 不需要api，给了api反而会受到limit限制
    'timeout': 1000,  # timeout时间短一点
    'rateLimit': 10,
    'hostname': 'fapi.binance.com',  # 无法fq的时候启用
    'enableRateLimit': False
}
exchange = ccxt.binance(BINANCE_CONFIG)

# =设定最多收集多少根K线，okex_v3不能超过1440根
max_len = 500


def main():

    # ===获取需要交易币种的历史数据。单账户程序：数据存到symbol_candle_data，多账户程序：数据存到本地csv文件
    # 遍历获取币种历史数据

    for symbol in symbol_config.keys():
        print('抓取历史数据：', symbol_config[symbol]['instrument_id'], min_time_interval)
        # 获取币种的历史数据，会删除最新一行的数据
        df = fetch_binance_symbol_history_candle_data(exchange, symbol_config[symbol]['instrument_type'], symbol_config[symbol]['instrument_id'], min_time_interval, max_len=max_len)
        # 存储数据到本地
        df.to_csv(os.path.join(data_save_dir, '%s_%s.csv' % (symbol, min_time_interval)), index=False)
        time.sleep(medium_sleep_time)  # 短暂的sleep
        df_copy = df.copy()
        for interval in time_interval_list[1:]:
            interval_re = interval.replace('m', 'T') if 'm' in interval else str(int(interval[:-1]) * 60) + 'T'
            df_tmp = df_copy.resample(rule=interval_re, offset=offset_time_re, on='candle_begin_time_GMT8', closed='left', label='left').agg(agg_dict).reset_index()
            df_tmp.to_csv(os.path.join(data_save_dir, '%s_%s.csv' % (symbol, interval)), index=False)
    # for time_interval in time_interval_list:


    # ===进入每次的循环，注意：每次循环的时间是min_time_interval
    while True:

        # =获取策略执行时间，并sleep至该时间
        # 获取run_time
        run_time = next_run_time(min_time_interval, ahead_seconds=1)
        # 计算本周期需要保存的数据周期。在sleep之前计算是为了节省后面的时间
        need_save_list = cal_need_save_time_interval_this_run_time(run_time, time_interval_list, offset_time_re)
        # sleep
        time.sleep(max(0, (run_time - datetime.now()).seconds))
        while True:  # 在靠近目标时间时
            if datetime.now() > run_time:
                break

        # =获取所有币种最近数据
        # 串行获取数据，和单账户程序相比，只是去除了symbol_info
        recent_candle_data = single_threading_get_data(exchange, symbol_config, min_time_interval, run_time, candle_num)
        for symbol in symbol_config.keys():
            print('\n', recent_candle_data[symbol].tail(2))

        # runtime 16：15

        # =转换数据周期，并且存储数据
        # 遍历所有需要转换的周期
        for time_interval in need_save_list:
            # 遍历所有需要转换的币种
            for symbol in symbol_config.keys():
                print('开始转换数据周期，并且存储：', time_interval, symbol,)
                df = recent_candle_data[symbol]

                if time_interval != min_time_interval:  # 需要转换的数据周期：不等于最小时间周期
                    if time_interval.endswith('m'):
                        rule = time_interval.replace('m', 'T')
                    else:
                        rule = time_interval
                    # 转化周期
                    df = recent_candle_data[symbol].resample(rule=rule, offset=offset_time_re, on='candle_begin_time_GMT8').agg(agg_dict)
                    # 保存最后一行数据，保留index
                    df.iloc[-1:, :].to_csv(os.path.join(data_save_dir, '%s_%s.csv' % (symbol, time_interval)), mode='a', header=None)
                else:  # 不需要转换的数据周期：等于最小时间周期
                    # 保存数据，不需要index
                    df.iloc[-1:, :].to_csv(os.path.join(data_save_dir, '%s_%s.csv' % (symbol, time_interval)), mode='a', index=False, header=None)

                # 输出data_ready
                t = datetime.now()
                pd.DataFrame(columns=[t]).to_csv(os.path.join(data_save_dir, 'data_ready_%s_%s_%s' % (symbol, time_interval, str(run_time).replace(':', '-'))), index=False)
                print('存储完数据时间：', t)

        # =每隔一段时间，重新获取一次历史数据：每奇数小时，重新获取一次历史数据。如此做目的有2：
        # 1.不让随着时间的推移，历史数据过长，导致读取数据速度变慢。
        # 2.万一计算过程中数据不对，可以及时从服务器修正
        if run_time.hour % 2 == 1 and run_time.minute == 0:
            print('sleep 3min后，开始重新抓取历史数据...')
            time.sleep(3*60)
            # 遍历获取币种历史数据
            for symbol in symbol_config.keys():
                print('抓取历史数据：', symbol_config[symbol]['instrument_id'], min_time_interval)
                # 获取币种的历史数据，会删除最新一行的数据
                df = fetch_binance_symbol_history_candle_data(exchange, symbol_config[symbol]['instrument_type'],
                                                              symbol_config[symbol]['instrument_id'], min_time_interval,
                                                              max_len=max_len)
                # 存储数据到本地
                df.to_csv(os.path.join(data_save_dir, '%s_%s.csv' % (symbol, min_time_interval)), index=False)
                time.sleep(medium_sleep_time)  # 短暂的sleep
                df_copy = df.copy()
                for interval in time_interval_list[1:]:
                    interval_re = interval.replace('m', 'T') if 'm' in interval else str(int(interval[:-1]) * 60) + 'T'
                    df_tmp = df_copy.resample(rule=interval_re, offset=offset_time_re, on='candle_begin_time_GMT8',
                                              closed='left', label='left').agg(agg_dict).reset_index()
                    df_tmp.to_csv(os.path.join(data_save_dir, '%s_%s.csv' % (symbol, interval)), index=False)
                time.sleep(medium_sleep_time)  # 短暂的sleep

        # =每隔一段时间，清除一下之前的data_ready文件：每周二的9点，删除所有data_ready文件
        if run_time.weekday() == 2 and run_time.hour == 9 and run_time.minute == 0:
            print('sleep 1min后，开始删除data_ready文件...')
            time.sleep(60)
            file_list = glob.glob(data_save_dir + '/*')  # python自带的库，或者某文件夹中所有文件的路径
            file_list = list(filter(lambda x: 'data_ready_' in x, file_list))
            for file in file_list:
                os.remove(file)

        # =本次循环结束
        print('\n', '-' * 20, '本次循环结束，%f秒后进入下一次循环' % long_sleep_time, '-' * 20, '\n\n')
        time.sleep(long_sleep_time)


if __name__ == '__main__':
    while True:
        # try:
            main()
        # except Exception as e:
        #     send_dingding_msg('系统出错，10s之后重新运行，出错原因：' + str(e))
        #     print(e)
        #     sleep(long_sleep_time)

