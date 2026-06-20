"""
Batch histórico CNV — Superfondos
Descarga todos los días disponibles en CNV e inserta en diaria_cnv
los fondos de _SUPERFONDO_CAFCI (+ nombre "Superfondo"/"Super Ahorro").

Uso:
    python AppTest/run_batch_cnv_superfondos.py
    python AppTest/run_batch_cnv_superfondos.py --desde 2024-01-01
    python AppTest/run_batch_cnv_superfondos.py --desde 2024-01-01 --hasta 2025-06-22
"""

import argparse
import json
import os
import sys
from datetime import datetime, date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "AppOO"))

from Modulos_Mysql import BDsystem

_appoo = os.path.join(os.path.dirname(__file__), "..", "AppOO")
_profile_path = os.environ.get("APPOO_PROFILE", os.path.join(_appoo, "profiles", "main.json"))
with open(_profile_path, encoding="utf-8") as _f:
    _cfg = json.load(_f)
BDsystem.configure(_cfg.get("db", {}))
_tmp = _cfg.get("tmp_path", os.path.join(_appoo, "tmp"))
if not os.path.isabs(_tmp):
    _tmp = os.path.normpath(os.path.join(_appoo, _tmp))
os.environ.setdefault("APPOO_TMP", _tmp)

import pandas as pd
from pathlib import Path

from download_cnv_selenium import obtener_documentos, descargar_cnv_hoy
from Modulos_Utilitarios import delete_file
from Class_FondosInversion import sync_cnv_superfondos, _CNV_NAMES_LIST


def _parse_fecha_arg(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def main():
    parser = argparse.ArgumentParser(description="Batch CNV Superfondos")
    parser.add_argument(
        "--desde",
        type=_parse_fecha_arg,
        default=None,
        help="Fecha mínima YYYY-MM-DD (default: todo lo disponible en CNV)",
    )
    parser.add_argument(
        "--hasta", type=_parse_fecha_arg, default=date.today(), help="Fecha máxima YYYY-MM-DD (default: hoy)"
    )
    args = parser.parse_args()

    print("Obteniendo lista de documentos disponibles en CNV...")
    docs = obtener_documentos()
    if not docs:
        print("ERROR: No se encontraron documentos en CNV.")
        sys.exit(1)

    docs.sort(key=lambda d: d["fecha_dt"])

    if args.desde:
        docs = [d for d in docs if d["fecha_dt"].date() >= args.desde]
    docs = [d for d in docs if d["fecha_dt"].date() <= args.hasta]

    print(
        f"  {len(docs)} fechas a procesar "
        f"({docs[0]['fecha_dt'].strftime('%d/%m/%Y')} → {docs[-1]['fecha_dt'].strftime('%d/%m/%Y')})"
    )

    total_insertados = 0
    for i, doc in enumerate(docs, 1):
        fecha_str = doc["fecha_dt"].strftime("%Y-%m-%d")
        print(f"  [{i}/{len(docs)}] {fecha_str} ... ", end="", flush=True)

        resultado = descargar_cnv_hoy(fecha_str)
        if not resultado.get("success") or not resultado.get("archivo"):
            print("SKIP (descarga fallida)")
            continue

        archivo = resultado["archivo"]
        try:
            df = pd.read_excel(archivo, skiprows=11, header=None, names=_CNV_NAMES_LIST)
            df.fillna(0, inplace=True)
            n = sync_cnv_superfondos(df)
            total_insertados += n
            print(f"OK ({n} insertados)")
        except Exception as e:
            print(f"ERROR parse: {e}")
        finally:
            delete_file(ruta=Path(archivo), display=False)

    print(f"\nFinalizado — total insertados: {total_insertados}")


if __name__ == "__main__":
    main()
