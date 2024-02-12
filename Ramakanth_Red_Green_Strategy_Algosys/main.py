import pandas as pd
from pathlib import Path
import pyotp
import Zerodha_Integration
from datetime import datetime, timedelta, timezone

result_dict={}

def write_to_order_logs(message):
    with open('OrderLog.txt', 'a') as file:  # Open the file in append mode
        file.write(message + '\n')


def delete_file_contents(file_name):
    try:
        # Open the file in write mode, which truncates it (deletes contents)
        with open(file_name, 'w') as file:
            file.truncate(0)
        print(f"Contents of {file_name} have been deleted.")
    except FileNotFoundError:
        print(f"File {file_name} not found.")
    except Exception as e:
        print(f"An error occurred: {str(e)}")


def get_zerodha_credentials():
    delete_file_contents("OrderLog.txt")
    credentials = {}
    try:
        df = pd.read_csv('ZerodhaCredentials.csv')
        for index, row in df.iterrows():
            title = row['Title']
            value = row['Value']
            credentials[title] = value
    except pd.errors.EmptyDataError:
        print("The CSV file is empty or has no data.")
    except FileNotFoundError:
        print("The CSV file was not found.")
    except Exception as e:
        print("An error occurred while reading the CSV file:", str(e))

    return credentials

def get_user_settings():
    global result_dict
    try:
        csv_path = 'TradeSettings.csv'
        df = pd.read_csv(csv_path)
        df.columns = df.columns.str.strip()
        result_dict = {}

        for index, row in df.iterrows():
            # Create a nested dictionary for each symbol
            symbol_dict = {
                'Symbol': row['Symbol'],
                'Timeframe': row['Timeframe'],
                'Quantity':row['Quantity'],
                'Expiery': row['Expiery'],
                'Expiery Type':row['Expiery Type'],
                'MaxProfitPerTrade': row['MaxProfitPerTrade'],
                'MaxLossPerTrade': row['MaxLossPerTrade'],
                'MaxProfitDay':row['MaxProfitDay'],
                'MaxLossDay':row['MaxLossDay'],
                'SymbolType': row['SymbolType'],
            }
            result_dict[row['Symbol']] = symbol_dict
        print(result_dict)
    except Exception as e:
        print("Error happened in fetching symbol", str(e))

get_user_settings()
credentials_dict = get_zerodha_credentials()
user_id = credentials_dict.get('ZerodhaUserId')  # Login Id
password = credentials_dict.get('ZerodhaPassword')  # Login password
fakey = credentials_dict.get('Zerodha2fa')
StartTime=credentials_dict.get('StartTime')
Stoptime=credentials_dict.get('Stoptime')

twofa = pyotp.TOTP(fakey)
twofa = twofa.now()
Zerodha_Integration.login(user_id, password, twofa)

Zerodha_Integration.get_all_instruments()


def token(symbol,instrument_type,segment,exchange,symboltype,exp):
    if symboltype=="SPOT":
        df = pd.read_csv('Instruments.csv')
        instrument_token = None  # Initialize the instrument token as None
        while instrument_token is None:
            selected_row = df[(df['tradingsymbol'] == symbol) &
                              (df['exchange'].astype(str) == exchange)&
                              (df['segment'].astype(str) == segment) &
                              ( df['instrument_type'].astype(str) == instrument_type) ]
            print(selected_row)
            if not selected_row.empty:
                instrument_token = selected_row['instrument_token'].values[0]
            else:
                print("Instrument token not found. Retrying...")



    if symboltype=="FUTURE":
        df = pd.read_csv('Instruments.csv')
        instrument_token = None

        while instrument_token is None:
            selected_row = df[(df['name'] == symbol) &
                              (df['exchange'].astype(str) == exchange) &
                              (df['segment'].astype(str) == segment) &
                              (df['instrument_type'].astype(str) == instrument_type)&
                              (df['expiry'].astype(str) == exp)]

            if not selected_row.empty:
                instrument_token = selected_row['instrument_token'].values[0]
            else:
                print("Instrument token not found. Retrying...")

    return instrument_token




def main_strategy ():
    global result_dict

    try:
        for symbol, params in result_dict.items():
            Expiery = str(params['Expiery'])
            print(Expiery)
            if params["SymbolType"] == "SPOT":
                if params['Symbol'] == "NIFTY":
                    token=256265
                if params['Symbol'] == "BANKNIFTY":
                    token =260105


            if params["SymbolType"] == "FUTURE":
                if params['Symbol'] == "NIFTY":
                    token = 18288898
                if params['Symbol'] == "BANKNIFTY":
                    token =18288642

            data=Zerodha_Integration.get_historical_data(Token=token, timeframe=params["Timeframe"],sym=params["Symbol"])
            last_three_rows = data.tail(3)

            # Extracting each row separately
            row1 = last_three_rows.iloc[0]
            row2 = last_three_rows.iloc[1]
            row3 = last_three_rows.iloc[2]
            print("row1: ",row1)
            print("row2: ",row2)
            print("row3: ",row3)


    except Exception as e:
        print("Error happened in Main strategy loop: ", str(e))



main_strategy ()
