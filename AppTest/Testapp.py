from ibapi.client import *
from ibapi.wrapper import *

from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from threading import Timer

class TestApp(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)

    def error(self, reqId, errorCode, errorString, advancedOrderRejectJson):
        print("Error: ", reqId, " ", errorCode, " ", errorString)

    def nextValidId(self, orderId):
        self.start()
        mycontract = Contract()
        mycontract.symbol = mycontract.symbol
        mycontract.secType = "STK"
        mycontract.exchange = "SMART"
        mycontract.currency = "USD"
        self.reqMarketDataType(4)
        self.reqMktData(orderId, mycontract, "", 0, 0, [])


    def updatePortfolio(self, contract: Contract, position: float, marketPrice: float, marketValue: float,
                        averageCost: float, unrealizedPNL: float, realizedPNL: float, accountName: str):


        print(contract.symbol, position, marketPrice, marketValue, averageCost,  unrealizedPNL)

    def tickPrice(self, reqId, tickType, price, attrib):
        print(f"tickPrice. reqId: {reqId}, tickType: {TickTypeEnum.to_str(tickType)}, price: {price}, attribs: {attrib}")


    def start(self):
        # Account number can be omitted when using reqAccountUpdates with single account structure
        self.reqAccountUpdates(True, "")


    def stop(self):
        self.reqAccountUpdates(False, "")
        self.done = True
        self.disconnect()

def main():
    app = TestApp()
    if EClient.isConnected(app):
        app.connect("127.0.0.1", 7496, 6666)
        #app.connect("127.0.0.1", 4001, 6666)
        Timer(.2, app.stop).start()
        app.run()
    else:
        print('sin conexion')

if __name__ == "__main__":
    main()


 #def updateAccountValue(self, key: str, val: str, currency: str, accountName: str):
    #    print("UpdateAccountValue. Key:", key, "Value:", val, "Currency:", currency, "AccountName:", accountName)
