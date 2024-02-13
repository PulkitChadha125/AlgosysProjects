import requests



def place_getalert(symbol,direction,price,code,qty):
    URL='http://trade.algosys.co.in/TDAlgoAPI/api/ProcessTask/PostStockRateWithParams'
    params1 = dict(inSymbol= symbol,
            type=direction,
            stopLoss=0,
           price= price,
            takeProfit= 0,
           stopPrice=0,
            strat_code=code,
            quantityInAlert = qty)

    r = requests.get(URL, params=params1)
    return r