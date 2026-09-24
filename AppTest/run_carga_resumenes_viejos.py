"""
Carga de una vez los resumenes de tarjeta Santander anteriores a agosto de 2026.

El formato cambio en agosto: hoy el ciclo viene en una linea con seis fechas dd/mm/yy y eso es lo unico que lee
SantanderArTarjetaResumen. Los resumenes de 2025 y del primer semestre de 2026 lo traen en tres lineas con el mes en
espanol, y las cuotas a vencer en la hoja 2. Ese formato no vuelve a aparecer, asi que el soporte NO va al parser de
produccion: vive aca, se corre una vez sobre los PDF que quedaron en desconocidos/, y despues este archivo se puede
borrar.

Escribe por el mismo load() del adaptador real, asi que respeta uq_import (file_hash, section), el INSERT IGNORE de
fin_card_cycles y el recalculo de billing_date.

PENDIENTE antes de correr --commit: ese load() resella billing_date sobre TODOS los movimientos en cuotas ya
cargados de la cuenta (42 filas al 2026-09-22), sin filtro de fecha y sin comparar contra lo que ya esta.
Hacer backup de esas filas primero.

Se invoca desde AppOO, y AppTest es hermana de AppOO, no hija:

    python ..\\AppTest\\run_carga_resumenes_viejos.py            # solo lee y muestra, no toca la BD
    python ..\\AppTest\\run_carga_resumenes_viejos.py --commit   # escribe en la BD
"""

import argparse
import json
import os
import re
import sys
from datetime import date

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

# import diferido — Class_Finance congela EXTRACTOS_DIR al importarse, asi que APPOO_TMP tiene que estar seteado antes
from Modulos_python import connect, pdfplumber  # noqa: E402
from Class_Finance import (  # noqa: E402
    EXTRACTOS_DIR,
    MESES_ES,
    SantanderAr,
    SantanderArTarjetaResumen,
    detect_adapter,
    parse_installments_due,
)


RE_FECHA_ES = re.compile(r"(\d{1,2})\s+([A-Za-z]{3})\.?\s*(\d{2})(?!\d)")
# 'CIERRE' y 'VENCIMIENTO' se buscan en mayusculas: en minusculas colisionan con 'Prox.Cierre:' y 'Vto. Ant.:'
ETIQUETAS_CICLO = (
    ("prev_closing", "Cierre Ant.:"),
    ("next_closing", "Prox.Cierre:"),
    ("next_due", "Prox.Vto.:"),
    ("closing", "CIERRE"),
    ("due", "VENCIMIENTO"),
)


def cuotas_a_vencer(lines):
    """parse_installments_due() sobre una copia sin guiones bajos: el Visa los intercala entre los digitos del
    importe ('_$_7_7_._8_5_0_,_8_5_' es una sola palabra para pdfplumber)."""
    limpias = [[dict(w, text=w["text"].replace("_", "")) for w in line] for line in lines]
    return parse_installments_due(limpias)


class ResumenFormatoViejo(SantanderArTarjetaResumen):
    """Mismo load() que el adaptador de produccion; lo unico distinto es de donde sale el ciclo."""

    def _extract_cycle(self) -> dict | None:
        with pdfplumber.open(self.pdf_path) as pdf:
            hojas = [self._words_to_lines(p.extract_words(x_tolerance=3, y_tolerance=3)) for p in pdf.pages[:2]]
        # una hoja a la vez: el 'top' arranca de cero en cada una, asi que concatenarlas cruza la fila de meses de
        # una con los importes de la otra (da un falso positivo de una cuota en el Visa de diciembre)
        installments = next((c for c in (cuotas_a_vencer(h) for h in hojas) if c), [])
        fechas: dict[str, date] = {}
        for line in hojas[0]:
            texto = " ".join(w["text"] for w in line)
            for clave, etiqueta in ETIQUETAS_CICLO:
                if clave in fechas:
                    continue
                pos = texto.find(etiqueta)
                if pos < 0:
                    continue
                # la fecha se busca despues de la etiqueta: las tres lineas del ciclo llevan dos fechas cada una
                m = RE_FECHA_ES.search(texto, pos + len(etiqueta))
                mes = MESES_ES.get(m.group(2).lower()) if m else None
                if mes:
                    fechas[clave] = date(2000 + int(m.group(3)), mes, int(m.group(1)))
        if not all(k in fechas for k in ("prev_closing", "closing", "due")):
            return None
        return {
            "prev_closing": fechas["prev_closing"],
            "closing": fechas["closing"],
            "due": fechas["due"],
            "next_closing": fechas.get("next_closing"),
            "next_due": fechas.get("next_due"),
            "installments": installments,
        }


def ciclo_ya_cargado(conn, account_ref: str, closing: date) -> bool:
    """Dos de los PDF son el mismo resumen (cierre 19-Mar-26) con distinto file_hash, asi que uq_import no los frena.
    Se chequea el cierre a mano en vez de confiar en el INSERT IGNORE de _save_card_cycle(): si fin_card_cycles no
    tiene un UNIQUE sobre (account_id, closing_date), ese IGNORE no atrapa nada y el ciclo entra dos veces."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT c.id FROM fin_card_cycles c JOIN fin_accounts a ON a.id = c.account_id "
        "WHERE a.account_ref = %s AND c.closing_date = %s",
        (account_ref, closing),
    )
    existe = cursor.fetchone() is not None
    cursor.close()
    return existe


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dir", default=os.path.join(EXTRACTOS_DIR, "desconocidos"))
    parser.add_argument("--commit", action="store_true", help="escribe en la BD; sin esto solo muestra")
    args = parser.parse_args()

    if not os.path.isdir(args.dir):
        raise SystemExit(f"No existe la carpeta: {args.dir}\nPasa --dir con la ruta de los PDF.")
    pdfs = sorted(f for f in os.listdir(args.dir) if f.lower().endswith(".pdf"))
    print(f"Carpeta: {args.dir}")
    print(f"PDFs: {len(pdfs)}   modo: {'COMMIT (escribe en BD)' if args.commit else 'solo lectura'}")

    conn = connect(**BDsystem.DB_CONFIG) if args.commit else None
    total = {"leidos": 0, "sin_ciclo": 0, "insertados": 0, "omitidos": 0, "otros": 0}
    for nombre in pdfs:
        ruta = os.path.join(args.dir, nombre)
        detected = detect_adapter(ruta)
        if not detected or detected[0] != "santander_tc_resumen":
            total["otros"] += 1
            regla = detected[0] if detected else "sin regla"
            print(f"\n{nombre[:40]:<40} omitido — no es resumen de tarjeta ({regla})")
            continue
        adapter = ResumenFormatoViejo(pdf_path=ruta, account_ref=detected[1])
        cycle = adapter._extract_cycle()
        if not cycle:
            total["sin_ciclo"] += 1
            print(f"\n{nombre[:40]:<40} SIN CICLO — revisar a mano")
            continue
        total["leidos"] += 1
        print(f"\n{nombre[:40]:<40} {detected[1]}")
        print(f"    cierre {cycle['prev_closing']} -> {cycle['closing']}   vence {cycle['due']}"
              f"   prox {cycle.get('next_closing')} / {cycle.get('next_due')}")
        if cycle["installments"]:
            detalle = "  ".join(f"{m:%Y-%m}={a}" for m, a in cycle["installments"])
            print(f"    cuotas a vencer ({len(cycle['installments'])}): {detalle}")
        else:
            print("    cuotas a vencer: ninguna en el PDF")
        if not args.commit:
            continue
        if ciclo_ya_cargado(conn, detected[1], cycle["closing"]):
            total["omitidos"] += 1
            print(f"    -> el cierre {cycle['closing']} ya esta en fin_card_cycles, omitido")
            continue
        stats = adapter.load(conn)
        if stats["inserted"]:
            total["insertados"] += 1
            print(f"    -> insertado: {stats['inserted']} filas")
        else:
            total["omitidos"] += 1
            print("    -> ya estaba cargado, omitido")

    if conn:
        conn.close()
    print("")
    print(f"Resumen: {total['leidos']} con ciclo | {total['sin_ciclo']} sin ciclo | {total['otros']} no-tarjeta")
    if args.commit:
        print(f"         {total['insertados']} insertados | {total['omitidos']} ya estaban")
    else:
        print("         nada escrito — volve a correr con --commit")


if __name__ == "__main__":
    main()
