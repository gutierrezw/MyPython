import datetime
import asyncio
import pprint
import easyib
from ib_insync import *
from ticktype import *
import ib_insync as ibi
from ibapi.client import *
from ibapi.wrapper import *
import time

class TestApp(EClient, EWrapper):
    def __init__(self):
        EClient.__init__(self, self)

    def error(self, reqId, errorCode, errorString, advancedOrderRejectJson):
        if errorCode not in (2104, 2106, 2158):
            print("Error: ", reqId, " ", errorCode, " ", errorString)

    def nextValidId(self, orderId: int):
        global dmkt, mycontract

        self.reqMarketDataType(3)
        if mycontract.symbol in ('BTC', 'ETH'):
            mycontract.secType = "CRYPTO"
            mycontract.exchange = "PAXOS"
            self.reqMktData(orderId, mycontract, "165", 0, 0, [])
        else:
            self.reqMktData(orderId, mycontract, "165, 456", 0, 0, [])

        self.reqContractDetails(orderId, mycontract)
        time.sleep(.7)
        self.disconnect()

    def tickPrice(self, reqId, tickType, price, attrib):
        global dmkt
        dmkt.update({TickTypeEnum.to_str(tickType) : float(price)})

    def tickSize(self, reqId, tickType, size):
        global dmkt
        dmkt.update({TickTypeEnum.to_str(tickType): float(size)})

    def tickString(self, reqId: TickerId, tickType: TickType, value: str):
        global dmkt
        if  TickTypeEnum.to_str(tickType) == 'IB_DIVIDENDS':
            if value != ',,,':
                ibdiv = value.rsplit(",")
                ibdiv[0] = float(ibdiv[0]) if ibdiv[0] != '' else 0
                ibdiv[1] = float(ibdiv[1]) if ibdiv[1] != '' else 0
                ibdiv[3] = float(ibdiv[3]) if ibdiv[3] != '' else 0
                dmkt.update({'past12Months': float(ibdiv[0]),
                             'next12Months': float(ibdiv[1]),
                             'nextDate': ibdiv[2],
                             'nextAmount': float(ibdiv[3])})

    def contractDetails(self, reqId:int, contractDetails:ContractDetails):
        global dmkt
        dmkt.update({'symbol': contractDetails.contract.symbol, 'conId': contractDetails.contract.conId,
                     'name': contractDetails.longName, 'stockType': contractDetails.stockType,
                     'currency': contractDetails.contract.currency, 'exchange': contractDetails.contract.exchange,
                     'secType': contractDetails.contract.secType, 'sector': contractDetails.category,
                     'industry': contractDetails.industry, 'subcategory': contractDetails.subcategory,
                     'timeZoneId': contractDetails.timeZoneId, 'LiquidHours': contractDetails.liquidHours})

    def contractDetailsEnd(self, reqId:int):
        pass



def main():
    global dmkt, mycontract
    ib = IB()
    iapi = 7496
    #iapi = 4001
    ib.connect('127.0.0.1', iapi, clientId=6666, account='U4214563')
    p = ib.positions(account='U4214563')
    ib.disconnect()

    xp = list()
    for i in p:
        dmkt = {}
        ticket = i.contract.symbol
        app = TestApp()
        app.connect("127.0.0.1", iapi, 6666)
        mycontract = Contract()
        mycontract.symbol = ticket
        mycontract.secType = "STK"
        mycontract.exchange = "SMART"
        mycontract.currency = "USD"
        ticket_dmkt = {ticket: dmkt}
        app.run()
        xp.append({ticket: dmkt})

    print('============================================nfinal= ', xp)


if __name__ == "__main__":
    main()


#ib = IB()
#ib.connect('127.0.0.1', iapi, clientId=6666, account='U4214563')
#p = ib.positions(account='U4214563')




