import pandas as pd
import time
from binance_cfuture.Config import *
import ccxt
pd.set_option('display.max_rows', 1000)
pd.set_option('expand_frame_repr', False)  # 当列太多时不换行
pd.set_option('display.unicode.ambiguous_as_wide', True)  # 设置命令行输出时的列对齐功能
pd.set_option('display.unicode.east_asian_width', True)
exchange = ccxt.binance(BINANCE_CONFIG_dict['son1'])

while True:
    df = pd.DataFrame(exchange.dapiPrivateGetBalance())
    df['time'] = pd.to_datetime(df['updateTime'], unit='ms')
    print(df.loc[df['asset']=='DOGE'])

    time.sleep(60)