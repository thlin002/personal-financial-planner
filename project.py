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
    bank_record = Bank_record()
    bank_record = Statement_analyzer("TransactionHistory_2023-Mar-Jul.csv").analyze()
    print(bank_record)
    print(bank_record.sum())

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

class Bank_record:
    def __init__(self):
        self.record = {}
    
    def __getitem__(self, key):
        if key not in self.record:
            self.record[key] = 0    # Initialize the key if it doesn't exist
        return self.record[key]
    
    def __setitem__(self, key, value):
        self.record[key] = value

    def __str__(self):
        return json.dumps(self.record, indent=2)
    
    def sort(self):
        self.record = dict(sorted(self.record.items()))
        return self
    
    def sum(self):
        return sum(self.record.values())

class Statement_analyzer:
    def __init__(self, filepath):
        self.filepath = filepath
        self.bank_record = Bank_record()

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

    def tx_reader(self):
        """
            convert the transaction history csv file into a list of dict
        """
        with open(self.filepath) as file:
            for line in file:
                if line.split(',')[0].strip() == 'Transaction History':
                    break
            
            bank_record =[]
            reader = csv.DictReader(file)
            for row in reader:
                bank_record.append({row['Transaction date'], })
            ...

    def analyze(self):
        with open(self.filepath) as file:
            for line in file:
                if line.split(',')[0].strip() == 'Transaction History':
                    break
           
            reader = csv.DictReader(file)
            cat, amount = None, None
            for row in reader:
                cat, amount = self.tx_sorter(row, cat, amount)
            if amount:
                self.bank_record[self.description_parser(cat)] += amount    # add the last transaction if the last row is the first row of a transaction
            
            return self.bank_record.sort()

    def tx_sorter(self, row, prev_cat=None, prev_amount=None):
        """
            Sort the transaction into different categories
        """
        try:
            # if amount_str is not empty, then the row is the first row of a transaction
            if (amount_str := '-'+row['Withdrawals (SGD)'] if (row['Withdrawals (SGD)']) else None) or (amount_str := row['Deposits (SGD)']):
                # Storing the first row
                tx_category = row['Description']
                amount = float(amount_str.replace(',',''))
                # look back to previous row to see if the previous transaction has second row. 
                # (The second row of a transaction is the row without the amount)
                if prev_amount:
                    self.bank_record[self.description_parser(prev_cat)] += prev_amount # if no second row, use categroy as key for the bank_record
                return tx_category, amount
            else:
                prev_detail = row['Description']
                self.bank_record[self.description_parser(prev_detail)] += prev_amount
                return None, None
        except ValueError:
            sys.exit("Invalid float value in the Withdrawal/Deposits column")

    def description_parser(self, tx_detail):
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