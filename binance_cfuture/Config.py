
# ==========配置运行相关参数==========
# =交易模式设置
mode = 'u模式'  # u模式，币模式
deal_adl = False  # 是否执行ADL检查重置

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

# 设置初始资金来源相关参数
funding_config = {
    'funding_from_spot': True,  # 从现货中直接提取交易币种作为保证金，这里选True。注意！如果现货不足，则本参数会自动转为False，也就是直接买现货。
    'funding_coin': 'USDT',  # 用于买入现货的交易币种，目前仅能填USD等价币，如USDT，BUSD
    'r_threshold': 0.0007,  # 建仓的最小期现差阈值,可设定为-1，则为忽略阈值，直接建仓
    'execute_amount': 30,  # 每次建仓的美元价值，BTC最小为200，其他币最小为20。
    'fee_use_bnb': True  # 使用BNB支付手续费
}

# =钉钉
# 在一个钉钉群中，可以创建多个钉钉机器人。
# 建议单独建立一个报错机器人，该机器人专门发报错信息。请务必将报错机器人在id和secret放到function.send_dingding_msg的默认参数中。
# 当我们运行多策略时，会运行多个python程序，建议不同的程序使用不同的钉钉机器人发送相关消息。每个程序的开始部分加上该机器人的id和secret
robot_id = '3316400a3627a7520d01371322510fbf9f4fe5c7bf5420c40b987ce44e990fe6'
secret = 'SECf8a88997fa4e3ced30d5b02dd38b06d1e949f47d1b66233630350c2fa9623b04'
robot_id_secret = [robot_id, secret]

# ===各个子账户的api配置
# 手工输入每个子账户的api
api_dict = {
    'main': {
            'apiKey': 'flVn0RcPr4m4hrJ8fZHXEMJHDb7XDGEhvhqS48eOXYkQ1nMXHAZoo5LTK3fP7v5U',
            'secret': 'RoyBB2Uq4QCOvi4sFVlXboM5e5jpN2yWirCXaFMnbWE0W8wT1eGWmX1d3Wl7XhgK',
    },
     'son2': {
        'email': 'ppherry2_virtual@rw2vcdbsnoemail.com',
        'apiKey': "mYpuRg1IsYCBO52k9KMvLHEx7hUQcMpMKrLyrXuILPsVAP7ZKaNkDTWXIaiTuLMU",
        'secret': "u89HSIXXEx3BbItro2RJFBuXI4ZZ5zmYxM36HGINWuD3ZP4ayy8y7uXFEMSfbOvM",
    },
    'son3': {
        'email': 'ppherry3_virtual@91z0byq6noemail.com',
        'apiKey': "uYWLRAPf8iXYDGfOzm5wR6w35uvn6PQWONzxZpe46FUDKLCQrZo3C5lK7HqchyIQ",
        'secret': "fDVklkFaCL36TR1ryjpaR4jZanDfbVwRpW545QUdFJvD1BIXrIPbGpKsABq0mhDa",
    },
    'son1': {
        'email': 'ppherry1_virtual@7gctieg8noemail.com',
        'apiKey': "BKBKpOGOqE3SQiqEsXnM1nbEdhexO58PkcjviD0m1ocgvImMmUSdp2QNtCQb2vsj",
        'secret': "VWHqTsYqkB9XkhOMy3064MyWWK9CgYT9ZlkmLHm54TFvCwO2nIllTly0HdXih02C",
    },
    'son5': {
        'email': 'ppherry5_virtual@jt9n2acvnoemail.com',
        'apiKey': "DS2xZ14YdEVLkNUTkMcEpWdimbQsr7Ra4brNpyant5Y6iTpS9HKwPXhl6ry6m8i1",
        'secret': "0qZGXK4vmMA8bLm5mgTh17mdavIpZuMfHGt84rYY5uUOxMGVIEQUxTfkSU41IoYn",
    },
    # 'son1': {
    #     'apiKey': "gXFbysjyuIahklw2Dx1suxvW7pHpp5BROITj4Tq2TtqKCejGkeXGNGvEf70IzT94",
    #     'secret': "4cudAWwweEoQvWkkq8HXnODpYz12B9RdzNE34KiA6PE1XTpqiu1XwqDhuniQrKP3",
    # },
    # 'son7': {
    #     'apiKey': "b0c088ee-",
    #     'secret': "",
    # },
    # 'son8': {
    #     'apiKey': "2f7e6278-",
    #     'secret': "",
    # },
}

# 形成exchange_config
BINANCE_CONFIG_dict = {}
HOST_NAME = 'fapi.binance.com'
for account_name in api_dict.keys():
    BINANCE_CONFIG_dict[account_name] = {
        'timeout': exchange_timeout,
        'rateLimit': 10,
        'verbose': False,
        'hostname': HOST_NAME,  # 无法fq的时候启用
        'enableRateLimit': False}
    BINANCE_CONFIG_dict[account_name]['apiKey'] = api_dict[account_name]['apiKey']
    BINANCE_CONFIG_dict[account_name]['secret'] = api_dict[account_name]['secret']

symbol_config_dict = {
    'son1': {
        'symbol_config':
            {
                'DOGEUSD_PERP': {'instrument_id': 'DOGEUSD_PERP',
                                 'instrument_type': 'spot',  # 使用K线的类型，现货'spot', 币本位合约'cfuture', u本位'ufuture'
                                  # 这里合约也可以填spot，即用现货K线模拟合约K线，如果参数需求K线数大于70，建议填spot
                                 'leverage': 1,
                                 'strategy_name': 'real_signal_none',  # 使用的策略的名称
                                 'para': [1],  # 参数
                                 'initial_funds': True,
                                 # 这里填True，则运行时按照下面所设置的initial_usd进行到等值套保状态，如有多余的币会转到现货账户，币不足的话则会购买
                                 # 如果initial_funds写True且仓位大于预设会平掉已开的套保以外的多余仓位；如果小于预设，则会平掉所有仓位重新初始化！
                                 # 相当于一次强制RESTART！所以，如果是非初始化状态运行，这里一定要写False。
                                 # 如果监测到合约账户币种保证金为0，将进行强制初始化
                                 'initial_usd_funds': 60,  # u模式初始投入的资金美元价值initial_usd
                                 '币模式保证金': 10,  # 每次开仓开多少仓位，单位为美金
                                 },
                # 'BNBUSD_PERP': {'leverage': 1.5,
                #                 'strategy_name': 'real_signal_simple_bolling_we',
                #                 'para': [100, 1.7],
                #                 'initial_funds': True,
                #                 'initial_usd_funds': 20,
                #                 '币模式保证金': 10,
                #                 },
            },
        'time_interval': '15m'  # 脚本运行周期，即多久跑执行一次策略
    },
'son2': {
        'symbol_config':
            {
                'BNBUSD_PERP': {'instrument_id': 'BNBUSD_PERP',
                                 'instrument_type': 'spot',  # 使用K线的类型，现货'spot', 币本位合约'cfuture', u本位'ufuture'
                                  # 这里合约也可以填spot，即用现货K线模拟合约K线，如果参数需求K线数大于70，建议填spot
                                 'leverage': 1,
                                 'strategy_name': 'real_signal_simple_bolling_we',  # 使用的策略的名称
                                 'para': [200, 2],  # 参数
                                 'initial_funds': False,
                                 # 这里填True，则运行时按照下面所设置的initial_usd进行到等值套保状态，如有多余的币会转到现货账户，币不足的话则会购买
                                 # 如果initial_funds写True且仓位大于预设会平掉已开的套保以外的多余仓位；如果小于预设，则会平掉所有仓位重新初始化！
                                 # 相当于一次强制RESTART！所以，如果是非初始化状态运行，这里一定要写False。
                                 # 如果监测到合约账户币种保证金为0，将进行强制初始化
                                 'initial_usd_funds': 20,  # u模式初始投入的资金美元价值initial_usd,至少为20
                                 '币模式保证金': 10,  # 每次开仓开多少仓位，单位为美金
                                 },
                'UNIUSD_PERP': {'instrument_id': 'UNIUSD_PERP',
                                'instrument_type': 'spot',  # 使用K线的类型，现货'spot', 币本位合约'cfuture', u本位'ufuture'
                                # ，即用现货K线模拟合约K线，如果参数需求K线数大于70，建议填spot
                                'leverage': 1,
                                'strategy_name': 'real_signal_simple_bolling_we',  # 使用的策略的名称
                                'para': [200, 2],  # 参数
                                'initial_funds': False,
                                # 这里填True，则运行时按照下面所设置的initial_usd进行到等值套保状态，如有多余的币会转到现货账户，币不足的话则会购买
                                # 如果initial_funds写True且仓位大于预设会平掉已开的套保以外的多余仓位；如果小于预设，则会平掉所有仓位重新初始化！
                                # 相当于一次强制RESTART！所以，如果是非初始化状态运行，这里一定要写False。
                                # 如果监测到合约账户币种保证金为0，将进行强制初始化
                                'initial_usd_funds': 30,  # u模式初始投入的资金美元价值initial_usd,至少为20
                                '币模式保证金': 10,  # 每次开仓开多少仓位，单位为美金
                                },
            },
        'time_interval': '1h'  # 脚本运行周期，即多久跑执行一次策略
    },
'son3': {
        'symbol_config':
            {
                'MANAUSD_PERP': {'instrument_id': 'MANAUSD_PERP',
                                 'instrument_type': 'spot',  # 使用K线的类型，现货'spot', 币本位合约'cfuture', u本位'ufuture'
                                  # 这里合约也可以填spot，即用现货K线模拟合约K线，如果参数需求K线数大于70，建议填spot
                                 'leverage': 1,
                                 'strategy_name': 'real_signal_none',  # 使用的策略的名称
                                 'para': [20],  # 参数
                                 'initial_funds': False,
                                 # 这里填True，则运行时按照下面所设置的initial_usd进行到等值套保状态，如有多余的币会转到现货账户，币不足的话则会购买
                                 # 如果initial_funds写True且仓位大于预设会平掉已开的套保以外的多余仓位；如果小于预设，则会平掉所有仓位重新初始化！
                                 # 相当于一次强制RESTART！所以，如果是非初始化状态运行，这里一定要写False。
                                 # 如果监测到合约账户币种保证金为0，将进行强制初始化
                                 'initial_usd_funds': 20,  # u模式初始投入的资金美元价值initial_usd,至少为20
                                 '币模式保证金': 10,  # 每次开仓开多少仓位，单位为美金
                                 },
                'BNBUSD_PERP': {'instrument_id': 'BNBUSD_PERP',
                                 'instrument_type': 'spot',  # 使用K线的类型，现货'spot', 币本位合约'cfuture', u本位'ufuture'
                                  # 这里合约也可以填spot，即用现货K线模拟合约K线，如果参数需求K线数大于70，建议填spot
                                 'leverage': 1,
                                 'strategy_name': 'real_signal_para',  # 使用的策略的名称
                                 'para': [1],  # 参数
                                 'initial_funds': False,
                                 # 这里填True，则运行时按照下面所设置的initial_usd进行到等值套保状态，如有多余的币会转到现货账户，币不足的话则会购买
                                 # 如果initial_funds写True且仓位大于预设会平掉已开的套保以外的多余仓位；如果小于预设，则会平掉所有仓位重新初始化！
                                 # 相当于一次强制RESTART！所以，如果是非初始化状态运行，这里一定要写False。
                                 # 如果监测到合约账户币种保证金为0，将进行强制初始化
                                 'initial_usd_funds': 20,  # u模式初始投入的资金美元价值initial_usd,至少为20
                                 '币模式保证金': 10,  # 每次开仓开多少仓位，单位为美金
                                 },

            },

        'time_interval': '15m'  # 脚本运行周期，即多久跑执行一次策略
    },
    'son12': {
        'symbol_config':
            {
                'BNBUSD_PERP': {'instrument_id': 'BNBUSD_PERP',
                                 'instrument_type': 'spot',  # 使用K线的类型，现货'spot', 币本位合约'cfuture', u本位'ufuture'
                                 # 这里合约也可以填spot，即用现货K线模拟合约K线，如果参数需求K线数大于70，建议填spot
                                 'leverage': 1,
                                 'strategy_name': 'real_signal_none',  # 使用的策略的名称
                                 'para': [20],  # 参数
                                 'initial_funds': True,
                                 # 这里填True，则运行时按照下面所设置的initial_usd进行到等值套保状态，如有多余的币会转到现货账户，币不足的话则会购买
                                 # 如果initial_funds写True且仓位大于预设会平掉已开的套保以外的多余仓位；如果小于预设，则会平掉所有仓位重新初始化！
                                 # 相当于一次强制RESTART！所以，如果是非初始化状态运行，这里一定要写False。
                                 # 如果监测到合约账户币种保证金为0，将进行强制初始化
                                 'initial_usd_funds': 20,  # u模式初始投入的资金美元价值initial_usd,至少为20
                                 '币模式保证金': 10,  # 每次开仓开多少仓位，单位为美金
                                 },

            },

        'time_interval': '15m'  # 脚本运行周期，即多久跑执行一次策略
    },
}

# =底层k线周期
kline_interval = '5m'  # 目前支持5m，15m，30m，1h，2h等。得交易所支持的K线才行。最好不要低于5m

# k线偏移的时间
offset_time = '-5m'  # 目前支持m（分钟），h（小时）为单位。必须是time_interval的整数倍。负数为提前执行，正数为延后执行。


# 设置初始资金来源相关参数
funding_config = {
    'spot_from_main_acc': True,  # 是否从母账户划转保证金币
    'funding_coin': 'USDT',  # 若现货不足，用于买入现货的交易币种，目前仅能填USD等价币，如USDT，BUSD
    'funding_coin_from_main_acc': False,  # 是否从母账户划转计价币
    'surplus_spot_deal': 'TO_MAIN',  # 建仓剩余现货处理方式,'SAVE'为保留在子账户现货账户，'TO_MAIN'为划转到母账户现货账户
}

