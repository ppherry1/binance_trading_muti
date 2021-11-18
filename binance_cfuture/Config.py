"""
邢不行2021策略分享会
微信：xbx2626
币安币本位择时策略框架
"""
# sleep时间配置
short_sleep_time = 1  # 用于和交易所交互时比较紧急的时间sleep，例如获取数据、下单
medium_sleep_time = 2  # 用于和交易所交互时不是很紧急的时间sleep，例如获取持仓
long_sleep_time = 10  # 用于较长的时间sleep

# timeout时间
exchange_timeout = 3000  # 3s

# 订单对照表
# 根据目标仓位和实际仓位，计算实际操作，"1": "开多"，"2": "开空"，"3": "平多"， "4": "平空"
binance_order_type = {
    '平多': 'SELL',
    '平空': 'BUY',
    '开多': 'BUY',
    '开空': 'SELL',
    '平多，开空': 'SELL',
    '平空，开多': 'BUY',
}

symbol_config_dict = {
    'son1': {
        'symbol_config':
            {
                'DOGEUSD_PERP': {'instrument_id': 'DOGEUSD_PERP',
                                 'instrument_type': 'cfuture',
                                 'leverage': 1.5,
                                 'strategy_name': 'real_signal_none',  # 使用的策略的名称
                                 'para': [100, 1.6],  # 参数
                                 'initial_funds': True,
                                 # 这里填True，则运行时按照下面所设置的initial_usd进行到等值套保状态，如有多余的币会转到现货账户，币不足的话则会购买
                                 # 如果initial_funds写True且仓位大于预设会平掉已开的套保以外的多余仓位；如果小于预设，则会平掉所有仓位重新初始化！
                                 # 相当于一次强制RESTART！所以，如果是非初始化状态运行，这里一定要写False。
                                 # 如果监测到合约账户币种保证金为0，将进行强制初始化
                                 'initial_usd_funds': 40,  # u模式初始投入的资金美元价值initial_usd
                                 '币模式保证金': 10,  # 每次开仓开多少仓位，单位为美金
                                 },
                # 'BNBUSD_PERP': {'leverage': 1.5,
                #                 'strategy_name': 'real_signal_simple_bolling_we',
                #                 'para': [100, 1.7],
                #                 'initial_funds': True,
                #                 'initial_usd_funds': 20,
                #                 '币模式保证金': 10,
                #                 },
            }
    }
}
