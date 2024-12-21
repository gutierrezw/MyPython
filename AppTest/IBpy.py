# api basica de conexion con IBKs

from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
import time


class TestApp(EClient, EWrapper):
    def __int__(self):
        EClient.__init__(self)
#        EWrapper.__init__(self)

    def error(self, reqId, errorCode, errorString):
        print("[Error]> ", reqId, " ", errorCode, " ", errorString)

    def contractDetails(self, reqId, contractDetails):
        print("contractDetails: ", reqId, " ", contractDetails)

#def main() -> object:
def main():

    app = TestApp()

    # app.connect("127.0.0.1", 4001, 4214563)

    app.connect("127.0.0.1", 7497, 4214563)

    xcontract = Contract()
    xcontract.symbol = "GILD"
    xcontract.setype = "STK"
    xcontract.exchange = "SMART"
    xcontract.currency = "USD"
    xcontract.primaryExchange = "ISLAND"

    time.sleep(3)
    app.reqContractDetails(EClient,1,xcontract)

    app.run()


if __name__=="__main__":
    main()

