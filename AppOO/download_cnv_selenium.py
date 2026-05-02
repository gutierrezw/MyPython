#!/usr/bin/env python3
"""
Descargar archivos Excel de CNV usando Selenium (navegador automatizado)

REQUISITOS:
pip install selenium
pip install webdriver-manager

USO COMO FUNCIÓN:
    from descargar_cnv_selenium import descargar_cnv_hoy
    resultado = descargar_cnv_hoy("10-12-2025")

USO COMO SCRIPT:
    python descargar_cnv_selenium.py 10-12-2025
"""

import logging
import os
import re
import sys
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup

_logger = logging.getLogger("FondosInversion")
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


def parse_fecha(fecha_str, display_log=False):
    """Convierte '11 dic. 2025' a datetime"""
    meses = {
        "ene": 1,
        "feb": 2,
        "mar": 3,
        "abr": 4,
        "may": 5,
        "jun": 6,
        "jul": 7,
        "ago": 8,
        "sep": 9,
        "oct": 10,
        "nov": 11,
        "dic": 12,
    }

    parts = fecha_str.strip().split()
    day = int(parts[0])
    month = meses[parts[1].replace(".", "")]
    year = int(parts[2])

    return datetime(year, month, day)


def obtener_documentos():
    """Obtiene lista de documentos disponibles de CNV"""
    url = "https://www.cnv.gov.ar/SitioWeb/FondosComunesInversion/CuotaPartes"

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content, "html.parser")

    documentos = []
    table = soup.find("table")

    if not table:
        return documentos

    for row in table.find_all("tr")[1:]:
        cols = row.find_all("td")
        if len(cols) >= 4:
            fecha_link = cols[0].find("a")
            if fecha_link:
                fecha_str = fecha_link.get_text(strip=True)
                href = fecha_link.get("href", "")

                uuid_match = re.search(
                    r"([A-F0-9]{8}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{12})",
                    href,
                    re.IGNORECASE,
                )

                if uuid_match:
                    uuid = uuid_match.group(1)
                    descripcion = cols[2].get_text(strip=True)
                    id_doc = cols[3].get_text(strip=True)

                    try:
                        fecha_dt = parse_fecha(fecha_str)
                        documentos.append(
                            {
                                "fecha": fecha_str,
                                "fecha_dt": fecha_dt,
                                "uuid": uuid,
                                "id": id_doc,
                                "descripcion": descripcion,
                            }
                        )
                    except:
                        pass

    return documentos


def descargar_excel_selenium(uuid, id_doc, fecha_str, directorio, display_log=False):
    """Descarga el archivo usando Selenium (navegador automatizado)"""

    if display_log:
        print(f"  📥 {id_doc} ({fecha_str})...", end=" ", flush=True)

    # Configurar Chrome
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Sin ventana visible
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--safebrowsing-disable-download-protection")

    # Configurar carpeta de descargas
    prefs = {
        "download.default_directory": os.path.abspath(directorio),
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": False,
        "safebrowsing.disable_download_protection_for_urls": ["https://aif2.cnv.gov.ar"],
    }
    chrome_options.add_experimental_option("prefs", prefs)

    try:
        # Iniciar navegador
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

        # Ir a la página
        url = f"https://aif2.cnv.gov.ar/Presentations/publicview/{uuid}"
        driver.get(url)

        # Esperar a que cargue el contenido (máximo 15 segundos)
        wait = WebDriverWait(driver, 15)

        # Buscar botón de descarga (varios selectores posibles)
        selectores = [
            "//a[contains(@href, 'GetFile')]",
            "//a[contains(@href, 'export')]",
            "//a[contains(@href, 'download')]",
            "//button[contains(text(), 'Excel')]",
            "//a[contains(text(), 'Excel')]",
            "//i[contains(@class, 'excel')]/..",
            "//i[contains(@class, 'download')]/..",
        ]

        boton_descarga = None
        for selector in selectores:
            try:
                boton_descarga = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                break
            except:
                continue

        if not boton_descarga:
            if display_log:
                print("⚠️  Botón no encontrado")
            driver.quit()
            return False

        # Hacer clic en el botón
        boton_descarga.click()

        # Esperar a que se complete la descarga (poll hasta 90s)
        excels_previos = {f for f in os.listdir(directorio) if f.endswith((".xlsx", ".xls"))}
        timeout = 90
        t0 = time.time()
        while time.time() - t0 < timeout:
            en_dir = os.listdir(directorio)
            nuevos_excel = [f for f in en_dir if f.endswith((".xlsx", ".xls")) and f not in excels_previos]
            en_progreso = [f for f in en_dir if f.endswith(".crdownload")]
            if nuevos_excel and not en_progreso:
                break
            time.sleep(1)

        # Limpiar archivos antiguos antes de renombrar
        archivos = os.listdir(directorio)
        archivos_excel = [f for f in archivos if f.endswith(".xlsx") or f.endswith(".xls")]

        if archivos_excel:
            # Tomar el más reciente
            archivos_excel.sort(
                key=lambda x: os.path.getmtime(os.path.join(directorio, x)),
                reverse=True,
            )
            archivo_descargado = archivos_excel[0]

            # Limpiar nombre: remover " (1)", " (2)", etc. que Chrome agrega cuando hay duplicados
            nombre_limpio = re.sub(r"\s*\(\d+\)", "", archivo_descargado)  # Remover (1), (2), etc.

            # Si tiene formato de fecha al principio (YYYYMMDD), usarlo
            # Si no, extraer fecha de fecha_str y agregar al inicio
            if not re.match(r"^\d{8}_", nombre_limpio):
                # Convertir fecha_str "10 dic. 2025" a "20251210"
                try:
                    fecha_dt = parse_fecha(fecha_str)
                    fecha_formato = fecha_dt.strftime("%Y%m%d")
                    # Agregar fecha al inicio del nombre limpio
                    nombre_limpio = f"{fecha_formato}_{nombre_limpio}"
                except:
                    pass

            nuevo_path = os.path.join(directorio, nombre_limpio)

            # Eliminar archivo antiguo si existe con el mismo nombre final
            if os.path.exists(nuevo_path) and nuevo_path != os.path.join(directorio, archivo_descargado):
                os.remove(nuevo_path)

            # Renombrar el nuevo archivo
            os.rename(os.path.join(directorio, archivo_descargado), nuevo_path)

            driver.quit()
            return nombre_limpio  # Retornar el nombre del archivo
        else:
            if display_log:
                print("⚠️  Archivo no descargado")
            driver.quit()
            return False

    except Exception as e:
        _logger.error(f"descargar_excel_selenium(): {str(e)[:80]}")
        try:
            driver.quit()
        except:
            pass
        return False


def descargar_cnv_hoy(fecha_str):
    """
    Descarga el archivo Excel más reciente de CNV para una fecha específica.

    Args:
        fecha_str: Fecha en formato "DD-MM-YYYY" o "YYYY-MM-DD"

    Returns:
        dict: {
            'success': bool,
            'archivo': str (ruta completa al archivo descargado),
            'exitosas': int,
            'fallidas': int,
            'total': int
        }
    """
    # Parsear fecha
    try:
        parts = fecha_str.split("-")
        if len(parts[0]) == 4:
            fecha_objetivo = datetime(int(parts[0]), int(parts[1]), int(parts[2]))
        else:
            fecha_objetivo = datetime(int(parts[2]), int(parts[1]), int(parts[0]))
    except:
        return {
            "success": False,
            "error": f"Formato de fecha inválido: {fecha_str}",
            "archivo": None,
        }

    # Crear directorio tmp
    directorio = "tmp"
    if not os.path.exists(directorio):
        os.makedirs(directorio)

    # Obtener documentos
    documentos = obtener_documentos()

    if not documentos:
        return {
            "success": False,
            "error": "No se encontraron documentos en CNV",
            "archivo": None,
        }

    # Filtrar documentos con fecha >= fecha_objetivo (inmediata superior o igual)
    docs_validos = [d for d in documentos if d["fecha_dt"] >= fecha_objetivo]

    if not docs_validos:
        return {
            "success": False,
            "error": f'No hay documentos posteriores o iguales a {fecha_objetivo.strftime("%d/%m/%Y")}',
            "archivo": None,
        }

    # Ordenar por fecha ascendente para obtener la inmediata superior
    docs_validos.sort(key=lambda x: x["fecha_dt"])

    # Tomar la fecha inmediata superior (primera en la lista ordenada)
    fecha_inmediata_superior = docs_validos[0]["fecha_dt"]

    # Obtener todos los documentos de esa fecha
    docs_a_descargar = [d for d in docs_validos if d["fecha_dt"] == fecha_inmediata_superior]

    # Si hay múltiples documentos, tomar el más reciente (último en aparecer en la lista)
    # La lista viene ordenada cronológicamente, el último es el más reciente
    docs_a_descargar.reverse()  # Invertir para intentar descargar el más reciente primero

    # Descargar (solo el primero exitoso, que será el más reciente)
    exitosas = 0
    fallidas = 0
    archivo_path = None
    nombre_archivo = None

    for doc in docs_a_descargar:
        resultado = descargar_excel_selenium(doc["uuid"], doc["id"], doc["fecha"], directorio)
        if resultado:  # resultado es el nombre del archivo si tuvo éxito
            exitosas += 1
            nombre_archivo = resultado
            archivo_path = os.path.abspath(os.path.join(directorio, nombre_archivo))
            break  # Solo necesitamos uno exitoso (el más reciente)
        else:
            fallidas += 1

        time.sleep(1)

    return {
        "success": exitosas > 0,
        "archivo": archivo_path,
        "nombre": nombre_archivo,
        "exitosas": exitosas,
        "fallidas": fallidas,
        "total": len(docs_a_descargar),
    }


def main():
    """Función principal para uso como script desde línea de comandos"""
    if len(sys.argv) < 2:
        print("Uso: python descargar_cnv_selenium.py DD-MM-YYYY")
        print("\nEjemplo:")
        print("  python descargar_cnv_selenium.py 10-12-2025")
        print("\nREQUISITOS:")
        print("  pip install selenium webdriver-manager")
        sys.exit(1)

    fecha_str = sys.argv[1]

    print(f"\n📋 Buscando documentos CNV del {fecha_str}...\n")

    resultado = descargar_cnv_hoy(fecha_str)

    if resultado["success"]:
        print(f"\n✅ Descarga exitosa!")
        print(f"   Archivo: {resultado['archivo']}")
        print(f"   Documentos procesados: {resultado['exitosas']}/{resultado['total']}\n")
    else:
        print(f"\n❌ Error: {resultado.get('error', 'Descarga fallida')}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
