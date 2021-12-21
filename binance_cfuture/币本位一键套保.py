from trading.account import *
from binance_cfuture.Config import *

hedging_acc = ['son2']  # 设置需要套保的账户
estimate_method = '四舍五入'  # 这里可以填'向下取整'（实际偏向多头）， '向上取整'（实际偏向空头）， '四舍五入'

for acc in hedging_acc:
    account = Account(api_dict[acc])
    print('开始调整币本位账户%s,调整前保证金情况：' % acc)
    c_assets = account.get_future_assets(params={'ins_type': 'cfuture'})
    print('调整前持仓情况：')
    c_positions = account.get_positionRisk(params={'ins_type': 'cfuture'})
    print('-----------------------------------------------------------------------------------------------')
    if c_assets:
        for asset in c_assets:
            print('开始处理%s...' % asset['资产'])
            face_value = 100 if asset['资产'] == 'BTC' else 10
            book_ticker = account.get_tickerBookTicker(params={'ins_type': 'spot', 'symbol': asset['资产'] + 'USDT'})
            print('book_ticker:')
            print(book_ticker)
            asset_value = float(asset['保证金余额']) * float(book_ticker[0]['bidPrice'])
            print('%s保证金美元价值：%f' % (asset['资产'], asset_value))
            expect_amt = 0
            if estimate_method == '四舍五入':
                expect_amt = -round(asset_value / face_value)
            elif estimate_method == '向下取整':
                expect_amt = -int(asset_value / face_value)
            elif estimate_method == '向上取整':
                expect_amt = -(int(asset_value / face_value) + 1)
            print('%s算法，期望持仓%s张' % (estimate_method, str(expect_amt)))
            actual_amt = 0
            if c_positions:
                for item in c_positions:
                    if item['交易对'] == asset['资产'] + 'USD_PERP':
                        actual_amt = float(item['持仓数量'])
            print('实际持仓%s张，计划交易张数：%s' % (str(actual_amt), str(expect_amt - actual_amt)))
            side = 'BUY' if expect_amt - actual_amt > 0 else 'SELL'
            trade_amt = int(abs(expect_amt - actual_amt))
            if trade_amt != 0:
                print('准备下单%s，方向：%s，交易张数%d' % (asset['资产'] + 'USD_PERP', side, trade_amt))
                info = account.post_order(params={
                    'ins_type': 'cfuture',  # 必填参数'spot'现货,'cfuture'币本位,'ufuture'U本位
                    'symbol': asset['资产'] + 'USD_PERP',  # 币种或合约名称，必填参数，例如'BTCUSDT','BTCUSD_PERP'
                    'side': side,  # 下单方向，必填参数，'BUY'为买或做多或平空，'SELL'为卖或做空或平多
                    'order_type': 'MARKET',  # 下单方式，必填参数，'LIMIT'限价单, 'MARKET'市价单
                    # 'price': 20000,  # 委托价格，限价单必填，市价单不能填
                    'quantity': trade_amt,  # 购买币数(现货/U本位)或张数(币本位)，合约必填，现货本参数和下面参数'quoteOrderQty'能且仅能填一个
                    # 例如我要买0.0001个BTC，使用ETHUSDT币对，则这里填0.0001
                    # 'quoteOrderQty': 60,  # 购买所使用的计价币币数，合约不能填，现货本参数和上面参数'quantity'能且仅能填一个
                    # 例如我要买60美元的BTC，使用ETHUSDT币对，则这里填60
                })
                print('下单完成，交易信息：')
                print(info)
            else:
                print('已处于套保状态，无需调整！')
            print('-----------------------------------------------------------------------------------------------')
    else:
        print('账户%s没有币本位保证金，不进行调整' % acc)

    print('账户%s套保调整完毕' % acc)

    pd.DataFrame(account.get_positionRisk(params={'ins_type': 'cfuture'}))
    print('===============================================================================================')