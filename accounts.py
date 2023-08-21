from datetime import date, timedelta
import pandas as pd
from decimal import *
from abc import ABC, abstractmethod
import re


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

    def __init__(self, filepath: str):
        self.filepath = filepath
        self._options = ['u', 'exit']
        # Inherited class could append more get_col functions to the list in the inherited class if needed
        self.get_col_funcs = [self.get_col1, self.get_col2]
        # Read the csv file if it exists and set the first column as index
        self.bookdf = pd.read_csv(self.filepath, index_col=0)
            
    def __del__(self):
        # Write the bookdf to the csv file, with the first column as index
        self.bookdf.to_csv(self.filepath)

    def __str__(self):
        return self.bookdf.to_string()

    def get_col1(self) -> Decimal:
        return Decimal(input("Amount, negative for expense/debt: "))

    @abstractmethod
    def get_col2(self):
        pass

    def init_bookdf(self):
        self.bookdf = pd.DataFrame(columns=self.columns)

    def usr_book_writer(self) -> None:
        # items is a dict of dict converted from the bookdf, which is a DataFrame
        while True:
            print(self.bookdf, end='\n\n')

            # loop until user input the correct option
            while not (option := input(f"Input 'a' to add, 'u' to update, 'd' to delete, and 'exit' to end.\nAvailable options {self._options}, Option: ").strip().lower()) in self._options:
                pass

            if option == 'exit':
                break
            
            if (name := input("Name: ").strip().lower()).isprintable():
                try:
                    match option:
                        case "a":
                            # construct a new row from the user input 
                            data = {name: [func() for func in self.get_col_funcs]}
                            new_row = pd.DataFrame.from_dict(data, orient='index', columns=self.columns)
                            # append the new row to the bookdf
                            self.bookdf = pd.concat([self.bookdf, new_row], verify_integrity=True)
                        case "u":
                            # if the name is in the index, update the row
                            if name in self.bookdf.index:
                                self.bookdf.loc[name] = [func() for func in self.get_col_funcs]
                        case "d":
                            self.bookdf.drop(name, inplace=True)
                except KeyError as e:
                    print(e, end=', try again\n\n')
                except ValueError as e:
                    print(e, end=', try again\n\n')
                except InvalidOperation as e:
                    print(e, end=', try again\n\n')

class Non_recurring_CF(Book):
    def __init__(self, filepath: str):
        self.columns = ['amount', 'date']
        try:
            super().__init__(filepath)
            self._options += ['a', 'd']
        except FileNotFoundError:
            self.init_bookdf()
        
    def get_col2(self) -> date:
        return date.fromisoformat(input("Date YYYY-MM-DD: "))

class Recurring_CF(Book):
    def __init__(self, filepath: str, spending = Decimal(0), income = Decimal(0)):
        self.columns = ['amount', 'freq']
        try:
            super().__init__(filepath)
        except FileNotFoundError:
            self.init_bookdf(spending, income)
    
    def update(self, spending:  Decimal, income: Decimal):
        ...
        #self.bookdf.loc['spending'] = spending
        #self.bookdf.loc['income'] = income

    def get_col2(self) -> timedelta:
        matches = re.search(r"([0-9]+)/([0-9]+)/([0-9]+)", int(input("Years/Month/Days").strip()))
        years, months, days = matches.group(1), matches.group(2), matches.group(3)
        return pd.DateOffset(years=years, months=months, days=days)
    
    def init_bookdf(self, spending: Decimal, income: Decimal):
        data = {
            'spending': [spending, pd.DateOffset(months=1)],
            'income': [income, pd.DateOffset(months=1)]
            }
        self.bookdf = pd.DataFrame.from_dict(data, orient='index', columns=self.columns)
        print(self.bookdf)

    def update_spending(self, spending: Decimal) -> None:
        self.bookdf.loc["spending"] = spending

class Savings(Book):
    def __init__(self, filepath: str, savings = Decimal(0), min_thresh = Decimal(0)):
        self.columns = ['savings', 'min_thresh']
        try:
            super().__init__(filepath)
        except FileNotFoundError:
            self.init_bookdf(savings, min_thresh)
    
    def init_bookdf(self, savings: Decimal, min_thresh: Decimal):
        data = {
            'savings': [savings, min_thresh]
            }
        self.bookdf = pd.DataFrame.from_dict(data, orient='index', columns=self.columns)
        print(self.bookdf)

    def get_col2(self) -> Decimal:
        return Decimal(input("Min threshold: "))

# end of Book and its inherited classes