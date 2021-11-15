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
