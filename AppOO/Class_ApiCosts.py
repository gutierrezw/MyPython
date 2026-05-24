"""
Class_ApiCosts.py - Tracker de costos API Anthropic (Admin API)
Endpoint: /v1/organizations/cost_report — devuelve costos en USD por día.
Tokens se estiman dividiendo el costo por el precio/M del modelo.
"""

from Modulos_python import requests, logging, date
from Modulos_Utilitarios import write_json_tmp

_logger = logging.getLogger("ApiTracker")

_API_BASE = "https://api.anthropic.com"
_API_VER = "2023-06-01"
_TMP_FILE = "api_costs.json"

_INPUT_TYPES = {"uncached_input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"}
_OUTPUT_TYPES = {"output_tokens"}

# Precio por 1M tokens (USD) — para estimar tokens a partir del costo
_PRECIO_INPUT = {
    "claude-opus-4": 5.00,
    "claude-opus-4-5": 5.00,
    "claude-opus-4-6": 5.00,
    "claude-sonnet-4-5": 3.00,
    "claude-sonnet-4-6": 3.00,
    "claude-haiku-4-5": 1.00,
    "claude-3-5-sonnet": 3.00,
    "claude-3-5-haiku": 0.80,
}
_PRECIO_OUTPUT = {
    "claude-opus-4": 25.00,
    "claude-opus-4-5": 25.00,
    "claude-opus-4-6": 25.00,
    "claude-sonnet-4-5": 15.00,
    "claude-sonnet-4-6": 15.00,
    "claude-haiku-4-5": 5.00,
    "claude-3-5-sonnet": 15.00,
    "claude-3-5-haiku": 4.00,
}
_DEFAULT_INPUT = 3.00
_DEFAULT_OUTPUT = 15.00


def _precio_input(model: str) -> float:
    for k, v in _PRECIO_INPUT.items():
        if k in model:
            return v
    return _DEFAULT_INPUT


def _precio_output(model: str) -> float:
    for k, v in _PRECIO_OUTPUT.items():
        if k in model:
            return v
    return _DEFAULT_OUTPUT


class ApiCostTracker:
    """Consulta cost_report de Anthropic Admin API y persiste en tmp/api_costs.json."""

    def __init__(self, api_key: str):
        self._headers = {
            "anthropic-version": _API_VER,
            "x-api-key": api_key,
        }

    def _fetch_pages(self, start: str, end: str) -> list:
        all_data = []
        next_page = None
        while True:
            params = {"starting_at": start, "ending_at": end, "group_by[]": "description", "bucket_width": "1d"}
            if next_page:
                params["page"] = next_page
            r = requests.get(
                f"{_API_BASE}/v1/organizations/cost_report", headers=self._headers, params=params, timeout=15
            )
            r.raise_for_status()
            page = r.json()
            all_data.extend(page.get("data", []))
            if not page.get("has_more"):
                break
            next_page = page.get("next_page")
        return all_data

    def get_monthly_summary(self) -> dict:
        """Retorna dict con costos y tokens estimados del mes actual. Guarda en tmp/api_costs.json."""
        hoy = date.today()
        inicio = date(hoy.year, hoy.month, 1).strftime("%Y-%m-%dT00:00:00Z")
        fin = hoy.strftime("%Y-%m-%dT23:59:59Z")
        hoy_str = hoy.strftime("%Y-%m-%d")

        buckets = self._fetch_pages(inicio, fin)

        total_cost = today_cost = 0.0
        total_input_tokens = total_output_tokens = 0
        by_model: dict = {}
        daily_map: dict = {}

        for bucket in buckets:
            day = bucket["starting_at"][:10]
            for r in bucket.get("results", []):
                model = r.get("model", "unknown")
                amount = float(r.get("amount", 0))
                ttype = r.get("token_type", "")

                total_cost += amount
                if day == hoy_str:
                    today_cost += amount

                if model not in by_model:
                    by_model[model] = {
                        "input_cost": 0.0,
                        "output_cost": 0.0,
                        "cost": 0.0,
                        "input_tokens": 0,
                        "output_tokens": 0,
                    }

                by_model[model]["cost"] += amount

                if ttype in _INPUT_TYPES:
                    by_model[model]["input_cost"] += amount
                    tokens = int(amount / _precio_input(model) * 1_000_000)
                    by_model[model]["input_tokens"] += tokens
                    total_input_tokens += tokens
                elif ttype in _OUTPUT_TYPES:
                    by_model[model]["output_cost"] += amount
                    tokens = int(amount / _precio_output(model) * 1_000_000)
                    by_model[model]["output_tokens"] += tokens
                    total_output_tokens += tokens

                if day not in daily_map:
                    daily_map[day] = 0.0
                daily_map[day] += amount

        daily = [{"date": k, "cost": round(v, 4)} for k, v in sorted(daily_map.items()) if v > 0]

        def _round_model(m):
            return {
                "input_cost": round(m["input_cost"], 4),
                "output_cost": round(m["output_cost"], 4),
                "cost": round(m["cost"], 4),
                "input_tokens": m["input_tokens"],
                "output_tokens": m["output_tokens"],
            }

        summary = {
            "periodo": f"{hoy.strftime('%B')} {hoy.year}",
            "total_cost": round(total_cost, 4),
            "today_cost": round(today_cost, 4),
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "by_model": {k: _round_model(v) for k, v in by_model.items()},
            "daily": daily,
        }

        write_json_tmp(_TMP_FILE, summary)
        _logger.warning(
            f"ApiCosts: total=${total_cost:.4f} hoy=${today_cost:.4f} "
            f"in={total_input_tokens:,} out={total_output_tokens:,} modelos={len(by_model)}"
        )
        return summary
