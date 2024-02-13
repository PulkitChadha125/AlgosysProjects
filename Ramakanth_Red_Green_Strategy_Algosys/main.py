import pandas as pd
from pathlib import Path
import pyotp
import Zerodha_Integration
from datetime import datetime, timedelta, timezone
import math
result_dict={}

def custom_round(price, symbol):
    rounded_price = None

    if symbol == "NIFTY":
        last_two_digits = price % 100
        if last_two_digits < 25:
            rounded_price = (price // 100) * 100
        elif last_two_digits < 75:
            rounded_price = (price // 100) * 100 + 50
        else:
            rounded_price = (price // 100 + 1) * 100
            return rounded_price

    elif symbol == "BANKNIFTY":
        last_two_digits = price % 100
        if last_two_digits < 50:
            rounded_price = (price // 100) * 100
        else:
            rounded_price = (price // 100 + 1) * 100
        return rounded_price

    else:
        pass

    return rounded_price

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
                'Expiery': row['TradeExpiery'],
                'Expiery Type':row['Expiery Type'],
                'MaxProfitPerTrade': row['MaxProfitPerTrade'],
                'MaxLossPerTrade': row['MaxLossPerTrade'],
                'MaxProfitDay':row['MaxProfitDay'],
                'MaxLossDay':row['MaxLossDay'],
                'SymbolType': row['SymbolType'],
                'InitialTrade':None,
                'OPTION_CONTRACT_TYPE': row['OPTION CONTRACT TYPE'],
                'strike_distance': int(row['strike distance']),
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

def zerodhahistorical(original_date):
    # Convert the original date string to a datetime object
    original_date_obj = datetime.strptime(original_date, '%d-%m-%Y')

    # Format the date in the desired custom format "yyyy-mm-dd"
    custom_date_format = original_date_obj.strftime('%Y-%m-%d')

    return custom_date_format
def main_strategy ():
    global result_dict

    try:
        for symbol, params in result_dict.items():
            symbol_value = params['Symbol']
            if isinstance(symbol_value, str):
                Expiery = str(params['Expiery'])
                expiryhistorical = zerodhahistorical(Expiery)
                print(expiryhistorical)
                if params["SymbolType"] == "SPOT":
                    responce =Zerodha_Integration.combinedltp_spot()
                    niftyltp = responce['NSE:NIFTY 50']['last_price']
                    banknifty_ltp = responce['NSE:NIFTY BANK']['last_price']

                    if params['Symbol'] == "NIFTY":
                        token=256265
                        usedltp = niftyltp
                    if params['Symbol'] == "BANKNIFTY":
                        token =260105
                        usedltp=banknifty_ltp


                if params["SymbolType"] == "FUTURE":
                    if params['Symbol'] == "NIFTY":
                        token = 18288898

                    if params['Symbol'] == "BANKNIFTY":
                        token =18288642

                data=Zerodha_Integration.get_historical_data(Token=token, timeframe=params["Timeframe"],sym=params["Symbol"])
                last_three_rows = data.tail(3)

                # Extracting each row separately

                row2 = last_three_rows.iloc[1]

                time_value = row2.name
                open_value = float(row2['open'])
                high_value = float(row2['high'])
                low_value = float(row2['low'])
                close_value =float(row2['close'])
                volume_value = float(row2['volume'])

                if  params['InitialTrade']== None and close_value >open_value :
                    #initial buy take call

                    if params["OPTION_CONTRACT_TYPE"] == "ATM":
                        strike = custom_round(int(float(usedltp)), params['Symbol'])
                        callstrike = strike
                        expiryhistorical = zerodhahistorical(Expiery)
                        callsymbol=Zerodha_Integration.get_option_symbol(sym=params['Symbol'],exp= expiryhistorical,
                                                                            strike=callstrike,type= "CE")
                        print(callsymbol)

                    if params["OPTION_CONTRACT_TYPE"] == "ITM":
                        strike = custom_round(int(float(usedltp)), params['Symbol'])
                        callstrike = int(strike) - int(params["strike_distance"])
                        expiryhistorical = zerodhahistorical(Expiery)
                        callsymbol = Zerodha_Integration.get_option_symbol(sym=params['Symbol'],
                                                                              exp=expiryhistorical, strike=callstrike,
                                                                              type="CE")
                        print(callsymbol)

                    if params["OPTION_CONTRACT_TYPE"] == "OTM":
                        strike = custom_round(int(float(usedltp)), params['Symbol'])
                        callstrike = int(strike) + int(params["strike_distance"])
                        expiryhistorical = zerodhahistorical(Expiery)
                        callsymbol = Zerodha_Integration.get_option_symbol(sym=params['Symbol'],
                                                                              exp=expiryhistorical, strike=callstrike,
                                                                              type="CE")
                        print(callsymbol)


                    print(f"Initial Buy taken @ {params['Symbol']} @ {usedltp} ")
                    params["InitialTrade"]="BUY"

                if  params['InitialTrade'] == None and close_value < open_value:
                    # initial sell take PUT
                    print("code reached here" )
                    if params["OPTION_CONTRACT_TYPE"] == "ATM":
                        strike = custom_round(int(float(usedltp)), params['Symbol'])
                        putstrike = strike
                        expiryhistorical = zerodhahistorical(Expiery)
                        putsymbol = Zerodha_Integration.get_option_symbol(sym=params['Symbol'],exp= expiryhistorical, strike=putstrike, type= "PE")
                        print(putsymbol)


                    if params["OPTION_CONTRACT_TYPE"] == "ITM":
                        strike = custom_round(int(float(usedltp)), params['Symbol'])
                        putstrike = int(strike) + int(params["strike_distance"])
                        expiryhistorical = zerodhahistorical(Expiery)
                        putsymbol = Zerodha_Integration.get_option_symbol(sym=params['Symbol'], exp=expiryhistorical,
                                                                             strike=putstrike, type="PE")
                        print(putsymbol)

                    if params["OPTION_CONTRACT_TYPE"] == "OTM":
                        strike = custom_round(int(float(usedltp)), params['Symbol'])
                        putstrike = int(strike) - int(params["strike_distance"])
                        expiryhistorical = zerodhahistorical(Expiery)
                        putsymbol = Zerodha_Integration.get_option_symbol(sym=params['Symbol'], exp=expiryhistorical,
                                                                             strike=putstrike, type="PE")
                        print(putsymbol)

                    print(f"Initial Short taken @ {params['Symbol']} @ {usedltp} ")
                    params["InitialTrade"] = "SHORT"

                if params["InitialTrade"]== "BUY" and usedltp <low_value:
                    # take put
                    if params["OPTION_CONTRACT_TYPE"] == "ATM":
                        strike = custom_round(int(float(usedltp)), params['Symbol'])
                        putstrike = strike
                        expiryhistorical = zerodhahistorical(Expiery)
                        putsymbol = Zerodha_Integration.get_option_symbol(sym=params['Symbol'], exp=expiryhistorical,
                                                                             strike=putstrike, type="PE")
                        print(putsymbol)

                    if params["OPTION_CONTRACT_TYPE"] == "ITM":
                        strike = custom_round(int(float(usedltp)), params['Symbol'])
                        putstrike = int(strike) + int(params["strike_distance"])
                        expiryhistorical = zerodhahistorical(Expiery)
                        putsymbol = Zerodha_Integration.get_option_symbol(sym=params['Symbol'], exp=expiryhistorical,
                                                                             strike=putstrike, type="PE")
                        print(putsymbol)

                    if params["OPTION_CONTRACT_TYPE"] == "OTM":
                        strike = custom_round(int(float(usedltp)), params['Symbol'])
                        putstrike = int(strike) - int(params["strike_distance"])
                        expiryhistorical = zerodhahistorical(Expiery)
                        putsymbol = Zerodha_Integration.get_option_symbol(sym=params['Symbol'], exp=expiryhistorical,
                                                                             strike=putstrike, type="PE")
                        print(putsymbol)
                    params["InitialTrade"]="SHORT"
                    print(f"Closing previous call trade  @ {params['Symbol']} @ {usedltp} and opening put trade")

                if params["InitialTrade"]== "SHORT" and usedltp >high_value:
                    # take Call
                    if params["OPTION_CONTRACT_TYPE"] == "ATM":
                        strike = custom_round(int(float(usedltp)), params['Symbol'])
                        callstrike = strike
                        expiryhistorical = zerodhahistorical(Expiery)
                        callsymbol = Zerodha_Integration.get_option_symbol(sym=params['Symbol'],
                                                                              exp=expiryhistorical, strike=callstrike,
                                                                              type="CE")
                        print(callsymbol)

                    if params["OPTION_CONTRACT_TYPE"] == "ITM":
                        strike = custom_round(int(float(usedltp)), params['Symbol'])
                        callstrike = int(strike) - int(params["strike_distance"])
                        expiryhistorical = zerodhahistorical(Expiery)
                        callsymbol = Zerodha_Integration.get_option_symbol(sym=params['Symbol'],
                                                                              exp=expiryhistorical, strike=callstrike,
                                                                              type="CE")
                        print(callsymbol)

                    if params["OPTION_CONTRACT_TYPE"] == "OTM":
                        strike = custom_round(int(float(usedltp)), params['Symbol'])
                        callstrike = int(strike) + int(params["strike_distance"])
                        expiryhistorical = zerodhahistorical(Expiery)
                        callsymbol = Zerodha_Integration.get_option_symbol(sym=params['Symbol'],
                                                                              exp=expiryhistorical, strike=callstrike,
                                                                              type="CE")
                        print(callsymbol)

                    params["InitialTrade"] = "BUY"
                    print(f"Closing previous put trade  @ {params['Symbol']} @ {usedltp} and opening call trade")








    except Exception as e:
        print("Error happened in Main strategy loop: ", str(e))



main_strategy ()
