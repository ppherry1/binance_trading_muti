from trading.account import *
from binance_cfuture.Config import *
import time

hedging_acc = ['son3', 'son2', 'son5', 'son12']  # 设置需要清仓的账户
main_acc = 'main'
estimate_method = '四舍五入'  # 这里可以填'向下取整'（实际偏向多头）， '向上取整'（实际偏向空头）， '四舍五入'
main_account = Account(api_dict[main_acc])
transfer_log_dict = dict()

for acc in hedging_acc:
    account = Account(api_dict[acc])
    # print('开始调整币本位账户%s,调整前保证金情况：' % acc)
    # c_assets = accont.get_future_assets(params={'ins_type': 'cfuture'})
    print('clear持仓情况：')
    c_positions = account.get_positionRisk(params={'ins_type': 'cfuture'})
    print('-----------------------------------------------------------------------------------------------')
    if c_positions:
        for position in c_positions:
            print('开始处理%s...' % position['交易对'])
            book_ticker = account.get_tickerBookTicker(params={'ins_type': 'cfuture', 'symbol': position['交易对']})
            pricePrecision = account.get_exchangeInfo(params={'ins_type': 'cfuture'}).set_index('symbol').at[position['交易对'], 'pricePrecision']
            side = 'BUY' if float(position['持仓数量']) < 0 else 'SELL'
            price = float(book_ticker[0]['askPrice']) * 1.02 if float(position['持仓数量']) < 0 else float(book_ticker[0]['bidPrice']) * 0.98
            price = round(price, int(pricePrecision))
            trade_amt = abs(int(position['持仓数量']))
            print('准备下单%s，方向：%s，交易张数%d' % (position['交易对'], side, trade_amt))
            info = account.post_order(params={
                'ins_type': 'cfuture',  # 必填参数'spot'现货,'cfuture'币本位,'ufuture'U本位
                'symbol': position['交易对'],  # 币种或合约名称，必填参数，例如'BTCUSDT','BTCUSD_PERP'
                'side': side,  # 下单方向，必填参数，'BUY'为买或做多或平空，'SELL'为卖或做空或平多
                'order_type': 'LIMIT',  # 下单方式，必填参数，'LIMIT'限价单, 'MARKET'市价单
                'price': price,  # 委托价格，限价单必填，市价单不能填
                'quantity': trade_amt,  # 购买币数(现货/U本位)或张数(币本位)，合约必填，现货本参数和下面参数'quoteOrderQty'能且仅能填一个
            })
            print('下单完成，交易信息：')
            print(info)
            print('-----------------------------------------------------------------------------------------------')
    else:
        print('账户%s没有币本位持仓，不进行调整' % acc)
    c_positions = account.get_positionRisk(params={'ins_type': 'cfuture'})
    time.sleep(3)
    print('开始调整币本位账户%s保证金,调整前保证金情况：' % acc)
    c_assets = account.get_future_assets(params={'ins_type': 'cfuture'})
    transfer_log_dict[acc] = dict()
    if c_assets:
        for asset in c_assets:
            print('开始处理%s...' % asset['资产'])
            transfer_amount = float(asset['最大可提款金额'])
            # account.post_assetTransfer({'asset': asset['资产'], 'type': 'CMFUTURE_MAIN', 'amount': transfer_amount})
            main_account.post_subAccountUniversalTransfer({
                'fromEmail': account.email,
                'asset': asset['资产'],
                'amount': transfer_amount,
                'fromAccountType': 'COIN_FUTURE'
            })
            if asset['资产'] not in transfer_log_dict[acc].keys():
                transfer_log_dict[acc][asset['资产']] = transfer_amount
            else:
                transfer_log_dict[acc][asset['资产']] += transfer_amount
    c_assets = account.get_future_assets(params={'ins_type': 'cfuture'})
    time.sleep(3)
    print('开始调整现货账户%s,调整前现货账情况：' % acc)
    spot_assets = account.get_spot_account({'ins_type': 'spot'})
    for asset in spot_assets:
        print('开始处理%s...' % asset['资产'])
        main_account.post_subAccountUniversalTransfer({
            'fromEmail': account.email,
            'asset': asset['资产'],
            'amount': float(asset['可用币数'])
        })
        if asset['资产'] not in transfer_log_dict[acc].keys():
            transfer_log_dict[acc][asset['资产']] = float(asset['可用币数'])
        else:
            transfer_log_dict[acc][asset['资产']] += float(asset['可用币数'])
    print('整现货账户%s,调整前现货账情况：' % acc)
    spot_assets = account.get_spot_account({'ins_type': 'spot'})

    print('账户%s调整完毕' % acc)
    print('===============================================================================================')

print('划转母账户明细:\n')
print(transfer_log_dict)
