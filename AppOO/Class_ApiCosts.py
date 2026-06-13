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

# Precio por 1M tokens (USD) — para calcular tokens a partir del costo
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


def _normalize(model: str) -> str:
    return model.lower().replace(" ", "-")


def _precio_input(model: str) -> float:
    norm = _normalize(model)
    for k, v in _PRECIO_INPUT.items():
        if k in norm:
            return v
    return _DEFAULT_INPUT


def _precio_output(model: str) -> float:
    norm = _normalize(model)
    for k, v in _PRECIO_OUTPUT.items():
        if k in norm:
            return v
    return _DEFAULT_OUTPUT


class ApiCostTracker:
    """Consulta cost_report de Anthropic Admin API y persiste en tmp/api_costs.json."""

    def __init__(self, api_key: str, workspace_id: str = ""):
        self._headers = {
            "anthropic-version": _API_VER,
            "x-api-key": api_key,
        }
        self._workspace_id = workspace_id

    def _fetch_pages(self, start: str, end: str, group_by: list = None) -> list:
        all_data = []
        next_page = None
        group_by = group_by or ["description"]
        while True:
            params = [
                ("starting_at", start),
                ("ending_at", end),
                ("bucket_width", "1d"),
            ] + [("group_by[]", g) for g in group_by]
            if next_page:
                params.append(("page", next_page))
            r = requests.get(
                f"{_API_BASE}/v1/organizations/cost_report", headers=self._headers, params=params, timeout=15
            )
            if not r.ok:
                _logger.error(f"[ApiCosts] HTTP {r.status_code}: {r.text}")
                r.raise_for_status()
            page = r.json()
            all_data.extend(page.get("data", []))
            if not page.get("has_more"):
                break
            next_page = page.get("next_page")
        return all_data

    def _fetch_api_keys(self) -> dict:
        """Retorna dict {workspace_id: key_name} — una key por workspace."""
        try:
            r = requests.get(f"{_API_BASE}/v1/organizations/api_keys", headers=self._headers, timeout=15)
            if not r.ok:
                return {}
            ws_to_key = {}
            for k in r.json().get("data", []):
                ws_id = k.get("workspace_id", "")
                if ws_id and ws_id not in ws_to_key:
                    ws_to_key[ws_id] = k.get("name", k["id"])
            return ws_to_key
        except Exception as e:
            _logger.warning(f"[ApiCosts._fetch_api_keys]: {e}")
            return {}

    def _fetch_workspaces(self) -> dict:
        """Retorna dict {workspace_id: workspace_name} consultando /v1/organizations/workspaces."""
        try:
            r = requests.get(f"{_API_BASE}/v1/organizations/workspaces", headers=self._headers, timeout=15)
            if not r.ok:
                return {}
            return {w["id"]: w.get("name", w["id"]) for w in r.json().get("data", [])}
        except Exception as e:
            _logger.warning(f"[ApiCosts._fetch_workspaces]: {e}")
            return {}

    def get_monthly_summary(self) -> dict:
        """Retorna dict con costos y tokens estimados del mes actual. Guarda en tmp/api_costs.json."""
        hoy = date.today()
        inicio = date(hoy.year, hoy.month, 1).strftime("%Y-%m-%dT00:00:00Z")
        fin = hoy.strftime("%Y-%m-%dT23:59:59Z")
        hoy_str = hoy.strftime("%Y-%m-%d")

        buckets = self._fetch_pages(inicio, fin)
        ws_buckets = self._fetch_pages(inicio, fin, group_by=["workspace_id"])
        ws_to_key = self._fetch_api_keys()  # {workspace_id: key_name}
        ws_names = self._fetch_workspaces()  # {workspace_id: workspace_name}

        total_cost = today_cost = 0.0
        total_input_tokens = total_output_tokens = 0
        by_model: dict = {}
        daily_map: dict = {}
        by_workspace: dict = {}

        _INPUT_TYPES = ("uncached_input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")
        _OUTPUT_TYPES = ("output_tokens",)

        for bucket in buckets:
            day = bucket["starting_at"][:10]
            for r in bucket.get("results", []):
                amount = float(r.get("amount", 0))
                model = r.get("model") or r.get("description", "unknown") or "unknown"
                token_type = r.get("token_type") or ""

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

                if token_type in _INPUT_TYPES:
                    by_model[model]["input_cost"] += amount
                    tokens = int(amount / _precio_input(model) * 1_000_000)
                    by_model[model]["input_tokens"] += tokens
                    total_input_tokens += tokens
                elif token_type in _OUTPUT_TYPES:
                    by_model[model]["output_cost"] += amount
                    tokens = int(amount / _precio_output(model) * 1_000_000)
                    by_model[model]["output_tokens"] += tokens
                    total_output_tokens += tokens

                if day not in daily_map:
                    daily_map[day] = 0.0
                daily_map[day] += amount

        for bucket in ws_buckets:
            for r in bucket.get("results", []):
                ws_id = r.get("workspace_id") or "default"
                label = ws_to_key.get(ws_id) or ws_names.get(ws_id) or ws_id
                amount = float(r.get("amount", 0))
                if label not in by_workspace:
                    by_workspace[label] = {"cost": 0.0}
                by_workspace[label]["cost"] += amount

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
            "by_workspace": {k: {"cost": round(v["cost"], 4)} for k, v in by_workspace.items()},
            "daily": daily,
        }

        write_json_tmp(_TMP_FILE, summary)
        _logger.warning(
            f"ApiCosts: total=${total_cost:.4f} hoy=${today_cost:.4f} "
            f"in={total_input_tokens:,} out={total_output_tokens:,} modelos={len(by_model)}"
        )
        return summary
