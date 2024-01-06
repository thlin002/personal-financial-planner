from datetime import date, timedelta
import pandas as pd
from decimal import *
from abc import ABC, abstractmethod
import sys
import re
import csv
import sqlite3

# Book and its inherited classes are used to store Future CF as opposed to Past CF defined in Bank_records, 
class Table(ABC):
    sheet_cols = {}

    @property
    def filepath(self):
        return self._filepath
    
    @filepath.setter
    def filepath(self, filepath):
        # might need to add some checking method for filepath format.
        self._filepath = filepath

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.df = pd.read_excel(pd.ExcelFile(self.filepath), index_col=False, sheet_name=list(self.sheet_cols.keys()))

    def create_missing_sheets(self, writer, sheet_name, cols):
        for sheet_name in self.sheet_cols:  
            if not sheet_name in self.df:
                # create a new empty sheet
                with pd.ExcelWriter(self.filepath) as writer:
                    Future_CF.create_new_sheet(writer, sheet_name, self.sheet_cols[sheet_name]) 

    # static method, no 'self' argument
    def create_new_sheet(writer, sheet_name, cols):
        pd.DataFrame(columns=cols).to_excel(writer, sheet_name)

    def __del__(self):
        pass

    def __str__(self):
        pass

class Future_CF(Table):
    sheet_cols = {
                'one_time_expense': ['name', 'amount', 'date'],
                'recurring_expense': ['name', 'amount', 'period'],
                'one_time_income': ['name', 'amount', 'date'],
                'recurring_income': ['name', 'amount', 'period']
    }
    def __init__(self, filepath: str):
        try:
            # read the xls file as self.xls and store it into pandas dataframe self.df
            super().__init__(filepath)
            with pd.ExcelWriter(filepath, mode='a') as writer:
                for sheet_name in self.sheet_cols:  
                    if not sheet_name in self.df:
                        print(f'Sheet {sheet_name} not found...')
                        print(f'Create new sheet...')
                        # create a new empty sheet
                        Future_CF.create_new_sheet(writer, sheet_name, self.sheet_cols[sheet_name]) 
        except FileNotFoundError:
            # create a new empty Future_cashflows excel file
            with pd.ExcelFile(self.filepath) as writer:
                for sheet_name in self.sheet_cols:
                    Future_CF.create_new_sheet(writer, sheet_name, self.sheet_cols[sheet_name])
            print(f'File {self.filepath} not found...')
            print('Create new file...')
            print('Ending the program...')
            sys.exit()

class Capital(Table):
    sheet_cols = {
            'current_deposit': ['account', 'amount'],
            'time_deposit': ['account', 'amount', 'date_of_maturity'],
            'bonds': ['account', 'amount', 'date_of_maturity'],
            'stocks': ['account', 'amount']
    }
    def __init__(self, filepath: str, savings = Decimal(0), min_thresh = Decimal(0)):
        try:
            super().__init__(filepath)
            for sheet_name in self.sheet_cols:  
                if not sheet_name in self.df:
                    # create a new empty sheet
                    with pd.ExcelWriter(filepath) as writer:
                        Future_CF.create_new_sheet(writer, sheet_name, self.sheet_cols[sheet_name]) 
        except FileNotFoundError:
            with pd.ExcelFile(self.filepath) as writer:
                Future_CF.create_new_sheet(writer, sheet_name, self.sheet_cols[sheet_name])

# end of Book and its inherited classes