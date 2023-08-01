import json
import pandas as pd
import requests
import re
import csv
from abc import ABC, abstractmethod
from datetime import date, timedelta
from itertools import islice
import spacy
from spacy.matcher import Matcher
from spacy import util

def main():
    # print(get_bond_yields())

    # book_onetime = onetime_book('onetime.csv')
    # book_recurring = recurring_book('recurring.csv')
    # book_savings = savings_book('savings.csv')
    # book_onetime.book_modifier()
    # book_recurring.book_modifier()
    # book_savings.book_modifier()
    #print(get_bond_yields())
    tx_parser("TransactionHistory_2023-Mar-Jul.csv")

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

    def book_modifier(self) -> None:
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

def tx_parser(filepath):
    nlp = spacy.load("en_core_web_sm")
    matcher = Matcher(nlp.vocab, validate=True)
    item_patterns = [[{"POS": "ADJ", "OP": "*"}, {"POS": {"IN": ["NOUN", "PROPN"]}, "OP": "+"}]]
    matcher.add("ITEM_PATTERN", item_patterns)
    with open(filepath) as file:
        reader = csv.DictReader(islice(file, 5, None))
        
        for row in reader:
            tx_category = row['Description']
            if (withdrawal:=row['Withdrawals (SGD)']):
                print(f"{tx_category}, {withdrawal}", end=' ') 
            elif (deposit:= row['Deposits (SGD)']):
                print(f"{tx_category}, {deposit}", end=' ') 
            row = reader.__next__()
            # re_prefix match example 1: "25/07/23  xx-9296 BUS/MRT", pattern: "(?:[0-9]{2}/[0-9]{2}/[0-9]{2} +)?(?:xx-[0-9]{4} +)?"
            # re_prefix match example 2: "OTHR - "
            re_prefix = r"(?:[0-9]{2}/[0-9]{2}/[0-9]{2} +)?(?:xx-[0-9]{4} +|OTHR - +)?"
            # re_suffix match example 1: "              P 05/03/23 USD 15.30", pattern: "(?: *(?:[A-Z]) *?)?(?:[0-9]{2}/[0-9]{2}/[0-9]{2}.*)"
            # re_suffix match example 1: "       S 06/03/23", pattern: "(?: *(?:[A-Z]) *?)?(?:[0-9]{2}/[0-9]{2}/[0-9]{2}.*)"
            # re_suffix match example 2: "           N  PWS FOOD", pattern: "( +[A-Z] +.*)?"
            re_suffix = r"(?:(?: *(?:[A-Z]) *)?(?:[0-9]{2}/[0-9]{2}/[0-9]{2}.*)| +[A-Z] +.*)?$"
            re_matches = re.search(re_prefix+r"(.+?)"+re_suffix, row['Description'])
            if re_matches:
                print(re_matches.group(1))
                doc = nlp(re_matches.group(1))
                matches = matcher(doc, as_spans=True)
                filtered = util.filter_spans(matches)
                #print("Noun phrases:", matches)
                print("Noun phrases:", filtered)
            else:
                print("No matches")
            
            #doc = nlp(row['Description'])

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