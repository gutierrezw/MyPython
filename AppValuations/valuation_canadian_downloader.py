# valuation_canadian_downloader.py
"""
Módulo para descargar reportes financieros de empresas canadienses desde SEDAR+.

⚠️ IMPORTANTE: SEDAR+ usa JavaScript dinámico, por lo que este módulo:
1. Proporciona URLs directas a documentos específicos (cuando se conocen)
2. Guía al usuario para descargas manuales si es necesario
3. Organiza archivos descargados manualmente

Para análisis completo, se recomienda descargar:
- Annual Financial Statements (IFRS)
- Annual Information Form (AIF)
- MD&A (Management Discussion & Analysis)
"""

from Modulos_python import os, requests, json, datetime, timezone
import time

# =====================================================
# Configuración
# =====================================================
BASE_DIR = r"C:\Users\InversionesWildaga\Documents\MyPython\AppOO\EDGAR"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

# URLs directas conocidas de documentos SEDAR+ (actualizadas manualmente)
SEDAR_KNOWN_DOCUMENTS = {
    "TU": {
        "company_name": "TELUS Corporation",
        "documents": {
            "2024_AIF": {
                "name": "2024 Annual Information Form",
                "url": "https://www.sedarplus.ca/csa-party/records/document.html?id=0cf4026a1276dfe0001bc1ee3dcfa6cfcef431e828fac2da90c78d4c7eed1f64",
                "direct_pdf": "https://assets.ctfassets.net/fltupc9ltp8m/72l0ZdifQn8mkDcthbw3SH/8c0dc3a45e326646d10c7bae976a9a69/TELUS_2024_Annual_Information_Form_EN.pdf",
                "year": 2024,
                "type": "AIF"
            },
            "2024_Financials": {
                "name": "2024 Annual Financial Statements",
                "search_hint": "Buscar en SEDAR+: 'TELUS Corporation' + 'Annual financial statements' + '2024'",
                "year": 2024,
                "type": "Financial Statements"
            },
        },
        "sedar_search": "https://www.sedarplus.ca/csa-party/search/search.html?query=TELUS+Corporation"
    },
    # Agregar más empresas según se necesiten
}


# =====================================================
# Funciones principales
# =====================================================
def get_company_info(ticker: str) -> dict:
    """Obtiene información de empresa canadiense"""
    ticker = ticker.upper()

    # Si está en la lista conocida
    if ticker in SEDAR_KNOWN_DOCUMENTS:
        return SEDAR_KNOWN_DOCUMENTS[ticker]

    # Mapeo básico de tickers canadienses comunes
    known_names = {
        "RY": "Royal Bank of Canada",
        "TD": "Toronto-Dominion Bank",
        "BCE": "BCE Inc.",
        "BNS": "Bank of Nova Scotia",
        "BMO": "Bank of Montreal",
        "CNQ": "Canadian Natural Resources",
        "ENB": "Enbridge Inc.",
        "SU": "Suncor Energy Inc.",
        "CNR": "Canadian National Railway",
        "CP": "Canadian Pacific Railway",
    }

    company_name = known_names.get(ticker, f"{ticker} (empresa canadiense)")

    return {
        "company_name": company_name,
        "documents": {},
        "sedar_search": f"https://www.sedarplus.ca/csa-party/search/search.html?query={company_name.replace(' ', '+')}"
    }


def download_pdf_from_url(url: str, save_path: str, display=False) -> bool:
    """
    Descarga un PDF desde una URL directa.

    Returns:
        True si descargó exitosamente, False si no
    """
    if os.path.exists(save_path):
        if display:
            print(f"  ⏭️  Ya existe: {os.path.basename(save_path)}")
        return True

    try:
        response = requests.get(url, headers=HEADERS, timeout=30)

        if response.status_code == 200:
            # Verificar que es PDF
            content_type = response.headers.get('content-type', '')
            if 'pdf' in content_type.lower() or url.lower().endswith('.pdf'):
                with open(save_path, 'wb') as f:
                    f.write(response.content)

                if display:
                    print(f"  ✅ Descargado: {os.path.basename(save_path)}")
                return True
            else:
                if display:
                    print(f"  ⚠️  No es PDF: {content_type}")
                return False
        else:
            if display:
                print(f"  ❌ HTTP {response.status_code}: {os.path.basename(save_path)}")
            return False

    except Exception as e:
        if display:
            print(f"  ❌ Error: {str(e)[:60]}")
        return False


def download_canadian_reports(ticker: str, display=False) -> bool:
    """
    Descarga reportes financieros de una empresa canadiense desde SEDAR+.

    Args:
        ticker: Ticker de la empresa (ej: TU, RY, BCE)
        display: Si mostrar mensajes de progreso

    Returns:
        True si encontró/descargó archivos, False si no
    """
    ticker = ticker.upper()
    company_info = get_company_info(ticker)

    if display:
        print("=" * 70)
        print(f"📊 {company_info['company_name']}")
        print("=" * 70)
        print(f"🇨🇦 Empresa Canadiense - Reportes en SEDAR+ (IFRS)\n")

    # Crear directorio
    ticker_dir = os.path.join(BASE_DIR, f"{ticker}_Canadian_Reports")
    os.makedirs(ticker_dir, exist_ok=True)

    downloaded_files = []
    documents = company_info.get('documents', {})

    if not documents:
        # No hay URLs directas conocidas
        if display:
            print(f"⚠️  No hay URLs directas configuradas para {ticker}")
            print(f"\n📋 Para descargar manualmente:")
            print(f"   1. Visita: {company_info['sedar_search']}")
            print(f"   2. Busca documentos:")
            print(f"      - Annual financial statements (últimos 3 años)")
            print(f"      - Annual information form (últimos 3 años)")
            print(f"      - MD&A (Management's Discussion & Analysis)")
            print(f"   3. Guarda los PDFs en: {ticker_dir}")
            print(f"\n💡 Después de descargar, ejecuta el análisis normalmente.\n")

        # Guardar metadata con instrucciones
        metadata_path = os.path.join(ticker_dir, "metadata.json")
        metadata = {
            "ticker": ticker,
            "company_name": company_info['company_name'],
            "company_type": "canadian",
            "standards": "IFRS",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sedar_search_url": company_info['sedar_search'],
            "manual_download_required": True,
            "instructions": "Descarga manualmente desde SEDAR+ y coloca PDFs en este directorio"
        }

        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=4, ensure_ascii=False)

        return False

    # Intentar descargar documentos conocidos
    if display:
        print(f"📥 Descargando documentos conocidos...\n")

    for doc_id, doc_info in documents.items():
        doc_name = doc_info['name']
        filename = f"{ticker}_{doc_info['year']}_{doc_info['type'].replace(' ', '_')}.pdf"
        save_path = os.path.join(ticker_dir, filename)

        # Intentar con URL directa de PDF si existe
        if 'direct_pdf' in doc_info:
            success = download_pdf_from_url(doc_info['direct_pdf'], save_path, display)
            if success:
                downloaded_files.append({
                    "name": doc_name,
                    "file": filename,
                    "path": save_path,
                    "year": doc_info['year'],
                    "type": doc_info['type']
                })
        elif 'search_hint' in doc_info:
            if display:
                print(f"  ℹ️  {doc_name}: {doc_info['search_hint']}")

    # Guardar metadata
    metadata_path = os.path.join(ticker_dir, "metadata.json")
    metadata = {
        "ticker": ticker,
        "company_name": company_info['company_name'],
        "company_type": "canadian",
        "standards": "IFRS",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "sedar_search_url": company_info.get('sedar_search'),
        "downloaded_files": downloaded_files,
    }

    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=4, ensure_ascii=False)

    if display:
        if downloaded_files:
            print(f"\n✅ Descargados: {len(downloaded_files)} archivos")
        print(f"📂 Directorio: {ticker_dir}")
        print(f"📝 Metadata: {metadata_path}\n")

    return len(downloaded_files) > 0


# =====================================================
# Entry Point
# =====================================================
if __name__ == "__main__":
    print("=" * 70)
    ticker = input("💼 Ingrese ticker de empresa canadiense (TU, RY, BCE, etc.): ").strip().upper()
    print("=" * 70 + "\n")

    download_canadian_reports(ticker, display=True)
