from ibapi.client import *
from ibapi.wrapper import *
import time

class TestApp(EClient, EWrapper):
    def __init__(self):
        EClient.__init__(self, self)

    def error(self, reqId, errorCode, errorString, advancedOrderRejectJson):
        #if errorCode not in (2104, 2106, 2158):
        print("Error: ", reqId, " ", errorCode, " ", errorString)

    def nextValidId(self, orderId: int):
        global dmkt, mycontract

        self.reqMarketDataType(4)
        self.reqMktData(orderId, mycontract, "165, 456", 0, 0, [])
        self.reqContractDetails(orderId, mycontract)

        time.sleep(.5)
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
            ibdiv = value.rsplit(",")
            dmkt.update({'past12Months': float(ibdiv[0]), 'next12Months': float(ibdiv[1]),
                         'nextDate': ibdiv[2], 'nextAmount': float(ibdiv[3])})

    def contractDetails(self, reqId:int, contractDetails:ContractDetails):
        global dmkt
        dmkt.update({'symbol': contractDetails.contract.symbol, 'conId': contractDetails.contract.conId,
                     'name': contractDetails.longName, 'stockType': contractDetails.stockType,
                     'currency': contractDetails.contract.currency, 'exchange': contractDetails.contract.exchange,
                     'secType': contractDetails.contract.secType, 'sector': contractDetails.category,
                     'industry': contractDetails.industry, 'subcategory': contractDetails.subcategory,
                     'timeZoneId': contractDetails.timeZoneId, 'LiquidHours': contractDetails.liquidHours})

    def contractDetailsEnd(self, reqId:int):
        self.disconnect()



def main():
    global dmkt, mycontract
    dmkt = {}
    ticket = 'HASI'
    app = TestApp()
    #app.connect("127.0.0.1", 4001, 6666)
    app.connect("127.0.0.1", 7496, 6666)
    mycontract = Contract()
    mycontract.symbol = ticket
    mycontract.secType = "STK"
    mycontract.exchange = "SMART"
    mycontract.currency = "USD"
    ticket_dmkt = {ticket: dmkt}
    app.run()
    print(ticket_dmkt)


if __name__ == "__main__":
    main()

