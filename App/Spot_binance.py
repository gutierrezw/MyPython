from binance.api import API


class Spot(API):
    def __init__(self, api_key=None, api_secret=None, **kwargs):
        if "base_url" not in kwargs:
            kwargs["base_url"] = "https://api.binance.com"
        super().__init__(api_key, api_secret, **kwargs)

    # MARKETS

    # ACCOUNT (including orders and trades)

    # WALLET

    # FIAT

    # C2C

    # Crypto LOANS
    # from binance.spot._crypto_loan import flexible_loan_adjust_ltv
    # from binance.spot._crypto_loan import flexible_loan_assets_data
    # from binance.spot._crypto_loan import flexible_loan_borrow_history
    # from binance.spot._crypto_loan import flexible_loan_borrow
    # from binance.spot._crypto_loan import flexible_loan_collateral_assets_data
    # from binance.spot._crypto_loan import flexible_loan_ltv_adjustment_history
    # from binance.spot._crypto_loan import flexible_loan_repay
    # from binance.spot._crypto_loan import flexible_loan_repayment_history

    # from binance.spot._crypto_loan import flexible_loan_ongoing_orders
    def flexible_loan_ongoing_orders(self, **kwargs):
        """Borrow - Get Flexible Loan Ongoing Orders (USER_DATA)

        Weight(IP): 300

        GET /sapi/v1/loan/flexible/ongoing/orders

        https://binance-docs.github.io/apidocs/spot/en/#borrow-get-flexible-loan-ongoing-orders-user_data

        Keyword Args:
            loanCoin (str, optional): Coin loaned
            collateralCoin (str, optional): Coin used as collateral
            current (int, optional): Current querying page. Start from 1. Default:1
            limit (int, optional): Default 500; max 1000.
            recvWindow (int, optional): The value cannot be greater than 60000
        """

        # gwi20240304 url_path = "/sapi/v1/loan/flexible/ongoing/orders"
        url_path = "/sapi/v2/loan/flexible/ongoing/orders"
        return self.sign_request("GET", url_path, {**kwargs})
    # PAY

    # Simple Earn

    # Auto-Invest
