class TradingBotSpot:
    def __init__(
        self,
        client,
        symbol: str,
        interval: str = "15m",
        rsi_period: int = 14,
        ema_fast: int = 12,
        ema_slow: int = 26,
        macd_signal: int = 9,
        capital_usdt: float = 100,
        risk_pct: float = 0.02
    ):
        self.client = client              # tu MySpot
        self.symbol = symbol
        self.interval = interval

        # Indicadores
        self.rsi_period = rsi_period
        self.ema_fast = ema_fast
        self.ema_slow = ema_slow
        self.macd_signal = macd_signal

        # Riesgo
        self.capital_usdt = capital_usdt
        self.risk_pct = risk_pct

        # Estado
        self.position = None              # None | "LONG"
        self.entry_price = None

    def get_klines(self, limit=200):
        return self.client.klines(
            symbol=self.symbol,
            interval=self.interval,
            limit=limit
        )

    def compute_indicators(self, df):
        df["ema_fast"] = df["close"].ewm(span=self.ema_fast).mean()
        df["ema_slow"] = df["close"].ewm(span=self.ema_slow).mean()

        df["macd"] = df["ema_fast"] - df["ema_slow"]
        df["macd_signal"] = df["macd"].ewm(span=self.macd_signal).mean()

        delta = df["close"].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)

        avg_gain = gain.rolling(self.rsi_period).mean()
        avg_loss = loss.rolling(self.rsi_period).mean()
        rs = avg_gain / avg_loss

        df["rsi"] = 100 - (100 / (1 + rs))
        return df

    def should_buy(self, row):
        return (
            row["rsi"] < 30 and
            row["macd"] > row["macd_signal"] and
            row["ema_fast"] > row["ema_slow"]
        )

    def should_sell(self, row):
        return (
            row["rsi"] > 70 or
            row["macd"] < row["macd_signal"]
        )

    def calc_quantity(self, price):
        risk_amount = self.capital_usdt * self.risk_pct
        qty = risk_amount / price
        return round(qty, 6)

    def buy(self, price):
        qty = self.calc_quantity(price)

        self.client.get_new_order(
            symbol=self.symbol,
            side="BUY",
            type="MARKET",
            quantity=qty
        )

        self.position = "LONG"
        self.entry_price = price

    def sell(self, qty):
        self.client.get_new_order(
            symbol=self.symbol,
            side="SELL",
            type="MARKET",
            quantity=qty
        )

        self.position = None
        self.entry_price = None

    def evaluate(self, df):
        last = df.iloc[-1]

        if self.position is None:
            if self.should_buy(last):
                self.buy(last["close"])

        elif self.position == "LONG":
            if self.should_sell(last):
                self.sell(self.calc_quantity(last["close"]))
