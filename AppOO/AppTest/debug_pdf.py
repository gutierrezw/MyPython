"""
Inspecciona coordenadas X/Y de las primeras palabras de un PDF.
Uso: python AppTest/debug_pdf.py <ruta_pdf> [pagina=0] [max_words=80]
"""

import sys
import pdfplumber

pdf_path = sys.argv[1]
page_num = int(sys.argv[2]) if len(sys.argv) > 2 else 0
max_words = int(sys.argv[3]) if len(sys.argv) > 3 else 80

with pdfplumber.open(pdf_path) as pdf:
    page = pdf.pages[page_num]
    words = page.extract_words(x_tolerance=3, y_tolerance=3)
    print(f"Página {page_num} — {len(words)} palabras totales, mostrando {min(max_words, len(words))}")
    print(f"{'x0':>8}  {'top':>8}  texto")
    print("-" * 50)
    for w in words[:max_words]:
        print(f"{w['x0']:8.1f}  {w['top']:8.1f}  {w['text']}")
