"""
Que saldo publica cada extracto, y con que coordenada. Solo lee PDFs: no toca la BD ni mueve archivos.

    python AppTest\\run_saldo_probe.py                 -> los PDF de tmp\\extractos y de desconocidos\\
    python AppTest\\run_saldo_probe.py <carpeta>
    python AppTest\\run_saldo_probe.py <archivo.pdf>

Para cada PDF imprime el adaptador detectado, las lineas que mencionan SALDO con la coordenada X de cada importe, y
lo que devolveria parse_balances() con el x_max que usa ese adaptador. Sirve para calibrar una clase nueva y para
confirmar, antes de soltar un PDF en extractos\\, que el saldo va a entrar.
"""

import json
import os
import re
import sys

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

from Modulos_python import pdfplumber
from Class_Finance import DESCONOCIDOS_DIR, EXTRACTOS_DIR, detect_adapter, parse_balances

# x_max con el que cada adaptador llama a parse_balances(). None = todavia no captura saldo.
X_MAX_POR_SECCION = {
    "bbva_cuenta": 10000.0,
    "bbva_ahorro": 10000.0,
    "bbva_tc": 530.0,
    "santander_tc_resumen": 500.0,
}
RE_IMPORTE = re.compile(r"^\$?-?\d{1,3}(?:\.\d{3})*,\d{2}$")


def words_to_lines(words, y_tol=3.0):
    """Mismo agrupamiento por fila que usan los adaptadores."""
    if not words:
        return []
    lines, current = [], [words[0]]
    for w in words[1:]:
        if abs(w["top"] - current[0]["top"]) <= y_tol:
            current.append(w)
        else:
            lines.append(sorted(current, key=lambda x: x["x0"]))
            current = [w]
    lines.append(sorted(current, key=lambda x: x["x0"]))
    return lines


def probe(ruta):
    det = detect_adapter(ruta)
    seccion = det[0] if det else None
    x_max = X_MAX_POR_SECCION.get(seccion)
    print("")
    print("=== %s" % os.path.basename(ruta))
    print("    adaptador: %s   cuenta: %s   x_max: %s" % (
        seccion or "NO DETECTADO", (det[1] if det else "-") or "multi-seccion",
        x_max if x_max else "no captura saldo todavia"))
    with pdfplumber.open(ruta) as pdf:
        hojas = [words_to_lines(p.extract_words(x_tolerance=3, y_tolerance=3)) for p in pdf.pages]
    print("    hojas: %d" % len(hojas))
    todas = []
    for n, lineas in enumerate(hojas, 1):
        todas.extend(lineas)
        for linea in lineas:
            texto = " ".join(w["text"].replace("_", "") for w in linea)
            if "SALDO" not in texto.upper():
                continue
            importes = ["%s@x%d" % (w["text"].replace("_", ""), int(w["x0"]))
                        for w in linea if RE_IMPORTE.match(w["text"].replace("_", ""))]
            print("    p%-2d %-58s | %s" % (n, texto[:58], "  ".join(importes) or "(sin importe)"))
    prev, curr = parse_balances(todas, x_max=x_max or 10000.0)
    print("    -> balance_prev=%s  balance_curr=%s" % (prev, curr))
    if len(hojas) > 2 and parse_balances(hojas[0] + hojas[-1], x_max=x_max or 10000.0) != (prev, curr):
        # el resumen de tarjeta solo mira la hoja 1 y la ultima; aca se miran todas
        print("    NOTA: con solo la hoja 1 y la ultima da otro resultado — el saldo cae en una hoja del medio")
    if x_max is None and (prev is not None or curr is not None):
        print("    NOTA: el PDF publica saldo y este adaptador todavia no lo guarda")


def main(objetivo=None):
    if objetivo and os.path.isfile(objetivo):
        probe(objetivo)
        return
    carpetas = [objetivo] if objetivo else [EXTRACTOS_DIR, DESCONOCIDOS_DIR]
    total = 0
    for carpeta in carpetas:
        if not os.path.isdir(carpeta):
            print("(no existe: %s)" % carpeta)
            continue
        print("")
        print("### %s" % carpeta)
        for nombre in sorted(f for f in os.listdir(carpeta) if f.lower().endswith(".pdf")):
            probe(os.path.join(carpeta, nombre))
            total += 1
    print("")
    print("%d PDF revisados" % total)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
