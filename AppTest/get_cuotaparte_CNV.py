import requests
from bs4 import BeautifulSoup
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import xml.etree.ElementTree as ET
import time
import json
import os


def v1get_driver(url_visor, path):

    #link_visor = "https://aif2.cnv.gov.ar/Presentations/publicview/2344B796-3352-4465-815D-0C7A0BAC97A1"

    # Configurar Selenium
    driver_path = "C:/Users/InversionesWildaga/Drivers/chromedriver.exe"

    # === INICIAR SELENIUM CON CHROME ===
    options = Options()
    options.add_argument("--headless")  # Opcional: sin abrir ventana
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(service=Service(driver_path), options=options)

    print("🌐 Abriendo visor de CNV...")
    driver.get(url_visor)
    time.sleep(5)  # Esperar a que cargue la página

    try:
        # === EXTRAER LA VARIABLE JAVASCRIPT 'presentation' ===
        print("🔍 Extrayendo variable 'presentation'...")
        presentation_xml = driver.execute_script("return presentation;")
        driver.quit()

        # === PARSEAR EL XML PARA ENCONTRAR GUID Y NOMBRE DE ARCHIVO ===
        root = ET.fromstring(presentation_xml)
        prop = root.find(".//propiedad[@id='PlaVDC']")
        if prop is None:
            raise ValueError("No se encontró la propiedad PlaVDC")

        lista_archivos = eval(prop.text)  # texto es una lista JSON
        guid = lista_archivos[0]['guid']
        nombre_archivo = lista_archivos[0]['nombreArchivo']

        print(f"📁 Archivo encontrado: {nombre_archivo}")
        print(f"🔗 GUID de descarga: {guid}")

        # === CONSTRUIR Y DESCARGAR EL ARCHIVO EXCEL ===
        url_descarga = f"https://aif2.cnv.gov.ar/Descarga/{guid}"
        print(f"📥 Descargando desde: {url_descarga}")
        response = requests.get(url_descarga)
        time.sleep(5)

        print(f"📦 Código HTTP: {response.status_code}")
        print(f"📦 Tamaño del contenido: {len(response.content)} bytes")

        # Si el contenido no es binario, mostrar los primeros bytes
        try:
            print("🧾 Primeros 200 bytes del contenido:")
            print(response.content[:200].decode("utf-8"))
        except:
            print("🧾 Contenido binario no imprimible.")

        with open(nombre_archivo, "wb") as f:
            f.write(response.content)

        print(f"✅ Archivo guardado como: {nombre_archivo}")

    except Exception as e:
        print(f"❌ Error durante el proceso: {e}")
        driver.quit()

def v2get_driver(url_visor, path):

    # Configurar Selenium
    driver_path = "C:/Users/InversionesWildaga/Drivers/chromedriver.exe"

    # === INICIAR SELENIUM CON CHROME ===
    options = Options()
    options.add_argument("--start-maximized")

    driver = webdriver.Chrome(service=Service(driver_path), options=options)

    # URL del visor de CNV
    print("🌐 Abriendo visor de CNV...")
    driver.get(url_visor)

    # Esperar que cargue la página completamente
    time.sleep(5)

    try:
        # Buscar y hacer clic en el botón que dice "Descargar"
        boton_descarga = driver.find_element(By.LINK_TEXT, "Descargar")
        boton_descarga.click()
        print("✅ Clic en botón de descarga realizado.")

        # Esperar unos segundos para permitir la descarga
        time.sleep(5)

    except Exception as e:
        print("❌ No se encontró el botón de descarga:", e)

    driver.quit()

def v3get_driver(url_visor, path):

    # Configurar Selenium
    driver_path = "C:/Users/InversionesWildaga/Drivers/chromedriver.exe"

    # Cambiá esto a tu carpeta deseada
    options = webdriver.ChromeOptions()
    prefs = {"download.default_directory": r"C:\Users\InversionesWildaga\Downloads"}
    options.add_experimental_option("prefs", prefs)

    # Iniciar Chrome
    driver = webdriver.Chrome(options=options)

    # Ir al visor de la CNV
    driver.get(url_visor)

    # Esperar carga total
    time.sleep(5)

    # Verificar si hay iframe
    iframes = driver.find_elements(By.TAG_NAME, "iframe")
    print(driver.iframes)
    if iframes:
        driver.switch_to.frame(iframes[0])  # Cambiamos al primer iframe

    try:
        # Esperamos a que el botón esté disponible
        boton = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.XPATH, '//button[contains(text(), "Descargar")]'))

        )
        boton.click()
        print("✅ Archivo descargado correctamente.")
    except Exception as e:
        print("❌ No se encontró el botón de descarga:", e)

    # Esperar para terminar la descarga
    time.sleep(5)
    driver.quit()

def v4get_driver(url_visor, path):
    options = Options()
    options.add_argument('--headless=new')
    driver = webdriver.Chrome(options=options)

    try:
        driver.get(url_visor)
        time.sleep(5)  # Esperar que cargue

        enlaces = driver.find_elements(By.CSS_SELECTOR, 'a.downloadFile')

        for enlace in enlaces:
            guid = enlace.get_attribute("data-guid")
            nombre_archivo = enlace.get_attribute("data-name")

            if not guid or not nombre_archivo:
                continue

            url_descarga = f"https://aif2.cnv.gov.ar/BlobWebService.svc/DownloadBlob/{guid}"
            print(f"📎 Descargando: {nombre_archivo} desde {url_descarga}")

            response = requests.get(url_descarga)
            if response.status_code == 200:
                with open(f"{carpeta_destino}/{nombre_archivo}", "wb") as f:
                    f.write(response.content)
                print("✅ Archivo guardado:", nombre_archivo)
            else:
                print("❌ Error al descargar", nombre_archivo)

    finally:
        driver.quit()

def get_driver(url_visor, path):

    # os.makedirs(path, exist_ok=True)

    options = Options()
    options.add_argument('--headless=new')  # Sin mostrar navegador
    driver = webdriver.Chrome(options=options)

    try:
        driver.get(url_visor)
        time.sleep(5)  # Esperar que cargue todo

        enlaces = driver.find_elements(By.CSS_SELECTOR, 'a.downloadFile')

        for enlace in enlaces:
            guid = enlace.get_attribute("data-guid")
            nombre_archivo = enlace.get_attribute("data-name")

            if not guid or not nombre_archivo:
                continue

            url_descarga = f"https://blob.cnv.gov.ar/BlobWebService.svc/DownloadBlob/{guid}"
            print(f"📎 Descargando: {nombre_archivo} - url_CNV:: {url_descarga}")

            response = requests.get(url_descarga)
            if response.status_code == 200:
                ruta_completa = os.path.join(carpeta_destino, nombre_archivo)
                with open(ruta_completa, "wb") as f:
                    f.write(response.content)
                print(f"✅ Guardado en: {ruta_completa}")
            else:
                print(f"❌ Error ({response.status_code}) al descargar: {nombre_archivo}")

    finally:
        driver.quit()

def url_CNV(hasta):
    ipath = os.getcwd()
    ipath += '\\tmp\\'
    url = "https://www.cnv.gov.ar/SitioWeb/FondosComunesInversion/CuotaPartes"

    fecha_obj = datetime.strptime(hasta, "%d %b %Y")

    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")

    # Buscar el enlace con esa fecha
    for a in soup.find_all("a", href=True):
        fecha_link = a.text.strip().lower()
        try:
            fecha_src = datetime.strptime(fecha_link, "%d %b %Y")
            link = a['href']
            print(f'link - {link} :: {fecha_src}')
            get_driver(link, ipath)

            if fecha_src == fecha_obj:
                break
        except ValueError:
            continue  # Ignora si el texto no es una fecha

if __name__ == '__main__':
    fecha = "02 jun 2025"
    url_CNV(fecha)