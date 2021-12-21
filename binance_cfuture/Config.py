
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
robot_secret = 'SECf8a88997fa4e3ced30d5b02dd38b06d1e949f47d1b66233630350c2fa9623b04'
robot_id_secret = [robot_id, robot_secret]

# ===各个子账户的api配置
# 手工输入每个子账户的api
api_dict = {
    'main': {
            'apiKey': 'ZcVo562JplzdaRRuTbS8PK760r7hGouocKXFi1MjZ56SslMMBqPcPgTFbjvT8Uvi',
            'secret': '6bi9D9Z8rlQUQmjhdw2iv1Mbm9CdXJA1PPuksyZOysQchKL346arHDfs042TemZr',
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
        'apiKey': "A3sgiz5hLZ2vGn3uYMm43pFzrrkSCsXR2cPTmZ801MG20Bz91Bve8UuxI6iPLPLj",
        'secret': "OhLkUu99HDKqOhujQEqDvp0Yqi049z5qGe3RqaapGQfWEo91VoR6w5xwd4Tpq2GC",
    },
    'son5': {
        'email': 'ppherry5_virtual@jt9n2acvnoemail.com',
        'apiKey': "DS2xZ14YdEVLkNUTkMcEpWdimbQsr7Ra4brNpyant5Y6iTpS9HKwPXhl6ry6m8i1",
        'secret': "0qZGXK4vmMA8bLm5mgTh17mdavIpZuMfHGt84rYY5uUOxMGVIEQUxTfkSU41IoYn",
    },
    'son4': {
        'email': 'ppherry4_virtual@3qh68epqnoemail.com',
        'apiKey': "DT00t10taGyGwvTKEEmfIxRmUzsrXzlcJLDypFGukl4NUAZxZalWCnHgwOiHg706",
        'secret': "OXLmFhHtq9Af5wgSe3KCOCSgnPD4wivCMJZVBGGhqKVJFE7cyEBqHmxmMSfyeYnk",
    },
    'son10': {
          'email': 'ppherry10_virtual@528scv45noemail.com',
          'apiKey': "ezbgmN8MI7IwgySDLjFCzVFJcdthxwZSyjPyRjhAjfr0543DqJrO2UTfwZrK9VHo",
          'secret': "LJVJdBz37lvwasDsF6DxnmL5T2u4131Uy9ErckIvOXNYlBzOBx7id90wuuezHiuG",
    },
    'son15': {
          'email': 'ppherry15_virtual@5qd20a15noemail.com',
          'apiKey': "n2YjIMUKVgFc1RKU6E5Jx6Y8hDLjb0tbkKCfMyuPuiwGR0kmmMmKE19vq8E7Vdo6",
          'secret': "j31QwdMJiqWxXr2VUsQYwYaj4bHaCurXCC6MjXzN3tmKGP7TH0nY5qw9J6zQyB10",
    },
}

# 形成exchange_config
BINANCE_CONFIG_dict = {}
HOST_NAME = 'fapi.binance.com'
for acc_name in api_dict.keys():
    BINANCE_CONFIG_dict[acc_name] = {
        'timeout': exchange_timeout,
        'rateLimit': 10,
        'verbose': False,
        'hostname': HOST_NAME,  # 无法fq的时候启用
        'enableRateLimit': False}
    BINANCE_CONFIG_dict[acc_name]['apiKey'] = api_dict[acc_name]['apiKey']
    BINANCE_CONFIG_dict[acc_name]['secret'] = api_dict[acc_name]['secret']


# =底层k线周期
kline_interval = '5m'  # 目前支持5m，15m，30m，1h，2h等。得交易所支持的K线才行。最好不要低于5m

# k线偏移的时间
offset_time = '-20m'  # 目前支持m（分钟），h（小时）为单位。必须是time_interval的整数倍。负数为提前执行，正数为延后执行。


# 设置初始资金来源相关参数
funding_config = {
    'spot_from_main_acc': True,  # 是否从母账户划转保证金币
    'funding_coin': 'USDT',  # 若现货不足，用于买入现货的交易币种，目前仅能填USD等价币，如USDT，BUSD
    'funding_coin_from_main_acc': True,  # 是否从母账户划转计价币
    'surplus_spot_deal': 'TO_MAIN',  # 建仓剩余现货处理方式,'SAVE'为保留在子账户现货账户，'TO_MAIN'为划转到母账户现货账户
}

take_profit_rate = 0  # 如果在回到套保状态时，保证金金额达到初始资金的几倍时，将提取多余的保证金（利润）到母账户。
