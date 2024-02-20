import time
import traceback
import pandas as pd
from pathlib import Path
import pyotp
import Zerodha_Integration,AlgosysIntegration
from datetime import datetime, timedelta, timezone
import math
result_dict={}
closed_pnl=[]
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
next_specific_part_time=datetime.now()
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
                'Target': row['Target'],
                'Stoploss': row['Stoploss'],
                'MaxProfitDay':row['MaxProfitDay'],
                'MaxLossDay':row['MaxLossDay'],
                'SymbolType': row['SymbolType'],
                'TSL_AFTER': row['TSL_AFTER'],
                'TSL_BY': row['TSL_BY'],
                'InitialTrade':None,
                'OPTION_CONTRACT_TYPE': row['OPTION CONTRACT TYPE'],
                'strike_distance': int(row['strike distance']),
                'zerodha_symbol':None,
                'algosys_symbol':None,
                'buy_price':None,
                'TargetValue':None,
                'StoplossValue': None,
                'tsl_start':None,
                'tsl_by':None,
                'USETSL':row['USETSL'],
                'secondrytradebuytime':None,
                'secondrytradeselltime': None,
                "open":0,
                "high": 0,
                "low": 0,
                "close": 0,
                "time_value":None,
                "runtime":datetime.now(),
                "cool" : row['Sync'],
                "exit_price":None,
                "pnl_current_trade_close":None

            }
            result_dict[row['Symbol']] = symbol_dict
        print("result_dict: ",result_dict)
    except Exception as e:
        print("Error happened in fetching symbol", str(e))

get_user_settings()
credentials_dict = get_zerodha_credentials()
user_id = credentials_dict.get('ZerodhaUserId')  # Login Id
password = credentials_dict.get('ZerodhaPassword')  # Login password
fakey = credentials_dict.get('Zerodha2fa')

strategycode= credentials_dict.get('StrategyCode')
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



def round_down_to_interval(dt, interval_minutes):
    remainder = dt.minute % interval_minutes
    minutes_to_current_boundary = remainder

    rounded_dt = dt - timedelta(minutes=minutes_to_current_boundary)

    rounded_dt = rounded_dt.replace(second=0, microsecond=0)

    return rounded_dt

def determine_min(minstr):
    min=0
    if minstr =="minute":
        min=1
    if minstr =="5minute":
        min=5
    if minstr =="15minute":
        min=15
    if minstr =="30minute":
        min=30

    return min






def main_strategy ():
    global result_dict,next_specific_part_time

    strategycode = credentials_dict.get('StrategyCode')
    try:
        for symbol, params in result_dict.items():
            symbol_value = params['Symbol']

            timestamp = datetime.now()
            timestamp = timestamp.strftime("%d/%m/%Y %H:%M:%S")
            if isinstance(symbol_value, str):
                Expiery = str(params['Expiery'])
                expiryhistorical = zerodhahistorical(Expiery)

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

                if datetime.now() >= params["runtime"]:
                    try:
                        if params["cool"] ==True:
                            time.sleep(7)
                        data=Zerodha_Integration.get_historical_data(Token=token, timeframe=params["Timeframe"],sym=params["Symbol"])
                        last_three_rows = data.tail(3)
                        row2 = last_three_rows.iloc[1]
                        row1 = last_three_rows.iloc[2]
                        time_value_current=row1.name
                        time_value = row2.name
                        computer_time=round_down_to_interval(datetime.now(), determine_min(params['Timeframe']))
                        open_value = float(row2['open'])
                        high_value = float(row2['high'])
                        low_value = float(row2['low'])
                        close_value = float(row2['close'])
                        volume_value = float(row2['volume'])
                        params["open"]= open_value
                        params["high"]= high_value
                        params["low"]= low_value
                        params["close"]= close_value
                        params["time_value"]= time_value
                        print(f"{params['Symbol']}= open: {params['open']}")
                        print(f"{params['Symbol']}= close: {params['close']}")
                        print("Candle time_value: ", params["time_value"])
                        next_specific_part_time = datetime.now() + timedelta(seconds=determine_min(params["Timeframe"])* 60)
                        next_specific_part_time=round_down_to_interval(next_specific_part_time,  determine_min(params["Timeframe"]) )
                        print("Next datafetch time = ",next_specific_part_time)
                        params['runtime'] = next_specific_part_time

                    except Exception as e:
                        print("Error happened in Histry data fetching  strategy loop: ", str(e))
                        time.sleep(3)
                        data = Zerodha_Integration.get_historical_data(Token=token, timeframe=params["Timeframe"],
                                                                       sym=params["Symbol"])
                        last_three_rows = data.tail(3)
                        row2 = last_three_rows.iloc[1]
                        row1 = last_three_rows.iloc[2]
                        time_value_current = row1.name
                        time_value = row2.name
                        computer_time = round_down_to_interval(datetime.now(), determine_min(params['Timeframe']))
                        open_value = float(row2['open'])
                        high_value = float(row2['high'])
                        low_value = float(row2['low'])
                        close_value = float(row2['close'])
                        volume_value = float(row2['volume'])
                        params["open"] = open_value
                        params["high"] = high_value
                        params["low"] = low_value
                        params["close"] = close_value
                        params["time_value"] = time_value
                        print(f"{params['Symbol']}= open: {params['open']}")
                        print(f"{params['Symbol']}= close: {params['close']}")
                        print("Candle time_value: ", params["time_value"])
                        next_specific_part_time = datetime.now() + timedelta(
                            seconds=determine_min(params["Timeframe"]) * 60)
                        next_specific_part_time = round_down_to_interval(next_specific_part_time,
                                                                         determine_min(params["Timeframe"]))
                        print("Next datafetch time = ", next_specific_part_time)
                        params['runtime'] =next_specific_part_time


                open_value = float(params["open"])
                high_value =float(params["high"])
                low_value =float(params["low"])
                close_value = float(params["close"])
                time_value= params["time_value"]



                if  (
                        params['InitialTrade'] in [None, "SHORT"] and
                        close_value > open_value and close_value>0 and open_value>0 and
                        params['secondrytradeselltime'] != time_value
                ):

                    if params['InitialTrade'] =="SHORT":
                        orderlog = f" {timestamp}exit previous trade {params['zerodha_symbol']}"
                        print(orderlog)
                        write_to_order_logs(orderlog)
                        exit_price = Zerodha_Integration.get_ltp_option(params['zerodha_symbol'])
                        params["exit_price"]= exit_price
                        params["pnl_current_trade_close"]= params["exit_price"]- params['buy_price']
                        params["pnl_current_trade_close"]=params["pnl_current_trade_close"]*params["Quantity"]
                        closed_pnl.append(params["pnl_current_trade_close"])
                        AlgosysIntegration.place_getalert(symbol=params['algosys_symbol'], direction="LX",
                                                          price=exit_price,
                                                          code=strategycode, qty=params["Quantity"])


                    params["InitialTrade"] = "BUY"

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

                    buyprice_ce= Zerodha_Integration.get_ltp_option(callsymbol)
                    tgt=buyprice_ce+ float(params['Target'])
                    sll=buyprice_ce-float(params['Stoploss'])
                    params['TargetValue'] = tgt
                    params['StoplossValue'] = sll


                    algosyssymbol="NSE:"+str(callsymbol)
                    params['zerodha_symbol'] = callsymbol
                    params['algosys_symbol'] = algosyssymbol
                    params['buy_price'] = buyprice_ce
                    params['tsl_start'] = params['buy_price'] + params['TSL_AFTER']
                    # LE,LX
                    AlgosysIntegration.place_getalert(symbol=algosyssymbol, direction="LE", price=buyprice_ce, code=strategycode, qty=params["Quantity"])
                    orderlog=f"{timestamp} Initial Buy taken previous candle green  open =  {open_value} , close={close_value} @ {params['Symbol']} @ {usedltp} @ CE contract ={params['zerodha_symbol']} @ price {params['buy_price']} @ previous candle time {time_value}"
                    print(orderlog)
                    write_to_order_logs(orderlog)




                if  (
                        params['InitialTrade'] in [None, "BUY"] and
                        close_value < open_value and  close_value>0 and open_value>0 and
                        params['secondrytradebuytime'] != time_value
                ):
                    # initial sell take PUT


                    if params['InitialTrade'] =="BUY":
                        orderlog = f" {timestamp}exit previous trade {params['zerodha_symbol']}"
                        print(orderlog)
                        write_to_order_logs(orderlog)
                        exit_price = Zerodha_Integration.get_ltp_option(params['zerodha_symbol'])
                        params["exit_price"] = exit_price
                        params["pnl_current_trade_close"] = params["exit_price"] - params['buy_price']
                        params["pnl_current_trade_close"] = params["pnl_current_trade_close"] * params["Quantity"]
                        closed_pnl.append(params["pnl_current_trade_close"])
                        AlgosysIntegration.place_getalert(symbol=params['algosys_symbol'], direction="LX",
                                                          price=exit_price,
                                                          code=strategycode, qty=params["Quantity"])


                    params["InitialTrade"] = "SHORT"


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

                    buyprice_pe = Zerodha_Integration.get_ltp_option(putsymbol)
                    tgt = buyprice_pe + float(params['Target'])
                    sll = buyprice_pe - float(params['Stoploss'])
                    params['TargetValue'] = tgt
                    params['StoplossValue'] = sll
                    algosyssymbol = "NSE:" + str(putsymbol)
                    params['zerodha_symbol'] = putsymbol
                    params['algosys_symbol'] = algosyssymbol
                    params['buy_price'] = buyprice_pe
                    params['tsl_start'] = params['buy_price'] + params['TSL_AFTER']
                    # LE,LX
                    AlgosysIntegration.place_getalert(symbol=algosyssymbol, direction="LE", price=buyprice_pe,
                                                      code=strategycode, qty=params["Quantity"])
                    orderlog = f" {timestamp} Initial Buy taken previous candle red ,open =  {open_value} , close={close_value} @ {params['Symbol']} @ {usedltp} @ PE contract ={params['zerodha_symbol']} @ price {params['buy_price'] } @ previous candle time {time_value} "
                    print(orderlog)
                    write_to_order_logs(orderlog)




                if (
                        params["InitialTrade"]== "BUY" and
                        usedltp < low_value and low_value>0
                ):
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
                    params['secondrytradebuytime']= None
                    params['secondrytradeselltime']= time_value

                    exit_price=Zerodha_Integration.get_ltp_option(params['zerodha_symbol'])
                    params["exit_price"] = exit_price
                    params["pnl_current_trade_close"] = params["exit_price"] - params['buy_price']
                    params["pnl_current_trade_close"] = params["pnl_current_trade_close"] * params["Quantity"]
                    closed_pnl.append(params["pnl_current_trade_close"])
                    AlgosysIntegration.place_getalert(symbol=params['algosys_symbol'], direction="LX", price=exit_price,
                                                      code=strategycode, qty=params["Quantity"])
                    params['zerodha_symbol'] = putsymbol
                    params['algosys_symbol'] = "NSE:"+str(putsymbol)
                    buyprice_pe=Zerodha_Integration.get_ltp_option(params['zerodha_symbol'])
                    tgt = buyprice_pe + float(params['Target'])
                    sll = buyprice_pe - float(params['Stoploss'])
                    params['TargetValue'] = tgt
                    params['StoplossValue'] = sll
                    params['buy_price'] = buyprice_pe
                    params['tsl_start']= params['buy_price']+params['TSL_AFTER']

                    AlgosysIntegration.place_getalert(symbol=params['algosys_symbol'] , direction="LE", price=params['buy_price'] ,
                                                      code=strategycode, qty=params["Quantity"])

                    # its buy exit and sell entry
                    orderlog = f"{timestamp} {params['Symbol']}: Ltp less than previous candle low : {low_value} Closing previous call trade and opening put trade {params['zerodha_symbol']} @ {params['buy_price'] }"
                    print(orderlog)
                    write_to_order_logs(orderlog)


                if (
                        params["InitialTrade"]== "SHORT" and
                        usedltp >high_value  and high_value>0
                ):
                    # take Call
                    print("main loop buy is faulty")


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
                    params['secondrytradebuytime'] = time_value
                    params['secondrytradeselltime'] = None

                    exit_price = Zerodha_Integration.get_ltp_option(params['zerodha_symbol'])
                    params["exit_price"] = exit_price
                    params["pnl_current_trade_close"] = params["exit_price"] - params['buy_price']
                    params["pnl_current_trade_close"] = params["pnl_current_trade_close"] * params["Quantity"]
                    closed_pnl.append(params["pnl_current_trade_close"])
                    AlgosysIntegration.place_getalert(symbol=params['algosys_symbol'], direction="LX", price=exit_price,
                                                      code=strategycode, qty=params["Quantity"])
                    params['zerodha_symbol'] = callsymbol
                    params['algosys_symbol'] = "NSE:" + str(callsymbol)
                    buyprice_ce = Zerodha_Integration.get_ltp_option(params['zerodha_symbol'])
                    tgt = buyprice_ce + float(params['Target'])
                    sll = buyprice_ce - float(params['Stoploss'])
                    params['TargetValue'] = tgt
                    params['StoplossValue'] = sll
                    params['buy_price'] = buyprice_ce
                    params['tsl_start'] = params['buy_price'] + params['TSL_AFTER']

                    AlgosysIntegration.place_getalert(symbol=params['algosys_symbol'], direction="LE",
                                                      price=params['buy_price'],
                                                      code=strategycode, qty=params["Quantity"])
                    orderlog = f"{timestamp} {params['Symbol']}:  Ltp: {usedltp} greater than previous candle high {high_value} Closing previous put trade and opening call trade {params['zerodha_symbol']} @ {params['buy_price'] }"
                    print(orderlog)
                    write_to_order_logs(orderlog)



    #  target and stoploss calculation

                print(f"{timestamp} {params['zerodha_symbol']} :{Zerodha_Integration.get_ltp_option(params['zerodha_symbol'])}")


                if (
                        params["InitialTrade"] == "BUY" and
                        params['TargetValue']>0 and
                        params['Target']>0 and
                        float(Zerodha_Integration.get_ltp_option(params['zerodha_symbol'])) >= float(params['TargetValue'])
                ):
                    exit_price=Zerodha_Integration.get_ltp_option(params['zerodha_symbol'])
                    params["exit_price"] = exit_price
                    params["pnl_current_trade_close"] = params["exit_price"] - params['buy_price']
                    params["pnl_current_trade_close"] = params["pnl_current_trade_close"] * params["Quantity"]
                    closed_pnl.append(params["pnl_current_trade_close"])
                    AlgosysIntegration.place_getalert(symbol=params['algosys_symbol'], direction="LX", price=exit_price,
                                                      code=strategycode, qty=params["Quantity"])
                    orderlog=f"{timestamp} {params['Symbol']}: Target executed for  {params['zerodha_symbol']} @ {exit_price}"
                    print(orderlog)
                    write_to_order_logs(orderlog)
                    params['StoplossValue'] = 0
                    params['Stoploss'] = 0
                    params['TargetValue'] = 0
                    params['Target'] = 0


                if (
                        params["InitialTrade"] == "BUY" and
                        params["StoplossValue"]>0 and
                        params["Stoploss"]>0 and
                        float(Zerodha_Integration.get_ltp_option(params['zerodha_symbol'])) <= float(params['StoplossValue'])
                ):
                    exit_price = Zerodha_Integration.get_ltp_option(params['zerodha_symbol'])
                    params["exit_price"] = exit_price
                    params["pnl_current_trade_close"] = params["exit_price"] - params['buy_price']
                    params["pnl_current_trade_close"] = params["pnl_current_trade_close"] * params["Quantity"]
                    closed_pnl.append(params["pnl_current_trade_close"])
                    AlgosysIntegration.place_getalert(symbol=params['algosys_symbol'], direction="LX", price=exit_price,
                                                      code=strategycode, qty=params["Quantity"])
                    orderlog = f"{timestamp} {params['Symbol']}: Stoploss executed for  {params['zerodha_symbol']} @ {exit_price}"
                    print(orderlog)
                    write_to_order_logs(orderlog)
                    params['StoplossValue'] = 0
                    params['Stoploss'] = 0
                    params['TargetValue'] = 0
                    params['Target'] = 0

                if (
                        params["InitialTrade"] == "SHORT" and
                        params['TargetValue'] > 0 and
                        params['Target'] > 0 and
                        float(Zerodha_Integration.get_ltp_option(params['zerodha_symbol'])) >= float(params['TargetValue'])
                ):
                    exit_price = Zerodha_Integration.get_ltp_option(params['zerodha_symbol'])
                    params["exit_price"] = exit_price
                    params["pnl_current_trade_close"] = params["exit_price"] - params['buy_price']
                    params["pnl_current_trade_close"] = params["pnl_current_trade_close"] * params["Quantity"]
                    closed_pnl.append(params["pnl_current_trade_close"])
                    AlgosysIntegration.place_getalert(symbol=params['algosys_symbol'], direction="LX", price=exit_price,
                                                      code=strategycode, qty=params["Quantity"])
                    orderlog = f"{timestamp} {params['Symbol']}: Target executed for  {params['zerodha_symbol']} @ {exit_price}"
                    print(orderlog)
                    write_to_order_logs(orderlog)
                    params['StoplossValue'] = 0
                    params['Stoploss'] = 0
                    params['TargetValue'] = 0
                    params['Target'] = 0

                if (
                        params["InitialTrade"] == "SHORT" and
                        params["StoplossValue"] > 0 and
                        params["Stoploss"] > 0 and
                        float(Zerodha_Integration.get_ltp_option(params['zerodha_symbol'])) <= float(params['TargetValue'])
                ):
                    exit_price = Zerodha_Integration.get_ltp_option(params['zerodha_symbol'])
                    params["exit_price"] = exit_price
                    params["pnl_current_trade_close"] = params["exit_price"] - params['buy_price']
                    params["pnl_current_trade_close"] = params["pnl_current_trade_close"] * params["Quantity"]
                    closed_pnl.append(params["pnl_current_trade_close"])
                    AlgosysIntegration.place_getalert(symbol=params['algosys_symbol'], direction="LX", price=exit_price,
                                                      code=strategycode, qty=params["Quantity"])
                    orderlog = f"{timestamp} {params['Symbol']}: Stoploss executed for  {params['zerodha_symbol']} @ {exit_price}"
                    print(orderlog)
                    write_to_order_logs(orderlog)
                    params['StoplossValue'] = 0
                    params['Stoploss'] = 0
                    params['TargetValue'] = 0
                    params['Target'] = 0

    #             booked pnl
                if len(closed_pnl) > 1:
                    total_pnl = sum(closed_pnl)
                    print(f"{timestamp} Total PnL:{total_pnl}" )


    #             running pnl current trade
                if  params['buy_price']>0:
                    pass

    #             tsl implementstaion

                if (
                        float(Zerodha_Integration.get_ltp_option(params['zerodha_symbol'])) >= params['tsl_start'] and
                        params["USETSL"]=="TRUE" and  params["InitialTrade"] is not None
                ):
                    params['StoplossValue'] =float(Zerodha_Integration.get_ltp_option(params['zerodha_symbol']))-float(params['TSL_BY'])
                    params['tsl_start']=float(Zerodha_Integration.get_ltp_option(params['zerodha_symbol']))+float(params['TSL_BY'])
                    orderlog = f"{timestamp} {params['Symbol']}: Tsl executed for {params['zerodha_symbol']} new stoploss {params['StoplossValue']}"
                    print(orderlog)
                    write_to_order_logs(orderlog)








    except Exception as e:
        print("Error happened in Main strategy loop: ", str(e))
        # traceback.print_exc()


while True :

    StartTime = credentials_dict.get('StartTime')
    Stoptime = credentials_dict.get('Stoptime')
    start_time = datetime.strptime(StartTime, '%H:%M').time()
    stop_time = datetime.strptime(Stoptime, '%H:%M').time()

    now = datetime.now().time()
    if now >= start_time and now < stop_time:
        main_strategy ()
