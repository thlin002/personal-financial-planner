import sys
import json
from typing import Any
import pandas as pd
import requests
import re
import csv
from abc import ABC, abstractmethod
from datetime import date, timedelta
import spacy
from spacy.matcher import Matcher
from spacy import util
from decimal import *

def main():
    # print(get_bond_yields())
    non_recurring_revenue = Non_recurring_revenue('onetime.csv')
    recurring_revenue = Recurring_revenue('recurring.csv')
    savings = Savings('savings.csv')
    non_recurring_revenue.usr_book_writer()
    recurring_revenue.usr_book_writer()
    savings.usr_book_writer()
    # print(get_bond_yields())
    # bank_records = Bank_records()
    # bank_records = Statement_analyzer("TransactionHistory_2023-Mar-Jul.csv").reader()
    # print(bank_records)
    # print(json.dumps(bank_records.sum_by_category(),indent=2, default=str))
    # all_month_sum = bank_records.monthly_cf_bef_inv()
    # print(json.dumps(all_month_sum,indent=2, default=str))
    # avg_spending = 0
    # for n, monthly in enumerate(all_month_sum.values()):
    #     avg_spending += monthly['spending']
    # avg_spending /= (n+1)
    # print(avg_spending)
        
# Book and its inherited classes are used to store Future CF as opposed to Past CF defined in Bank_records, 
# and provide a preliminary CLI for user to edit the book.
# TODO: Implement the GUI for user to edit the book with Django
class Book(ABC):
    @property
    def filepath(self):
        return self._filepath
    
    @filepath.setter
    def filepath(self, filepath):
        self._filepath = filepath

    @property
    def columns(self):
        return self._columns
    
    @columns.setter
    def columns(self, columns):
        self._columns = columns

    @property
    def get_col_funcs(self):
        return self._get_col_funcs
    
    @get_col_funcs.setter
    def get_col_funcs(self, get_col_funcs):
        self._get_col_funcs = get_col_funcs
    
    def __init__(self, col_ext: list, filepath: str):
        self.filepath = filepath
        self.columns = ['num'] + col_ext
        # could append more get_col functions to the list in the inherited class if needed
        self.get_col_funcs = [self.get_col1, self.get_col2]
        try:
            # Read the csv file if it exists and set the first column as index
            self.bookdata = pd.read_csv(self.filepath, index_col=0)
        
        # catch FileNotFoundError and pandas.errors.EmptyDataError
        except Exception:
            self.bookdata = pd.DataFrame(columns=self.columns)

    def __del__(self):
        # Write the bookdata to the csv file, with the first column as index
        self.bookdata.to_csv(self.filepath, columns=self.columns, index_label=['name'])

    def __str__(self):
        return self.bookdata.to_string()

    def get_col1(self) -> Decimal:
        return Decimal(input("Amount, Input negative num for expense/debt: "))

    @abstractmethod
    def get_col2(self):
        pass

    def usr_book_writer(self) -> None:
        """
            A CLI interface for user to edit the book items

            :return: A Dataframe that contains the update bookdata
            :rtype: pandas DataFrame object
        """
        # items is a dict of dict converted from the bookdata, which is a DataFrame
        items = self.bookdata.to_dict()
        while True:
            print(pd.DataFrame.from_records(items, columns=self.columns), end='\n\n')
            
            # loop until user input the correct option
            while not (option := input("Input 'a' to ammend, 'd' to delete, and 'exit' to end\nInput: ").strip().lower()) in ('a', 'd', 'exit'):
                pass

            if option == 'exit':
                break
            
            if (name := input("Name (No space allowed): ").strip().lower()).isalnum():
                match option:
                    case "a":
                        self.usr_write_row(items, name)
                    case "d":
                        self.usr_delete_row(items, name) 
            
        self.bookdata = pd.DataFrame.from_records(items, columns=self.columns)

    def usr_write_row(self, items: dict, name: str) -> None:
        for i, col in enumerate(self.columns):
            while True:
                try:
                    items[col][name] = self.get_col_funcs[i]()
                    break
                except Exception:
                    print("Invalid input")

    def usr_delete_row(self, items: dict, name: str) -> None:
        for col in self.columns:
            try:
                items[col].pop(name)
            except KeyError:
                print("Item doesn't exist")

class Non_recurring_revenue(Book):
    def __init__(self, filepath: str):
        super().__init__(['date',], filepath)
        
    def get_col2(self) -> date:
        return date.fromisoformat(input("Date YYYY-MM-DD: "))

class Recurring_revenue(Book):
    def __init__(self, filepath: str):
        super().__init__(['freq',], filepath)
    
    def get_col2(self) -> timedelta:
        return timedelta(days=float(input("Frequency(days): ")))
    
    def update_avg_spending(self, avg_spending: Decimal) -> None:
        ...

class Savings(Book):
    def __init__(self, filepath: str):
        super().__init__(['rainy-day-fund',], filepath)
    
    def usr_book_writer(self) -> None:
        items = self.bookdata.to_dict()
        while True:
            print(pd.DataFrame.from_records(items, columns=self.columns), end='\n\n')
            
            # loop until user input the correct option
            while not (option := input("Update savings. Input 'a' to ammend, 'exit' to end\nInput: ").strip().lower()) in ('a', 'exit'):
                pass

            if option == 'exit':
                    break
            self.usr_write_row(items, 'savings')
            print(pd.DataFrame.from_records(items, columns=self.columns), end='\n\n')

        self.bookdata = pd.DataFrame.from_records(items, columns=self.columns)

    def get_col2(self) -> Decimal:
        return Decimal(input("Rainy day fund: "))

# end of Book and its inherited classes

class Bank_records:
    def __init__(self):
        # key: month, value: list of dict, each dict is a transaction
        # could be access by bank_record[month]
        self._records = {}

    def __getitem__(self, key):
        if key not in self._records:
            self._records[key] = []    # Initialize the key if it doesn't exist
        return self._records[key]
    
    def __setitem__(self, key, lst):
        self._records[key] = lst

    def append(self, key, tx):
        self._records[key].append(tx)

    def __str__(self):
        string = ""
        for month in self._records:
            for tx in self._records[month]:
                string += f"month: {month:<2} date: {tx['date'].isoformat():<12} amount: {tx['amount']:<15} name: {tx['name']}\n"
        return string

    def sort(self):
        ...
        #self._records = dict(sorted(self._records.items()))
        return self
    
    def sum_by_category(self):
        categorized = {}
        for month in self._records:
            for tx in self._records[month]:
                if month not in categorized:
                    categorized[month] = {}
                if tx['name'] not in categorized[month]:
                    categorized[month][tx['name']] = 0
                categorized[month][tx['name']] += tx['amount']
            # sort the dict by key
            categorized[month] = dict(sorted(categorized[month].items()))
        return categorized
    
    def monthly_cf_bef_inv(self) -> tuple:
        categorized = self.sum_by_category()
        sum_by_month = {}
        avg_monthly_spending = 0
        avg_monthly_income = 0

        for n, month in enumerate(categorized):
            for key, value in categorized[month].items():
                if self._is_inv(key):
                    # to be implemented
                    ...
                else:
                    if month not in sum_by_month:
                        sum_by_month[month] = {'spending': 0, 'income': 0}
                    if value < 0:
                        # spending
                        sum_by_month[month]['spending'] += value
                    else:
                        # income
                        sum_by_month[month]['income'] += value
            # for calculating the average spending and income
            avg_monthly_spending += sum_by_month[month]['spending']
            avg_monthly_income += sum_by_month[month]['income']
        
        avg_monthly_spending /= (n+1)
        avg_monthly_income /= (n+1)

        # return tuple(Decimal, Decimal, dict of dict)
        return avg_monthly_spending, avg_monthly_income, sum_by_month

    def _is_inv(self, key):
        return self._is_bond_inv(key)

    def _is_bond_inv(self, key):
        return re.search(r"ISSUE CODE:[A-Z][A-Z0-9]{1}[0-9]{5}[A-Z]", key)

class Statement_analyzer:
    @property
    def filepath(self):
        return self._filepath
    
    @filepath.setter
    def filepath(self, filepath):
        self._filepath = filepath
    
    def __init__(self, filepath):
        self.filepath = filepath
        self.bank_record = Bank_records()

        # setup regex
        self.tx_regex = {}
        # re_prefix match example 1: "25/07/23  xx-9296 BUS/MRT"            pattern: "(?:[0-9]{2}/[0-9]{2}/[0-9]{2} +)?(?:xx-[0-9]{4} +)?"
        # re_prefix match example 2: "OTHR - "
        self.tx_regex['prefix'] = r"(?:[0-9]{2}/[0-9]{2}/[0-9]{2} +)?(?:xx-[0-9]{4} +|OTHR - +|[0-9]{5}\w+)?"
        # re_suffix match example 1: "              P 05/03/23 USD 15.30"   pattern: "(?: *(?:[A-Z]) *?)?(?:[0-9]{2}/[0-9]{2}/[0-9]{2}.*)"
        # re_suffix match example 2: "       S 06/03/23"                    pattern: "(?: *(?:[A-Z]) *?)?(?:[0-9]{2}/[0-9]{2}/[0-9]{2}.*)"
        # re_suffix match example 3: "           N  PWS FOOD"               pattern: "( +[A-Z] +.*)?"
        # re_suffix match example 4: " 297532059        S"
        self.tx_regex['suffix'] = r"[0-9]*(?:(?: *(?:[A-Z]) *)?(?:[0-9]{2}/[0-9]{2}/[0-9]{2}.*)| +[A-Z] +.*)?$"
        
        # setup spacy
        self.nlp = spacy.load("en_core_web_sm")
        self.matcher = Matcher(self.nlp.vocab, validate=True)
        #item_patterns = [[{"POS": "ADJ", "OP": "*"}, {"POS": {"IN": ["NOUN", "PROPN"]}, "OP": "+"}]]
        item_patterns = [[{"ENT_TYPE": {"NOT_IN": ["LAW", "DATE", "TIME", "PERCENT", "MONEY", "QUANTITY", "ORDINAL", "CARDINAL"]}, "OP": "+"}]]
        self.matcher.add("ITEM_PATTERN", item_patterns)

    def reader(self):
        with open(self.filepath) as file:
            for line in file:
                if line.split(',')[0].strip() == 'Transaction History':
                    break
           
            reader = csv.DictReader(file)
            date, cat, amount = None, None, None
            for row in reader:
                date, cat, amount = self._tx_parser(row, date, cat, amount)
            if amount:
                self.bank_record[date.month].append({'date': date, 'name': self.description_parser(cat), 'amount': amount}) # add the last transaction if the last row is the first row of a transaction
            return self.bank_record.sort()

    def _tx_parser(self, row, prev_date=None, prev_cat=None, prev_amount=None):
        try:
            # if amount_str is not empty, then the row is the first row of a transaction
            if (amount_str := '-'+row['Withdrawals (SGD)'] if (row['Withdrawals (SGD)']) else None) or (amount_str := row['Deposits (SGD)']):
                # Storing the first row
                tx_category = row['Description']
                amount = Decimal(amount_str.replace(',',''))
                match = re.search(r"([0-9]{2})/([0-9]{2})/([0-9]{4})", row['Transaction date']) # extract the date, month, year
                if match:
                    tx_date = date(int(match.group(3)), int(match.group(2)), int(match.group(1)))
                # look back to previous row to see if the previous transaction has second row. 
                # (The second row of a transaction is the row without the amount)
                if prev_amount:
                    self.bank_record[prev_date.month].append({'date': prev_date, 'name': self._description_parser(prev_cat), 'amount': prev_amount}) # if no second row, use categroy for the item name
                return tx_date, tx_category, amount
            else:
                prev_detail = row['Description']
                self.bank_record[prev_date.month].append({'date': prev_date, 'name': self._description_parser(prev_detail), 'amount': prev_amount}) # if has second row, use the second row for the item name
                return None, None, None
        except ValueError:
            sys.exit("Invalid float value in the Withdrawal/Deposits column")

    def _description_parser(self, tx_detail):
        re_matches = re.search(self.tx_regex['prefix']+r"(.+?)"+self.tx_regex['suffix'], tx_detail)
        if re_matches:
            #print(re_matches.group(1))
            doc = self.nlp(re_matches.group(1))
            matches = self.matcher(doc, as_spans=True)
            filtered = util.filter_spans(matches)
            item_name = ""
            for word in filtered:
                item_name += word.text + " "
        
        if (item := item_name.strip()) == "":
            sys.exit("No item name found")
        return item

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