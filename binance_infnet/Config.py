"""
币安交易所网格策略实盘需要的配置参数
"""

# 钉钉配置
dingding_config = {
    'robot_id': '',
    'secret': ''
}
# 账户api，本策略目前只能设置一个子账户
api_dict = {
    'main': {
        'apiKey': '',
        'secret': '',
    },
}

# =====配置运行相关参数=====

# =底层数据时间粒度 # MOD
time_interval = '5m'  # 目前支持以m或h为单位,数字须为整数。得binance支持的K线才行。最好不要低于5m。
# 常用：1分钟线1m，5分钟线5m，15分钟线15m，30分钟线30m，小时线60m或1h，4小时线240m或4h，日线1440m或24h，周线10080m或168h。最大值为10080m或168h

# =执行的时间间隔（多长时间执行一次定投） # MOD ADD
execution_interval = '60m'  # 必须和time_interval使用相同单位，即同为m或同为h，最好是time_interval的整数倍数。
# 常用：1分钟投1m，5分钟投5m，15分钟投15m，30分钟投30m，小时投60m或1h，4小时投240m或4h，日投1440m或24h，周投10080m或168h，月投（4周）40320m或672h。

# 执行时间的偏移量，必须和time_interval使用相同单位，且必须是time_interval的整数倍
offset_time = '-20m'

# 下面这些参数一般不用改

# 币安最小交易金额不能小于10u, 设置大一点，避免计算经度出现误差，无法成交
min_trade_account = 12
# 设定最多收集多少根历史k线
max_len = 89
# 币安订单状态对照表
binance_order_state = {
    'NEW': '订单被交易引擎接受',
    'PARTIALLY_FILLED': '部分订单被成交',
    'FILLED': '订单完全成交',
    'CANCELED': '用户撤销了订单',
    'PENDING_CANCEL': '撤销中',
    'REJECTED': '订单没有被交易引擎接受，也没被处理',
    'EXPIRED': '订单被交易引擎取消'
}

# sleep时间配置
short_sleep_time = 1  # 用于和交易所交互时比较紧急的时间sleep，例如获取数据、下单
medium_sleep_time = 2  # 用于和交易所交互时不是很紧急的时间sleep，例如获取持仓
long_sleep_time = 10  # 用于较长的时间sleep
long_long_sleep_time = 30  # 用于较长的时间sleep

# timeout时间
exchange_timeout = 3000  # 3s

# 形成exchange_config
BINANCE_CONFIG_dict = {}
HOST_NAME = 'binance.com'
for account_name in api_dict.keys():
    BINANCE_CONFIG_dict[account_name] = {
        'timeout': exchange_timeout,
        'rateLimit': 10,
        'hostname': HOST_NAME,  # 无法fq的时候启用
        'enableRateLimit': False
    }
    BINANCE_CONFIG_dict[account_name]['apiKey'] = api_dict[account_name]['apiKey']
    BINANCE_CONFIG_dict[account_name]['secret'] = api_dict[account_name]['secret']

# 兼容主程序
robot_id_secret = [dingding_config['robot_id'], dingding_config['secret']]


# 交易币对配置
symbol_config_dict = {
    'main': {
        'symbol_config':
            {
                'BTC-USDT': {
                    'instrument_id': 'BTC-USDT',  # 现货币对，-前是交易币，-后是计价币
                    'instrument_type': 'spot',
                    'strategy_name': 'real_tomato_net',  # 定投策略
                    'base_invest_val': 1.0,  # 以计价货币计的基础定投额
                    'invested_times': 0,  # 策略开始时的已投资次数，请准确设定，否则会导致意外交易（不涉及投资次数的策略可随意设）
                    'para': [800],
                },
                'ETH-USDT': {
                    'instrument_id': 'ETH-USDT',  # 现货币对，-前是交易币，-后是计价币
                    'instrument_type': 'spot',
                    'strategy_name': 'real_tomato_net',  # 定投策略
                    'base_invest_val': 1.0,  # 以计价货币计的基础定投额
                    'invested_times': 0,  # 策略开始时的已投资次数，请准确设定，否则会导致意外交易（不涉及投资次数的策略可随意设）
                    'para': [800],
                },
                # 'ICP-USDT': {
                #     'instrument_id': 'ICP-USDT',  # 现货币对，-前是交易币，-后是计价币
                #     'strategy_name': 'real_tomato_net',  # 定投策略
                #     'base_invest_val': 1.0,  # 以计价货币计的基础定投额
                #     'invested_times': 0,  # 策略开始时的已投资次数，请准确设定，否则会导致意外交易（不涉及投资次数的策略可随意设）
                #     'para': [100],
                # },
                # 'BNB-USDT': {
                #     'instrument_id': 'BNB-USDT',  # 现货币对，-前是交易币，-后是计价币
                #     'strategy_name': 'real_tomato_net',  # 定投策略
                #     'base_invest_val': 1.0,  # 以计价货币计的基础定投额
                #     'invested_times': 0,  # 策略开始时的已投资次数，请准确设定，否则会导致意外交易（不涉及投资次数的策略可随意设）
                #     'para': [400],
                # },
                # 'DOGE-USDT': {
                #     'instrument_id': 'DOGE-USDT',  # 现货币对，-前是交易币，-后是计价币
                #     'strategy_name': 'real_tomato_net',  # 定投策略
                #     'base_invest_val': 1.0,  # 以计价货币计的基础定投额
                #     'invested_times': 0,  # 策略开始时的已投资次数，请准确设定，否则会导致意外交易（不涉及投资次数的策略可随意设）
                #     'para': [100],
                # },
                # 'DASH-USDT': {
                #     'instrument_id': 'DASH-USDT',
                #     'strategy_name': 'real_tomato_net',  # 不同币种可以使用不同的策略
                #     'para': [100],
                #     'base_invest_val': 1.0,
                #     'invested_times': 0
                # },
                # 'CAKE-USDT': {
                #     'instrument_id': 'CAKE-USDT',
                #     'strategy_name': 'real_tomato_net',  # 不同币种可以使用不同的策略
                #     'para': [100],
                #     'base_invest_val': 1.0,
                #     'invested_times': 0
                # },
                # 'TRU-USDT': {
                #     'instrument_id': 'TRU-USDT',
                #     'strategy_name': 'real_tomato_net',  # 不同币种可以使用不同的策略
                #     'para': [100],
                #     'base_invest_val': 1.0,
                #     'invested_times': 0
                # }
            },
    },
}
# 是否开启资金分组
is_use_capital_group = True  # True表示开启按资金分组，False表示关闭资金分组，全部币种在同一时间交易
# 根据资金分别设置提前时间
capital_offset_time = {
    # '-30m': 100,
    '-15m': 800,
    # '-5m': 400
}

