from massive import RESTClient

client = RESTClient("ZVNtBpw4fymBFSxL4zqu81lpQc2t8QKo")
# client = RESTClient("ZVNtBpw4fymBFSxL4zqu81lpQc2t8QKo")


tickers = []
i = 0
for t in client.list_tickers(
    ticker="X:BTCUSDT",
    market="crypto",
    active="true",
    order="asc",
    limit="100",
    sort="ticker",
):
    tickers.append(t)
    if i > 2:
        break

print(tickers)
