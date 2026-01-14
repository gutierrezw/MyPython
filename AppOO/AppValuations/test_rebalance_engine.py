# =========================
# Test offline RebalanceEngine
# =========================

from pprint import pprint

# importar tu engine real
from rebalance_engine import RebalanceEngine


# =========================
# Fake DataHub (mínimo)
# =========================
class FakeDataHub:
    def __init__(self):
        self.info = {
            "AAPL": {
                "sector": "Tech",
                "region": "USA",
                "asset_type": "Stock",
                "buy": {"valuation": {"label": "neutral"}},
            },
            "JNJ": {
                "sector": "Health",
                "region": "USA",
                "asset_type": "Stock",
                "dividends": {
                    "monthly": {
                        "Jan": 12.5,
                        "Apr": 12.5,
                        "Jul": 12.5,
                        "Oct": 12.5,
                    }
                },
            },
            "NESN": {
                "sector": "Consumer",
                "region": "Europe",
                "asset_type": "Stock",
                "dividends": {
                    "monthly": {
                        "Mar": 18.0,
                        "Sep": 18.0,
                    }
                },
            },
            "BTC": {
                "sector": "Crypto",
                "region": "Global",
                "asset_type": "Crypto",
                "buy": {"valuation": {"label": "cheap"}},
            },
            "TimeDataHub": {},
        }

        self.manager_buysell = {
            "sector": {
                "data": {
                    "summary": {
                        "Name": ["Tech", "Health", "Consumer", "Crypto"],
                        "Peso": [0.40, 0.20, 0.15, 0.25],
                        "media": 0.25,
                    }
                },
                "total_valor_market": 46275.88,
            },
            "region": {
                "data": {
                    "summary": {
                        "Name": ["USA", "Europe", "Global"],
                        "Peso": [0.55, 0.25, 0.20],
                        "media": 1 / 3,
                    }
                },
                "total_valor_market": 46275.88,
            },
            "activos": {
                "data": {
                    "summary": {
                        "Name": ["Stock", "Crypto"],
                        "Peso": [0.70, 0.30],
                        "media": 0.50,
                    }
                },
                "total_valor_market": 46275.88,
            },
        }


# =========================
# Run test
# =========================
if __name__ == "__main__":

    hub = FakeDataHub()
    engine = RebalanceEngine(hub)

    print("\n=== GAPS ===")
    pprint(engine.compute_gaps())

    print("\n=== NORMALIZED GAPS ===")
    pprint(engine.normalize_gaps())

    print("\n=== DIMENSION PRIORITY ===")
    pprint(engine.prioritize_dimensions())

    print("\n=== RANKING FINAL ===")
    ranking = engine.rank()

    for i, r in enumerate(ranking, start=1):
        print(f"\n#{i} {r['symbol']}")
        print("  score:", round(r["score"], 4))
        print("  metadata:", r["metadata"])
        print("  impacto:")
        pprint(r["impacto"])
