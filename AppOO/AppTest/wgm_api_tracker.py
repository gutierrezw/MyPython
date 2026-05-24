"""
WGM API Cost Tracker — Módulo Python
=====================================
Trackea el uso y costo de la API de Anthropic.
Integrable como módulo en el sistema de pensión WGM.

Instalación:
    pip install requests rich python-dotenv

Uso rápido:
    python wgm_api_tracker.py

Uso como módulo:
    from wgm_api_tracker import APITracker
    tracker = APITracker(api_key="sk-ant-...")
    resumen = tracker.get_monthly_summary()
    print(resumen)
"""

import os
import json
import requests
from datetime import datetime, date, timedelta
from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv

# ── Intentamos importar rich para UI bonita ──────────────────────────────────
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.columns import Columns
    from rich import box
    from rich.text import Text
    from rich.progress import BarColumn, Progress
    RICH = True
except ImportError:
    RICH = False

load_dotenv()

# ── Precios por modelo (USD por 1M tokens) — Mayo 2026 ──────────────────────
PRECIOS = {
    "claude-opus-4":     {"input": 5.00,  "output": 25.00},
    "claude-opus-4-5":   {"input": 5.00,  "output": 25.00},
    "claude-opus-4-6":   {"input": 5.00,  "output": 25.00},
    "claude-sonnet-4-5": {"input": 3.00,  "output": 15.00},
    "claude-sonnet-4-6": {"input": 3.00,  "output": 15.00},
    "claude-haiku-4-5":  {"input": 1.00,  "output": 5.00},
    "claude-3-5-sonnet": {"input": 3.00,  "output": 15.00},
    "claude-3-5-haiku":  {"input": 0.80,  "output": 4.00},
    "default":           {"input": 3.00,  "output": 15.00},
}

ANTHROPIC_API = "https://api.anthropic.com"
ANTHROPIC_VER = "2023-06-01"


# ── Dataclasses ───────────────────────────────────────────────────────────────
@dataclass
class ModelUsage:
    model:        str
    input_tokens: int   = 0
    output_tokens:int   = 0
    requests:     int   = 0
    cost:         float = 0.0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    @property
    def short_name(self) -> str:
        return self.model.replace("claude-", "").replace("-2024", "")


@dataclass
class DailyCost:
    date:  str
    cost:  float
    tokens:int


@dataclass
class MonthlySummary:
    periodo:      str
    total_cost:   float
    total_tokens: int
    total_input:  int
    total_output: int
    total_reqs:   int
    balance:      float
    by_model:     dict[str, ModelUsage]    = field(default_factory=dict)
    daily:        list[DailyCost]          = field(default_factory=list)
    today_cost:   float                    = 0.0
    today_reqs:   int                      = 0


# ── Tracker principal ─────────────────────────────────────────────────────────
class APITracker:
    """Tracker de costos de la API de Anthropic para el sistema WGM."""

    def __init__(self, api_key: Optional[str] = None, credito_total: float = 10.0):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        self.credito_total = credito_total
        self._headers = {
            "x-api-key":         self.api_key,
            "anthropic-version": ANTHROPIC_VER,
            "content-type":      "application/json",
        }

    # ── Precio por modelo ────────────────────────────────────────────────────
    def _precio(self, model: str) -> dict:
        for k, v in PRECIOS.items():
            if k in model:
                return v
        return PRECIOS["default"]

    def _calc_cost(self, model: str, input_t: int, output_t: int) -> float:
        p = self._precio(model)
        return (input_t * p["input"] + output_t * p["output"]) / 1_000_000

    # ── Llamada a la API ─────────────────────────────────────────────────────
    def _fetch_usage(self, start: str, end: str) -> list[dict]:
        """Trae el usage diario desde la API de Anthropic."""
        if not self.api_key or not self.api_key.startswith("sk-ant"):
            raise ValueError("API key inválida. Debe comenzar con sk-ant...")

        url = f"{ANTHROPIC_API}/v1/usage"
        params = {"start_date": start, "end_date": end, "granularity": "daily"}
        r = requests.get(url, headers=self._headers, params=params, timeout=15)

        if r.status_code == 401:
            raise PermissionError("API key incorrecta o sin permisos.")
        if r.status_code == 403:
            raise PermissionError("Sin acceso al endpoint de usage. Verificá permisos.")
        r.raise_for_status()
        return r.json().get("data", [])

    # ── Resumen mensual ───────────────────────────────────────────────────────
    def get_monthly_summary(self, year: Optional[int] = None, month: Optional[int] = None) -> MonthlySummary:
        """Retorna el resumen de uso del mes indicado (default: mes actual)."""
        hoy = date.today()
        year  = year  or hoy.year
        month = month or hoy.month

        inicio = date(year, month, 1).strftime("%Y-%m-%d")
        fin    = hoy.strftime("%Y-%m-%d")
        periodo= f"{hoy.strftime('%B')} {year}"

        entries = self._fetch_usage(inicio, fin)

        total_cost = total_input = total_output = total_reqs = 0
        today_cost = today_reqs = 0
        by_model: dict[str, ModelUsage] = {}
        daily_map: dict[str, DailyCost] = {}
        hoy_str = hoy.strftime("%Y-%m-%d")

        for e in entries:
            model    = e.get("model", "unknown")
            inp      = e.get("input_tokens", 0)
            out      = e.get("output_tokens", 0)
            reqs     = e.get("request_count", 1)
            day      = e.get("date", "")
            cost     = self._calc_cost(model, inp, out)

            total_cost   += cost
            total_input  += inp
            total_output += out
            total_reqs   += reqs

            if day == hoy_str:
                today_cost += cost
                today_reqs += reqs

            # Por modelo
            if model not in by_model:
                by_model[model] = ModelUsage(model=model)
            mu = by_model[model]
            mu.input_tokens  += inp
            mu.output_tokens += out
            mu.requests      += reqs
            mu.cost          += cost

            # Por día
            if day not in daily_map:
                daily_map[day] = DailyCost(date=day, cost=0.0, tokens=0)
            daily_map[day].cost   += cost
            daily_map[day].tokens += inp + out

        daily = sorted(daily_map.values(), key=lambda x: x.date)
        balance = self.credito_total - total_cost

        return MonthlySummary(
            periodo=periodo,
            total_cost=total_cost,
            total_tokens=total_input + total_output,
            total_input=total_input,
            total_output=total_output,
            total_reqs=total_reqs,
            balance=balance,
            by_model=by_model,
            daily=daily,
            today_cost=today_cost,
            today_reqs=today_reqs,
        )

    # ── Resumen últimos N días ────────────────────────────────────────────────
    def get_last_days(self, days: int = 7) -> MonthlySummary:
        """Resumen de los últimos N días."""
        hoy    = date.today()
        inicio = (hoy - timedelta(days=days)).strftime("%Y-%m-%d")
        fin    = hoy.strftime("%Y-%m-%d")

        entries = self._fetch_usage(inicio, fin)

        total_cost = total_input = total_output = total_reqs = 0
        by_model: dict[str, ModelUsage] = {}
        daily_map: dict[str, DailyCost] = {}

        for e in entries:
            model = e.get("model", "unknown")
            inp   = e.get("input_tokens", 0)
            out   = e.get("output_tokens", 0)
            reqs  = e.get("request_count", 1)
            day   = e.get("date", "")
            cost  = self._calc_cost(model, inp, out)

            total_cost   += cost
            total_input  += inp
            total_output += out
            total_reqs   += reqs

            if model not in by_model:
                by_model[model] = ModelUsage(model=model)
            mu = by_model[model]
            mu.input_tokens  += inp
            mu.output_tokens += out
            mu.requests      += reqs
            mu.cost          += cost

            if day not in daily_map:
                daily_map[day] = DailyCost(date=day, cost=0.0, tokens=0)
            daily_map[day].cost   += cost
            daily_map[day].tokens += inp + out

        daily   = sorted(daily_map.values(), key=lambda x: x.date)
        balance = self.credito_total - total_cost

        return MonthlySummary(
            periodo=f"Últimos {days} días",
            total_cost=total_cost,
            total_tokens=total_input + total_output,
            total_input=total_input,
            total_output=total_output,
            total_reqs=total_reqs,
            balance=balance,
            by_model=by_model,
            daily=daily,
        )

    # ── Export JSON ───────────────────────────────────────────────────────────
    def export_json(self, summary: MonthlySummary, path: str = "wgm_api_usage.json"):
        data = {
            "periodo":      summary.periodo,
            "total_cost":   round(summary.total_cost, 6),
            "balance":      round(summary.balance, 6),
            "total_tokens": summary.total_tokens,
            "total_input":  summary.total_input,
            "total_output": summary.total_output,
            "total_reqs":   summary.total_reqs,
            "today_cost":   round(summary.today_cost, 6),
            "today_reqs":   summary.today_reqs,
            "by_model": {
                m: {
                    "cost":         round(u.cost, 6),
                    "tokens":       u.total_tokens,
                    "input_tokens": u.input_tokens,
                    "output_tokens":u.output_tokens,
                    "requests":     u.requests,
                }
                for m, u in summary.by_model.items()
            },
            "daily": [
                {"date": d.date, "cost": round(d.cost, 6), "tokens": d.tokens}
                for d in summary.daily
            ],
            "exported_at": datetime.now().isoformat(),
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return path


# ── Display con rich ──────────────────────────────────────────────────────────
def display_rich(summary: MonthlySummary, credito_total: float = 10.0):
    console = Console()

    # ── Header ───────────────────────────────────────────────────────────────
    console.print()
    console.print(Panel(
        f"[bold white]WGM[/] · [cyan]API Cost Tracker[/]  |  [dim]{summary.periodo}[/]",
        border_style="blue", padding=(0, 2)
    ))

    # ── Cards de stats ────────────────────────────────────────────────────────
    bal_color = "green" if summary.balance > 3 else "yellow" if summary.balance > 1 else "red"
    bal_icon  = "✓" if summary.balance > 3 else "⚠" if summary.balance > 1 else "✗"

    cards = [
        Panel(f"[{bal_color}]{bal_icon} ${summary.balance:.2f}[/]\n[dim]Saldo restante[/]",
              border_style=bal_color, title="[dim]BALANCE[/]", padding=(0,1)),
        Panel(f"[blue]${summary.total_cost:.4f}[/]\n[dim]Gasto del período[/]",
              border_style="blue", title="[dim]GASTO[/]", padding=(0,1)),
        Panel(f"[violet]{_fmt_tokens(summary.total_tokens)}[/]\n[dim]Input + Output[/]",
              border_style="magenta", title="[dim]TOKENS[/]", padding=(0,1)),
        Panel(f"[cyan]{summary.total_reqs}[/]\n[dim]Llamadas totales[/]",
              border_style="cyan", title="[dim]REQUESTS[/]", padding=(0,1)),
    ]
    console.print(Columns(cards))

    # ── Tabla por modelo ──────────────────────────────────────────────────────
    if summary.by_model:
        tbl = Table(box=box.SIMPLE_HEAVY, border_style="bright_black",
                    title="[dim]USO POR MODELO[/]", title_style="dim")
        tbl.add_column("Modelo",   style="bold white",  no_wrap=True)
        tbl.add_column("Tokens",   style="magenta",     justify="right")
        tbl.add_column("Input",    style="dim",         justify="right")
        tbl.add_column("Output",   style="dim",         justify="right")
        tbl.add_column("Requests", style="cyan",        justify="right")
        tbl.add_column("Costo",    style="green",       justify="right")
        tbl.add_column("%",        style="dim",         justify="right")

        sorted_models = sorted(summary.by_model.values(), key=lambda x: x.cost, reverse=True)
        for mu in sorted_models:
            pct = (mu.cost / summary.total_cost * 100) if summary.total_cost > 0 else 0
            bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
            tbl.add_row(
                mu.short_name,
                _fmt_tokens(mu.total_tokens),
                _fmt_tokens(mu.input_tokens),
                _fmt_tokens(mu.output_tokens),
                str(mu.requests),
                f"${mu.cost:.4f}",
                f"{pct:.0f}%",
            )
        console.print(tbl)

    # ── Historial diario ──────────────────────────────────────────────────────
    if summary.daily:
        console.print("[dim]HISTORIAL DIARIO (últimos 10 días)[/]")
        max_cost = max(d.cost for d in summary.daily) or 1
        for d in summary.daily[-10:]:
            bar_len = int(d.cost / max_cost * 30)
            bar     = "█" * bar_len + "░" * (30 - bar_len)
            cost_c  = "green" if d.cost < 0.3 else "yellow" if d.cost < 0.8 else "red"
            console.print(
                f"  [dim]{d.date}[/]  [{cost_c}]{bar}[/]  [white]${d.cost:.4f}[/]  [dim]{_fmt_tokens(d.tokens)}[/]"
            )
        console.print()

    # ── Alerta saldo bajo ─────────────────────────────────────────────────────
    if summary.balance < 3:
        console.print(Panel(
            f"[yellow]⚠ Saldo bajo: ${summary.balance:.2f} restantes de ${credito_total:.2f}[/]\n"
            "[dim]Recargá en console.anthropic.com → Billing[/]",
            border_style="yellow", padding=(0, 2)
        ))


def _fmt_tokens(n: int) -> str:
    if n >= 1_000_000: return f"{n/1_000_000:.2f}M"
    if n >= 1_000:     return f"{n/1_000:.1f}K"
    return str(n)


# ── Display sin rich (fallback) ───────────────────────────────────────────────
def display_simple(summary: MonthlySummary):
    sep = "─" * 52
    print(f"\n{'─'*52}")
    print(f"  WGM · API Cost Tracker  |  {summary.periodo}")
    print(sep)
    print(f"  Saldo restante : ${summary.balance:.2f}")
    print(f"  Gasto período  : ${summary.total_cost:.4f}")
    print(f"  Tokens totales : {_fmt_tokens(summary.total_tokens)}")
    print(f"  Requests       : {summary.total_reqs}")
    print(sep)
    print("  Por modelo:")
    for mu in sorted(summary.by_model.values(), key=lambda x: x.cost, reverse=True):
        pct = (mu.cost / summary.total_cost * 100) if summary.total_cost else 0
        print(f"    {mu.short_name:<20} ${mu.cost:.4f}  {_fmt_tokens(mu.total_tokens)}  {pct:.0f}%")
    print(sep)
    if summary.daily:
        print("  Últimos días:")
        for d in summary.daily[-7:]:
            print(f"    {d.date}  ${d.cost:.4f}  {_fmt_tokens(d.tokens)}")
    print(sep + "\n")


# ── CLI principal ─────────────────────────────────────────────────────────────
def main():
    import argparse

    parser = argparse.ArgumentParser(description="WGM API Cost Tracker")
    parser.add_argument("--key",     "-k", help="API key (o variable ANTHROPIC_API_KEY)")
    parser.add_argument("--days",    "-d", type=int, default=0,  help="Últimos N días (0 = mes actual)")
    parser.add_argument("--credito", "-c", type=float, default=10.0, help="Crédito total cargado (default $10)")
    parser.add_argument("--json",    "-j", help="Exportar JSON a este path")
    parser.add_argument("--simple",  "-s", action="store_true", help="Output simple sin rich")
    args = parser.parse_args()

    api_key = args.key or os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("ERROR: Falta API key. Usá --key o definí ANTHROPIC_API_KEY en el entorno.")
        return

    tracker = APITracker(api_key=api_key, credito_total=args.credito)

    try:
        if args.days > 0:
            summary = tracker.get_last_days(args.days)
        else:
            summary = tracker.get_monthly_summary()

        if args.json:
            path = tracker.export_json(summary, args.json)
            print(f"JSON exportado: {path}")

        if RICH and not args.simple:
            display_rich(summary, args.credito)
        else:
            display_simple(summary)

    except (ValueError, PermissionError) as e:
        print(f"ERROR: {e}")
    except requests.RequestException as e:
        print(f"ERROR de red: {e}")


if __name__ == "__main__":
    main()
