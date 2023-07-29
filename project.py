import json
import pandas as pd
import requests
from datetime import date, timedelta

def main():
    # print(get_bond_yields())

    book_onetime = book('onetime.csv')
    book_recurring = recurring_book('recurring.csv')
    book_onetime.book_modifier()
    book_recurring.book_modifier()
    #print(get_bond_yields())

class book:
    def __init__(self, filepath):
        self.filepath = filepath
        self.columns = ['num', 'date']
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

    def book_modifier(self):
        """
            A interface for user to edit the book items

            :return: A Dataframe that contains the update bookdata
            :rtype: pandas DataFrame object
        """
        items = self.bookdata.to_dict()
        print(pd.DataFrame.from_records(items, columns=self.columns))
        while True:
            while not (option := input("Input 'a' to add and 'd' to delete\nInput 'exit' to end\nInput: ").strip().lower()) in ('a', 'd', 'exit'):
                pass
            if option == 'exit':
                break

            if (name := input("Name: ").strip().lower()).isalnum():
                match option:
                    case "a":
                        items[self.columns[0]][name] = self.get_float()
                        items[self.columns[1]][name] = self.get_time()
                    case "d":
                        try:
                            items[self.columns[0]].pop(name)
                            items[self.columns[1]].pop(name)
                        except KeyError:
                            print("Item doesn't exist")
            print(pd.DataFrame.from_records(items))
            
        self.bookdata = pd.DataFrame.from_records(items)

    def get_float(self):
        while True:
            try:
                num = float(input("Number(outflow -, inflow +): "))
                break
            except ValueError:
                print("Invalid floating point number")
        return num

    def get_time(self):
        while True:
            try:
                d = date.fromisoformat(input("Date YYYY-MM-DD: "))
                break
            except ValueError:
                print("Invalid date format")   
        return d
        
class recurring_book(book):
    def __init__(self, filepath):
        self.filepath = filepath
        self.columns = ['num', 'freq']
        try:
            self.bookdata = pd.read_csv(self.filepath, index_col=0)
        # catch FileNotFoundError and pandas.errors.EmptyDataError
        except Exception:
            self.bookdata = pd.DataFrame(columns=self.columns)
    
    def get_time(self):
        while True:
            try:
                d = timedelta(days=int(input("Frequency(days): ")))
                break
            except ValueError:
                print("Invalid date format")   
        return d

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
