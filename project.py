import sys
import json
import pandas as pd
import requests
import re
import csv
from abc import ABC, abstractmethod
from datetime import date, timedelta
import spacy
from spacy.matcher import Matcher
from spacy import util

def main():
    # print(get_bond_yields())

    # book_onetime = onetime_book('onetime.csv')
    # book_recurring = recurring_book('recurring.csv')
    # book_savings = savings_book('savings.csv')
    # book_onetime.book_writer()
    # book_recurring.book_writer()
    # book_savings.book_writer()
    #print(get_bond_yields())
    bank_records = Bank_records()
    bank_records = Statement_analyzer("TransactionHistory_2023-Mar-Jul.csv").reader()
    print(bank_records)
    print(json.dumps(bank_records.sum_by_category(),indent=2))
    print(json.dumps(bank_records.monthly_cf_bef_inv(),indent=2))

class Book(ABC):
    def __init__(self, col_ext: list, filepath: str):
        self.filepath = filepath
        self.columns = ['num'] + col_ext
        try:
            self.bookdata = pd.read_csv(self.filepath, index_col=0)
        # catch FileNotFoundError and pandas.errors.EmptyDataError
        except Exception:
            self.bookdata = pd.DataFrame(columns=self.columns)

    def __del__(self):
        self.bookdata.to_csv(self.filepath, columns=self.columns, index_label=['name'])

    def __str__(self):
        return self.bookdata.to_string()

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
    def bookdata(self):
        return self._bookdata
    
    @bookdata.setter
    def bookdata(self, bookdata):
        self._bookdata = bookdata

    def book_writer(self) -> None:
        """
            A interface for user to edit the book items

            :return: A Dataframe that contains the update bookdata
            :rtype: pandas DataFrame object
        """
        items = self.bookdata.to_dict()
        print(pd.DataFrame.from_records(items, columns=self.columns), end='\n\n')
        while True:
            while not (option := input("Input 'a' to add and 'd' to delete\nInput 'exit' to end\nInput: ").strip().lower()) in ('a', 'd', 'exit'):
                pass
            if option == 'exit':
                break

            if (name := input("Name (No space char allowed): ").strip().lower()).isalnum():
                match option:
                    case "a":
                        items[self.columns[0]][name] = self.get_col1()
                        items[self.columns[1]][name] = self.get_col2()
                    case "d":
                        try:
                            items[self.columns[0]].pop(name)
                            items[self.columns[1]].pop(name)
                        except KeyError:
                            print("Item doesn't exist")
            print(pd.DataFrame.from_records(items, columns=self.columns), end='\n\n')
            
        self.bookdata = pd.DataFrame.from_records(items, columns=self.columns)

    def get_col1(self) -> float:
        while True:
            try:
                num = float(input("Number (Negative for expense or debt): "))
                break
            except ValueError:
                print("Invalid floating point number")
        return num

    @abstractmethod
    def get_col2(self):
        pass

class Onetime_book(Book):
    def __init__(self, filepath: str):
        super().__init__(['date',], filepath)
    
    def get_col2(self) -> date:
        while True:
            try:
                d = date.fromisoformat(input("Date YYYY-MM-DD: "))
                break
            except ValueError:
                print("Invalid date format")   
        return d

class Recurring_book(Book):
    def __init__(self, filepath: str):
        super().__init__(['freq',], filepath)
    
    def get_col2(self) -> timedelta:
        while True:
            try:
                d = timedelta(days=int(input("Frequency(days): ")))
                break
            except ValueError:
                print("Invalid date format")   
        return d

class Savings_book(Book):
    def __init__(self, filepath: str):
        super().__init__(['rainy-day-fund',], filepath)
    
    def get_col2(self) -> float:
        print("Rainy day fund, ", end='')
        return self.get_col1()

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
        return categorized
    
    def monthly_cf_bef_inv(self):
        categorized = self.sum_by_category()
        sum = {}
        for month in categorized:
            for key, value in categorized[month].items():
                if self._is_inv(key):
                    ...
                else:
                    if month not in sum:
                        sum[month] = {'spending': 0, 'income': 0}
                    if value < 0:
                        # spending
                        sum[month]['spending'] += value
                    else:
                        # income
                        sum[month]['income'] += value
        return sum

    def _is_inv(self, key):
        return self._is_bond_inv(key)

    def _is_bond_inv(self, key):
        return re.search(r"ISSUE CODE:[A-Z][A-Z0-9]{1}[0-9]{5}[A-Z]", key)

class Statement_analyzer:
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
        
    @property
    def filepath(self):
        return self._filepath
    
    @filepath.setter
    def filepath(self, filepath):
        self._filepath = filepath

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
                amount = float(amount_str.replace(',',''))
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