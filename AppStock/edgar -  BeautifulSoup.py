from bs4 import BeautifulSoup
from pathlib import Path
import re


def inspect_ixbrl_html(path, ScanContex=False):
    p = Path(path)
    text = p.read_text(encoding="utf-8", errors="ignore")

    soup = BeautifulSoup(text, "lxml")

    print("\n========================================================")
    print(f"📌 ANALIZANDO ARCHIVO: {p.name}")
    print("========================================================\n")

    # ---------------------------------------------------------
    # 1) Mostramos todos los TAG NAMES que existen en el archivo
    # ---------------------------------------------------------
    tag_names = set([t.name for t in soup.find_all(True)])
    print("🔍 TAGS DETECTADOS:")
    for t in sorted(tag_names):
        print(" -", t)
    print("\nTotal tags:", len(tag_names))

    # ---------------------------------------------------------
    # 2) Buscamos todos los elementos que posiblemente sean I-XBRL
    # ---------------------------------------------------------
    print("\n========================================================")
    print("🔍 POSIBLES TAGS INLINE I-XBRL ENCONTRADOS")
    print("========================================================")

    candidates = []

    # A) tags ix:...
    candidates.extend(soup.find_all(lambda t: t.name and "ix:" in t.name.lower()))

    # B) tags con name="us-gaap:*"
    candidates.extend(soup.find_all(lambda t: t.has_attr("name")))

    # C) tags con data-*
    candidates.extend(
        soup.find_all(lambda t: any(k.startswith("data-") for k in t.attrs))
    )

    # Eliminar duplicados
    uniq = []
    seen = set()
    for t in candidates:
        if id(t) not in seen:
            uniq.append(t)
            seen.add(id(t))

    print(f"Total candidatos encontrados: {len(uniq)}\n")

    if ScanContex:

        # ---------------------------------------------------------
        # 3) Mostrar ejemplos concretos (máx 40)
        # ---------------------------------------------------------
        for i, tag in enumerate(uniq[:40]):
            print(f"\n[{i+1}] TAG:")
            print(" - name:", tag.name)
            print(" - atributos:", tag.attrs)
            text = tag.get_text(" ", strip=True)
            print(" - texto:", text[:200])
            print(" - HTML:", str(tag)[:400])

        # ---------------------------------------------------------
        # 4) Buscar contextRef/unitRef donde sea que aparezcan
        # ---------------------------------------------------------
        print("\n========================================================")
        print("🔍 ATRIBUTOS contextRef / unitRef")
        print("========================================================")

        ctx_refs = soup.find_all(
            lambda t: t.has_attr("contextref") or t.has_attr("contextRef")
        )
        unit_refs = soup.find_all(
            lambda t: t.has_attr("unitref") or t.has_attr("unitRef")
        )

        print(f"Total contextRef encontrados: {len(ctx_refs)}")
        print(f"Total unitRef encontrados: {len(unit_refs)}")

        if ctx_refs:
            print("\nEjemplo contextRef:")
            print(str(ctx_refs[0])[:400])

        if unit_refs:
            print("\nEjemplo unitRef:")
            print(str(unit_refs[0])[:400])

    print("\n========================================================")
    print("FIN DE INSPECCIÓN")
    print("========================================================\n")


# ---------------------------------------------------------
# EJEMPLO DE USO
# ---------------------------------------------------------
if __name__ == "__main__":
    # CAMBIA ESTA RUTA POR CUALQUIER ARCHIVO .HTM DESCARGADO
    archivo = r"C:\Users\InversionesWildaga\Documents\MyPython\AppOO\EDGAR\HASI_EDGAR_Files\10Q_Filings\hasi-20250930.htm"
    archivo = r"C:\Users\InversionesWildaga\Documents\MyPython\AppOO\EDGAR\HASI_EDGAR_Files\10Q_Filings\hasi-20250331.htm"
    inspect_ixbrl_html(archivo)
