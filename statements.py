import csv
import sys
import re
import pandas as pd
import spacy
from spacy.matcher import Matcher
from spacy import util
from datetime import date, datetime
from decimal import *

class Bank_records:
    def __init__(self, bank_records_df: pd.DataFrame):
        self.records = bank_records_df

    def __str__(self):
        return self.records.to_string()
    
    def sum_by_category(self, monthly=False):
        # could use pandas categoricals to further categorize the transactions, e.g. food, transportation, etc.
        if monthly:
            # TODO: make the date label to month only, not the last day of the month
            return pd.DataFrame(self.records.groupby('desc').resample('M', on='date')['amount'].sum(), columns=['amount'])  # set the last column name to amount
        else:
            #return self.records.groupby(pd.Grouper(freq="1M", key="date"))
            return pd.DataFrame(self.records.groupby('desc')['amount'].sum(), columns=['amount'])   # set the last column name to amount

    def monthly_spending(self) -> tuple:
        # boolean indexing by amount < 0 and desc containing no investment
        spending_records = self.records[(self.records['amount'] < 0) & ~(pd.Series(self.records['desc'].apply(self.is_inv)).array)]
        return pd.DataFrame(spending_records.groupby(pd.Grouper(freq="1M", key="date"))['amount'].sum(), columns=['amount'])

    def monthly_income(self) -> tuple:
        # boolean indexing by amount > 0 and desc containing no investment
        income_records = self.records[(self.records['amount'] > 0) & ~(pd.Series(self.records['desc'].apply(self.is_inv)).array)]
        return pd.DataFrame(income_records.groupby(pd.Grouper(freq="1M", key="date"))['amount'].sum(), columns=['amount'])

    def is_inv(self, key):
        return self.is_bond_inv(key)

    def is_bond_inv(self, key):
        return bool(re.search(r"ISSUE CODE:[A-Z][A-Z0-9]{1}[0-9]{5}[A-Z]", key))    # convert to bool for pandas boolean indexing
    
    def income_report(self):
        # All monthly income transactions
        print("All monthly income transactions:")
        income_category = self.sum_by_category(monthly=True)
        print(income_category[income_category['amount'] > 0], end='\n\n')
        # Monthly salary
        print("Monthly salary:")
        print(self.monthly_income(), end='\n\n')

    
class Statement_analyzer:
    #TODO add feature to parse Available Balance
    @property
    def tx_records(self):
        return self._tx_records
    
    @tx_records.setter
    def tx_records(self, tx_records):
        self._tx_records = tx_records

    @property
    def filepath(self):
        return self._filepath

    @filepath.setter
    def filepath(self, filepath):
        self._filepath = filepath
    
    def __init__(self, filepath):
        self.filepath = filepath
        self.tx_records = {'date': [], 'desc': [], 'amount': []}
        # setup regex
        self.tx_regex = {}
        """
        # re_prefix match example 1: "25/07/23  xx-9296 BUS/MRT"            pattern: "(?:[0-9]{2}/[0-9]{2}/[0-9]{2} +)?(?:xx-[0-9]{4} +)?"
        # re_prefix match example 2: "OTHR - "
        """
        self.tx_regex['prefix'] = r"(?:[0-9]{2}/[0-9]{2}/[0-9]{2} +)?(?:xx-[0-9]{4} +|OTHR - +|[0-9]{5}\w+)?"
        """
        suffix match example 1: "              P 05/03/23 USD 15.30"   pattern: "(?: *(?:[A-Z]) *?)?(?:[0-9]{2}/[0-9]{2}/[0-9]{2}.*)"
        suffix match example 2: "       S 06/03/23"                    pattern: "(?: *(?:[A-Z]) *?)?(?:[0-9]{2}/[0-9]{2}/[0-9]{2}.*)"
        suffix match example 3: "           N  PWS FOOD"               pattern: "( +[A-Z] +.*)?"
        suffix match example 4: " 297532059        S"
        """
        self.tx_regex['suffix'] = r"[0-9]*(?:(?: *(?:[A-Z]) *)?(?:[0-9]{2}/[0-9]{2}/[0-9]{2}.*)| +[A-Z] +.*)?$"
        # setup spacy
        self.nlp = spacy.load("en_core_web_sm")
        self.matcher = Matcher(self.nlp.vocab, validate=True)
        # Failed patterns I've tried: item_patterns = [[{"POS": "ADJ", "OP": "*"}, {"POS": {"IN": ["NOUN", "PROPN"]}, "OP": "+"}]]
        item_patterns = [[{"ENT_TYPE": {"NOT_IN": ["LAW", "DATE", "TIME", "PERCENT", "MONEY", "QUANTITY", "ORDINAL", "CARDINAL"]}, "OP": "+"}]]
        self.matcher.add("ITEM_PATTERN", item_patterns)

    def add_tx_record(self, date, desc, amount):
        self.tx_records['date'].append(date)
        self.tx_records['desc'].append(desc)
        self.tx_records['amount'].append(amount)

    def reader(self):
        with open(self.filepath) as file:
            for line in file:
                if line.split(',')[0].strip() == 'Transaction History':
                    break
           
            reader = csv.DictReader(file)
            date, cat, amount = None, None, None
            for row in reader:
                date, cat, amount = self.tx_parser(row, date, cat, amount)
            if amount:
                self.add_tx_record(date, cat, amount) # add the last transaction if the last row is the first row of a transaction
            return pd.DataFrame(self.tx_records)

    def tx_parser(self, row, prev_date: date, prev_cat: str, prev_amount: Decimal):
        try:
            # if amount_str is not empty, then the row is the first row of a transaction
            if (amount_str := '-'+row['Withdrawals (SGD)'] if (row['Withdrawals (SGD)']) else None) or (amount_str := row['Deposits (SGD)']):
                # Storing the first row
                tx_category = row['Description']
                amount = Decimal(amount_str.replace(',',''))
                # extract the date, month, year from the row and convert into datetime.date object
                match = re.search(r"([0-9]{2})/([0-9]{2})/([0-9]{4})", row['Transaction date'])
                if match:
                    tx_date = datetime(int(match.group(3)), int(match.group(2)), int(match.group(1)))
                # look back to previous row to see if the previous transaction has second row. 
                # (The second row of a transaction is the row without the amount)
                if prev_amount:
                    self.add_tx_record(prev_date, self.description_parser(prev_cat), prev_amount) # if no second row, use categroy for the item name
                return tx_date, tx_category, amount
            else:
                prev_detail = row['Description']
                self.add_tx_record(prev_date, self.description_parser(prev_detail), prev_amount) # if has second row, use the second row for the item name
                return None, None, None
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