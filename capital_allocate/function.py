def convert_account(exchange_name, df, func_name):
    print(func_name)
    if exchange_name == 'OKEX':
        if func_name == 'get_account_balance':
            print(df)
            return df

# def concat_config(allocate_types=allocate_types_default):


