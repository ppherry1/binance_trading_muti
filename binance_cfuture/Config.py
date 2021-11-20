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

# 设置初始资金来源相关参数
funding_config = {
    'funding_from_spot': True,  # 从现货中直接提取交易币种作为保证金，这里选True。注意！如果现货不足，则本参数会自动转为False，也就是直接买现货。
    'funding_coin': 'USDT',  # 用于买入现货的交易币种，目前仅能填USD等价币，如USDT，BUSD
    'r_threshold': 0.0007,  # 建仓的最小期现差阈值,可设定为-1，则为忽略阈值，直接建仓
    'execute_amount': 20,  # 每次建仓的美元价值，BTC最小为200，其他币最小为20。
    'fee_use_bnb': True  # 使用BNB支付手续费
}

# ===各个子账户的api配置
# 手工输入每个子账户的api
api_dict = {
    'son1': {
            'apiKey': 'A3sgiz5hLZ2vGn3uYMm43pFzrrkSCsXR2cPTmZ801MG20Bz91Bve8UuxI6iPLPLj',
            'secret': 'OhLkUu99HDKqOhujQEqDvp0Yqi049z5qGe3RqaapGQfWEo91VoR6w5xwd4Tpq2GC',
    },
    'son2': {
        'apiKey': "159f77be-",
        'secret': "",
    },
    'son3': {
        'apiKey': "53dba3e5-",
        'secret': "",
    },
    # 'son4': {
    #     'apiKey': "56739d25-",
    #     'secret': "",
    # },
    # 'son5': {
    #     'apiKey': "670aad81-",
    #     'secret': "",
    # },
    # 'son6': {
    #     'apiKey': "0ecf49a7-",
    #     'secret': "",
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
                                 'strategy_name': 'real_signal_random',  # 使用的策略的名称
                                 'para': [1],  # 参数
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
            },
        'time_interval': '15m'
    }
}
