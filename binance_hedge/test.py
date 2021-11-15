import pandas as pd
import ccxt

pd.set_option('display.max_rows', 1000)
pd.set_option('expand_frame_repr', False)  # 当列太多时不换行
pd.set_option('display.unicode.ambiguous_as_wide', True)  # 设置命令行输出时的列对齐功能
pd.set_option('display.unicode.east_asian_width', True)
BINANCE_CONFIG = {
    'apiKey': 'abQuFm1dhtdgtLfaATADkE4Dmss8s0q5pzUVycIndBphvpNo7ANdVz9rdVVH9P6o',
    'secret': 'fmW4cRLsV1sYzY50aOaF9Utk5wbTFTW7QZIwS850HSOaWzF56dYzG15YMWyoxzZR',
    'rateLimit': 10,
    'verbose': False,
    'hostname': 'fapi.binance.com',
    'enableRateLimit': False}
exchange = ccxt.binance(BINANCE_CONFIG)


df = pd.DataFrame(exchange.fapiPublicGetHistoricalTrades({'symbol': 'BTCUSDT'}))

# # ============币安U本位FACE_VALUE==========
# df = pd.DataFrame(exchange.fapiPublicGetExchangeInfo()['symbols'])
# symbol_list = df['symbol'].tolist()
# info_list = []
# for symbol in symbol_list:
#     info_dict = dict()
#     info_dict['symbol'] = symbol
#     for item in df.loc[df['symbol'] == symbol]['filters'].values[0]:
#         if item['filterType'] == 'LOT_SIZE':
#             info_dict['minQty'] = float(item['minQty'])
#             info_dict['stepSize'] = float(item['stepSize'])
#         info_list.append(info_dict)
# df_info = pd.DataFrame(info_list)
# df_info.drop_duplicates(inplace=True)
# print(df_info)
# # ============币安U本位FACE_VALUE==========
