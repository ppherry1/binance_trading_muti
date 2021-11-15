import ccxt
import os
import sys
from time import sleep
import numpy as np
import pandas as pd
from datetime import datetime

pd.set_option('display.max_rows', 1000)
pd.set_option('expand_frame_repr', False)  # 当列太多时不换行
# 设置命令行输出时的列对齐功能
pd.set_option('display.unicode.ambiguous_as_wide', True)
pd.set_option('display.unicode.east_asian_width', True)

# 返回的计划账户sub_accounts必须有一列['plan_available']作为计划调整后的余额


# # 不调整资金，用于测试
# def allocate_none(sub_accounts, main_account, equity_curve, strategy_para):
#     sub_accounts['plan_available'] = sub_accounts['max_withdraw']
#     return sub_accounts
#
#
# # 随机调整资金，用于测试，strategy_para需要有两个参数，第一个是待调整的币种，第二个是随机划拨的最大值，例如['USDT', 1.0]
# def allocate_random(sub_accounts, main_account, equity_curve, strategy_para):
#     sub_accounts = sub_accounts.loc[sub_accounts['currency'] == strategy_para[0]]
#     sub_accounts['plan_available'] = sub_accounts['max_withdraw'].apply(lambda x: x + (np.random.rand() - 0.5) * strategy_para[1] * 2)
#     return sub_accounts
#
#
# # 取出不用于策略账户的可划转USDT，按比例分配到各策略账户
# # strategy_para需要有两个参数，第一个是待调整的币种，第二个是每种策略的分配比例，比例总值不能大于1.0，可以小于1，小于1的部分则为母账户留存比例
# # 例如['USDT', {'cta': 0.3, 'autoinvest': 0.2, 'infnet': 0.4}]，即表示择时策略分配30%，定投策略分配20%，无限网格分配40%，母账户留存10%
# def allocate_withdraw_by_fixed_rate(sub_accounts, main_account, equity_curve, strategy_para):
#     sub_accounts = sub_accounts.loc[sub_accounts['currency'] == strategy_para[0]]  # 筛选currency为para[0]指定的币种
#     sr = sub_accounts.groupby(['allocate_type'])['allocate_type'].count()
#     sr.name = 'allocate_type_count'
#     sr2 = pd.Series(strategy_para[1], name='allocate_type_rate')
#     sub_accounts = sub_accounts.set_index('allocate_type').join(sr, on='allocate_type').join(sr2, on='allocate_type')
#     sub_accounts.reset_index(inplace=True, drop=False)
#     if main_account:
#         sum_available = sub_accounts['max_withdraw'].sum() + float(main_account[0]['available'])
#     else:
#         sum_available = sub_accounts['max_withdraw'].sum()
#     print(sum_available)
#     sub_accounts['plan_available'] = sum_available * sub_accounts['allocate_type_rate'] / sub_accounts['allocate_type_count']
#     sub_accounts['plan_available'].fillna(0, inplace=True)
#     return sub_accounts


def allocate_by_fixed_rate(total_asset, alloc_rate_info, strategy_params):
    alloc_rate_list = []
    for key, value in alloc_rate_info.items():
        tmp = dict()
        tmp['acc'] = key
        for into_key, into_value in value.items():
            tmp[into_key] = into_value
        alloc_rate_list.append(tmp)
    df_alloc_rate = pd.DataFrame(alloc_rate_list)
    df_alloc_rate.set_index('acc', inplace=True)
    df_alloc_rate = df_alloc_rate.apply(lambda x: x/x.sum(axis=0))
    alloc_rate = strategy_params[0]
    for col in df_alloc_rate.columns.to_list():
        df_alloc_rate[col] = total_asset * df_alloc_rate[col] * alloc_rate[col]
    plan_sub_accs = df_alloc_rate.sum(axis=1).to_dict()
    return plan_sub_accs

