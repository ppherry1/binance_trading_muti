from trading_class.wraps_func import *
from capital_allocate.capital_config import *
from capital_allocate import capital_strategy


class Account:
    def __init__(self, account_info, base_b='USDT'):
        # account_info包含apiKey, secret, passphrase, config, id, password。condig是策略配置。
        # apiKey, secret, passphrase是API，id是注册账户的邮箱或手机号(站内转账用)，password是资金密码
        self.exchange_name = 'OKEXbinance'
        self.exchange = ccxt.okex({'password': account_info['passphrase'],
                                   'timeout': 3000,
                                   'rateLimit': 10,
                                   'apiKey': account_info['apiKey'],
                                   'secret': account_info['secret'],
                                   })
        self.id = account_info['id']
        self.password = account_info['password']
        self.max_repeat_times = 10  # 重试交易所的交互命令最大重试次数
        self.lever = strategy_leverage_default
        self.base_capital = base_b
        self.allocate_rate_type = allocate_rate_type
        self.config = dict()
        self.config['strategy'] = dict()
        self.config['lever'] = dict()
        self.config['symbols'] = dict()
        for allocate_type in allocate_types_default:
            if self.id in eval(allocate_type).symbol_config_dict.keys():
                self.config['strategy'][allocate_type] = eval(allocate_type).symbol_config_dict[self.id]
                self.config['symbols'][allocate_type] = []

                for stra in eval(allocate_type).symbol_config_dict[self.id]['symbol_config'].keys():
                    self.config['symbols'][allocate_type].append(eval(allocate_type).symbol_config_dict[self.id]['symbol_config'][stra]['instrument_id'])
                    if 'leverage' in eval(allocate_type).symbol_config_dict[self.id]['symbol_config'][stra].keys():
                        self.config['lever'][eval(allocate_type).symbol_config_dict[self.id]['symbol_config'][stra]['instrument_id']] = float(eval(allocate_type).symbol_config_dict[self.id]['symbol_config'][stra]['leverage'])
            else:
                self.config[allocate_type] = None



    @try_catch
    @return_is_normal
    def post_asset_withdrawal(self, to_id, ccy, amt):
        # 用于转账给其他OK用户，注意：必须是免验证的账户
        # ccy是转账币种，amt是转账数量
        if self.password is None:
            print('未设置资金密码，无法转账')
            raise Exception
        else:
            result = self.exchange.private_post_asset_withdrawal(params={
                "amt": amt,
                "fee": "0",
                "pwd": self.password,
                "dest": "3",
                "ccy": ccy,
                "toAddr": to_id.id})
            return result

    @try_catch
    @return_is_normal(use_bin_return=True)
    def post_asset_transfer(self, from_asset, to_asset, ccy, amt, transfer_type="0"):
        # 资金划转，ccy是转账币种，amt是转账数量
        # 1：币币账户 3：交割合约 5：币币杠杆账户 6：资金账户 9：永续合约账户 12：期权合约 18：统一账户
        result = self.exchange.private_post_asset_transfer(params={
            "amt": amt,
            "ccy": ccy,
            "from": from_asset,
            "to": to_asset,
            "type": transfer_type
        })
        return result

    @try_catch
    @return_is_normal(use_bin_return=True)
    def post_account_set_leverage(self, instId, lever, mgnMode, posSide=None):
        df = self.exchange.private_post_account_set_leverage({
            "instId": instId,
            "lever": lever,
            "mgnMode": mgnMode,
            "posSide": posSide,
        })
        return df

    @convert_dataframe
    @return_is_normal
    @repeat
    def get_account_positions(self):
        df = self.exchange.private_get_account_positions()
        return df

    @convert_dataframe
    @return_is_normal
    @repeat
    def get_account_balance(self):
        df = self.exchange.private_get_account_balance()
        return df

    @convert_dataframe
    @return_is_normal
    @repeat
    def get_account_account_position_risk(self):
        df = self.exchange.private_get_account_account_position_risk()
        return df

    @convert_dataframe
    @return_is_normal
    @repeat
    def get_asset_balance(self):
        df = self.exchange.private_get_asset_balances()
        return df

    def refresh_base_asset_balance(self):
        df = self.get_asset_balance()
        if self.base_capital in df['ccy'].to_list():
            base_asset = float(df.loc[df['ccy'] == self.base_capital, 'availBal'][0])
            return base_asset
        else:
            return 0.0

    def capital_quick_send_to_main(self, main_acc, send_amt):
        self.post_asset_transfer('18', '6', self.base_capital, str(send_amt))
        self.post_asset_withdrawal(main_acc, self.base_capital, str(send_amt))

    def capital_quick_receive(self):
        asset = self.refresh_base_asset_balance()
        self.post_asset_transfer('6', '18', self.base_capital, str(asset))

    def refresh_capital_account(self):
        df_balance = self.get_account_balance()
        df_positions = self.get_account_positions()
        if df_balance.empty:
            df_balance = pd.DataFrame(columns=['ccy', 'eqUsd', 'eq'])
        if df_positions.empty:
            df_positions = pd.DataFrame(columns=['instId', 'imr', 'lever', 'notionalUsd', 'instType', 'pos'])
        df_balance = df_balance[['ccy', 'eqUsd', 'eq']].copy()
        if not df_balance.empty:
            base_balance = float(df_balance.loc[df_balance['ccy'] == self.base_capital, 'eq'][0])
        else:
            base_balance = 0
        df_balance = df_balance.loc[df_balance['ccy'] != self.base_capital]
        df_balance['instType'] = 'SPOT'
        df_balance['imr'] = df_balance['eqUsd'].copy()
        df_balance['lever'] = 1
        df_positions = df_positions[['instId', 'imr', 'lever', 'notionalUsd', 'instType', 'pos']].copy()
        df_balance.rename(columns={'ccy': 'instId', 'eqUsd': 'notionalUsd', 'eq': 'pos'}, inplace=True)
        df_capital = pd.concat([df_positions, df_balance])
        df_capital['true_lever'] = df_capital['instId'].map(self.config['lever'])
        df_capital.loc[df_capital['true_lever'].isna(), 'true_lever'] = df_capital.loc[df_capital['true_lever'].isna(), 'instType'].map(self.lever)
        df_capital['true_imr'] = df_capital['imr'].astype(float) * df_capital['lever'].astype(float) / df_capital['true_lever'].astype(float)
        with_draw = base_balance - df_capital['true_imr'].sum()
        return df_capital, with_draw

    def caculate_allocate_rate(self):
        # 计算本账户待分配份额
        df_positions = self.get_account_positions()
        if not df_positions.empty:
            position_symbol = df_positions['instId'].to_list()
        else:
            position_symbol = []
        allocate_rate = dict()
        for allocate_type in allocate_types_default:
            if self.allocate_rate_type[allocate_type] == 'free':
                if allocate_type in self.config['symbols'].keys():
                    allocate_rate[allocate_type] = len([val for val in self.config['symbols'][allocate_type] if val not in position_symbol])
            elif self.allocate_rate_type[allocate_type] == 'all':
                if allocate_type in self.config['symbols'].keys():
                    allocate_rate[allocate_type] = len(self.config['symbols'][allocate_type])
        return allocate_rate


main_account_info = {'apiKey': '3ff63842-c363-49c2-afd4-7af13e52ec98',
                     'secret': 'DA07AD847B22C9D4FC76FDEDE4A07353',
                     'passphrase': '8uu7yy6',
                     'id': 'ppherry@126.com',
                     'password': 'Aa123098'}
sub_accounts_info = [{'apiKey': 'e2961456-9d07-45d9-9236-db52d2b0715e',
                     'secret': '56D1939CC0FCA8E597113D5F5C3131B8',
                     'passphrase': '8uu7yy6',
                     'id': 'ppherry@yeah.net',
                     'password': 'Aa123098'},
                    {'apiKey': '8acfb334-ce4e-4de7-bf50-b6c488d7ee91',
                     'secret': '36E0BDCEA369CCBCA3FB9E1F4436901A',
                     'passphrase': '8uu7yy6',
                     'id': 'glasssquirrel@yeah.net',
                     'password': 'Aa123098'}
                    ]
main_account = Account(main_account_info)
main_asset = main_account.refresh_base_asset_balance()
sub_accounts = dict()
capital_info = dict()
with_draw_info = dict()
allocate_rate_info = dict()

for account in sub_accounts_info:
    sub_accounts[account['id']] = Account(account)
    capital_info[account['id']], with_draw_info[account['id']] = sub_accounts[account['id']].refresh_capital_account()
    allocate_rate_info[account['id']] = sub_accounts[account['id']].caculate_allocate_rate()


def deal_captital_strategy(main_asset, with_draw_info, alloc_rate_info, strategy_name, strategy_params):
    for acc in with_draw_info.keys():
        main_asset += float(with_draw_info[acc])
    plan_sub_accs = getattr(capital_strategy, strategy_name)(main_asset, alloc_rate_info, strategy_params)
    plan_list = []
    for acc in plan_sub_accs.keys():
        plan_tmp = dict()
        plan_tmp['acc'] = acc
        plan_tmp['plan'] = plan_sub_accs[acc]
        plan_tmp['wd'] = with_draw_info[acc]
        plan_list.append(plan_tmp)
    df_plan = pd.DataFrame(plan_list)
    df_plan['transfer'] = df_plan['plan'] - df_plan['wd']
    df_plan.sort_values('transfer', ascending=True, inplace=True)
    return df_plan


df_plan = deal_captital_strategy(main_asset, with_draw_info, allocate_rate_info, strategy_name_default, strategy_para_default)
for row in df_plan.loc[df_plan['transfer'] < 0].iterrows():
    sub_accounts[row[1]['acc']].capital_quick_send_to_main(main_account, abs(row[1]['transfer']))

time.sleep(180)
for row in df_plan.loc[df_plan['transfer'] > 0].iterrows():
    main_account.post_asset_withdrawal(row[1]['acc'], base_capital, row[1]['transfer'])
    sub_accounts[row[1]['acc']].capital_quick_receive()


# ss4 = main_account.post_account_set_leverage('FIL-USDT-SWAP', '2', 'cross')
# ss = main_account.get_account_positions()
# ss1 = main_account.get_account_balance()

# ss2 = main_account.post_asset_transfer("18", "6", "USDT", "1")
# transfer_result = main_account.post_asset_withdrawal(sub_account1, 'USDT', '1')


