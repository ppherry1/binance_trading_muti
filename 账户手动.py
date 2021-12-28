from trading_class.account import *

# apikey
account_info = {
        'apiKey': "ezbgmN8MI7IwgySDLjFCzVFJcdthxwZSyjPyRjhAjfr0543DqJrO2UTfwZrK9VHo",
          'secret': "LJVJdBz37lvwasDsF6DxnmL5T2u4131Uy9ErckIvOXNYlBzOBx7id90wuuezHiuG",
}
customer = Account(account_info)

# 通用参数'ins_type': 'cfuture'为币本位合约,'ufuture'为U本位合约,'spot'为现货。
# ===============================查询命令===============================================

# # 查询所有币种持仓信息（合约）
# res = customer.get_future_positions({
#     'ins_type': 'cfuture'  # 必填参数'cfuture'币本位,'ufuture'U本位
# })

# # 查询所有币种持仓风险信息（合约）
# res = customer.get_positionRisk({
#     'ins_type': 'cfuture'  # 必填参数'cfuture'币本位,'ufuture'U本位
# })

# # 查询所有币种保证金信息（合约）
# res = customer.get_future_assets({
#     'ins_type': 'cfuture'  # 必填参数'cfuture'币本位,'ufuture'U本位
# })

# # 查询所有币种余额信息（现货）
# res = customer.get_spot_account({
#     'ins_type': 'spot'  # 必填参数'spot'现货
# })

# # 查询指定币种（或合约名称）成交信息
# # 不填开始结束日期的话，则默认显示最近的100条成交记录，最多显示100条
# res = customer.get_userTrades({
#     'ins_type': 'cfuture',  # 必填参数'spot'现货,'cfuture'币本位,'ufuture'U本位
#     'symbol': 'DOTUSD_PERP',  # 币种或合约名称，必填参数，例如'BTCUSDT','BTCUSD_PERP'
#     # 'startTime': '2020-1-1',  # 开始时间，选填参数，例如'2020-1-1'
#     # 'endTime': '2021-11-1',  # 结束时间，选填参数，例如'2020-1-1'
# })

# # 查询指定合约历史强平单
# # 不填开始结束日期的话，则默认显示最近的100条强平记录，最多显示100条
# res = customer.get_forceOrders({
#     'ins_type': 'cfuture',  # 必填参数,'cfuture'币本位,'ufuture'U本位
#     'symbol': 'BTCUSD_PERP',  # 币种或合约名称，必填参数，例如'BTCUSDT','BTCUSD_PERP'
#     # 'startTime': '2020-1-1',  # 开始时间，选填参数，例如'2020-1-1'
#     # 'endTime': '2021-11-1',  # 结束时间，选填参数，例如'2020-1-1'
#     'autoCloseType': 'ADL',  # 强平类型，选填参数，'LIQUIDATION'为爆仓，'ADL'为自动减仓
# })

# =================================挂单和下单======================================

# # 查询指定币种或合约历史挂单记录
# # 不填开始结束日期的话，则默认显示最近的100条强平记录，最多显示100条
# res = customer.get_allOrders({
#     'ins_type': 'cfuture',  # 必填参数'spot'现货,'cfuture'币本位,'ufuture'U本位
#     'symbol': 'BTCUSD_PERP',  # 币种或合约名称，必填参数，例如'BTCUSDT','BTCUSD_PERP'
#     # 'startTime': '2020-1-1',  # 开始时间，选填参数，例如'2020-1-1'
#     # 'endTime': '2021-11-1',  # 结束时间，选填参数，例如'2020-1-1'
# })

# # 查询指定币种或所有币种当前挂单
# # 不填symbol的话，则显示当前所有挂单
# res = customer.get_openOrders({
#     'ins_type': 'cfuture',  # 必填参数'spot'现货,'cfuture'币本位,'ufuture'U本位
#     # 'symbol': 'BTCUSD_PERP',  # 币种或合约名称，选填参数，例如'BTCUSDT','BTCUSD_PERP'
# })

# # 撤销指定币种或所有币种当前挂单
# # 不填symbol的话，则撤销当前所有挂单
# res = customer.delete_allOpenOrders({
#     'ins_type': 'cfuture',  # 必填参数'spot'现货,'cfuture'币本位,'ufuture'U本位
#     'symbol': 'BTCUSD_PERP',  # 币种或合约名称，必填参数，例如'BTCUSDT','BTCUSD_PERP'
# })

# 下单from datetime import datetime,timedelta
# 合约使用的话，则持仓方式必须为单项持仓模式
res = customer.post_order({
    'ins_type': 'cfuture',  # 必填参数'spot'现货,'cfuture'币本位,'ufuture'U本位
    'symbol': 'ETHUSD_PERP',  # 币种或合约名称，必填参数，例如'BTCUSDT','BTCUSD_PERP'
    'side': 'BUY',  # 下单方向，必填参数，'BUY'为买或做多或平空，'SELL'为卖或做空或平多
    'order_type': 'MARKET',  # 下单方式，必填参数，'LIMIT'限价单, 'MARKET'市价单
    # 'price': 20000,  # 委托价格，限价单必填，市价单不能填
    'quantity': 8,  # 购买币数(现货/U本位)或张数(币本位)，合约必填，现货本参数和下面参数'quoteOrderQty'能且仅能填一个
    # 例如我要买0.0001个BTC，使用ETHUSDT币对，则这里填0.0001
    # 'quoteOrderQty': 60,  # 购买所使用的计价币币数，合约不能填，现货本参数和上面参数'quantity'能且仅能填一个
    # 例如我要买60美元的BTC，使用ETHUSDT币对，则这里填60
})



