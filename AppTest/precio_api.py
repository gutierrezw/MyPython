from ibapi.client import *
from ibapi.wrapper import *
import time
from pprint import pprint

class TestApp(EClient, EWrapper):
    def __init__(self):
        EClient.__init__(self, self)

    def error(self, reqId, errorCode, errorString,  advancedOrderRejectJson):
        if errorCode not in(2104, 2106, 2158):
            print("Error: ", reqId, " ", errorCode, " ", errorString)

    def tickPrice(self, reqId, tickType, price, attrib):
        global pprice
        pprice.append({TickTypeEnum.to_str(tickType): price})

    def contractDetails(self, reqId, contractDetails):
        global pcontract
        pcontract = list()
        pcontract.append({'symbol': contractDetails.contract.symbol})
        pcontract.append({'conId': contractDetails.contract.conId})
        pcontract.append({'longName': contractDetails.longName})
        pcontract.append({'stockType': contractDetails.stockType})
        pcontract.append({'currency': contractDetails.contract.currency})
        pcontract.append({'exchange': contractDetails.contract.exchange})
        pcontract.append({'secType': contractDetails.contract.secType})
        pcontract.append({'sector': contractDetails.category})
        pcontract.append({'industry': contractDetails.industry})
        pcontract.append({'subcategory': contractDetails.subcategory})
        pcontract.append({'timeZoneId': contractDetails.timeZoneId})
        pcontract.append({'LiquidHours': contractDetails.liquidHours})

    def contractDetailsEnd(self, reqId):
        print("End of contractDetails")
        self.disconnect()

def main():

    global mycontract, pprice, pcontract
    app = TestApp()
    pprice = list()
    app.connect("127.0.0.1", 7496, 6666)

    glist = ('165', '232', '243', '258', '456')
    mycontract = Contract()
    mycontract.symbol = "HASI"
    mycontract.secType = "STK"
    mycontract.exchange = "SMART"
    mycontract.currency = "USD"
    mycontract.primaryExchange = "ISLAND"
    time.sleep(.1)

    app.reqMarketDataType(3)
    app.reqMktData(1, mycontract, "232, 456, 258, 165", 0, 0, [])
    app.reqContractDetails(2, mycontract)
    app.run()
    print(pprice, pcontract)


if __name__ == "__main__":
    main()

