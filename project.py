import sys
import json
import pandas as pd
import requests
from accounts import *
from statements import *
from decimal import *

def main():
    pd.set_option('display.max_rows', None)
    bank_records = Bank_records(Statement_analyzer("TransactionHistory_2023-Mar-Jul.csv").reader())
    spending = Decimal(bank_records.monthly_spending().mean()[0]).quantize(Decimal('.01'))
    income = Decimal(bank_records.monthly_income().min()[0])
    print(bank_records)
    print(bank_records.sum_by_category(monthly=True))
    print(bank_records.monthly_spending())
    print(bank_records.monthly_spending().mean())
    print(bank_records.monthly_income().min())
    print(bank_records.income_report())

    print(get_bond_yields())

    future_cf = Future_CF('Future_cashflows.xlsx')
    for item in future_cf.df.items():
        print(item)

def get_bond_yields():
    base_url = 'https://api.fiscaldata.treasury.gov/services/api/fiscal_service'
    endpoint = '/v2/accounting/od/avg_interest_rates'

    f_time = f'record_date:gte:{(date.today()-timedelta(days=365)).strftime("%Y-%m-%d")}'
    f_security_type = f'security_desc:in:(Treasury Bills,Treasury Bonds)'
    filter = '?filter=' + f_time + f_security_type

    print(filter)
    url = base_url + endpoint + '?filter=' + f_time + ',' + f_security_type
    r = requests.get(url)
    return json.dumps(r.json()['data'], indent=2)

if __name__ == "__main__":
    main()