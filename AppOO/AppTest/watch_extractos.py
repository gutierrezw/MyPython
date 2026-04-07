"""
CLI para procesar manualmente PDFs de la carpeta tmp/extractos/.
La lógica vive en Class_Finance.py.

Uso:
    python AppTest/watch_extractos.py          # procesa lo que haya y sale
"""

import sys
import os
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Class_Finance import scan_extractos

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)s  %(message)s")

if __name__ == "__main__":
    result = scan_extractos()
    print(result)
