
account_type_contrast = {'spot': '1', 'futures': '3', 'funding': '6', 'swap': '9'}

# 配置钉钉
robot_id = '3316400a3627a7520d01371322510fbf9f4fe5c7bf5420c40b987ce44e990fe6'
secret = 'SECf8a88997fa4e3ced30d5b02dd38b06d1e949f47d1b66233630350c2fa9623b04'

base_capital = 'USDT'
allocate_types_default = ['cta', 'infnet']  # 执行的策略类型
strategy_leverage_default = {'SPOT': 20, 'SWAP': 2, 'FUTURES': 2,  'MARGIN': 2}  # 执行的策略类型
allocate_rate_type = {'cta': 'free', 'autoinvest': 'all', 'infnet': 'all'}  # 策略分配方式，free为按未开仓分配，all为全分配
strategy_name_default = 'allocate_by_fixed_rate'  # 执行的资金配置策略
strategy_para_default = [{'cta': 0.7, 'infnet': 0.1}]  # 资金配置策略的参数

