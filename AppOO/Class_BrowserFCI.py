import os
import logging

from datetime import date

from Modulos_python import sync_playwright, PlaywrightTimeout
from Modulos_Mysql import BDsystem

_logger = logging.getLogger("BrowserFCI")

_TIMEOUT = 30_000  # ms por paso


class BrowserFCI:
    # === BBVA Argentina — ajustar selectores con F12 ===
    _BBVA_URL_LOGIN = "https://www.bbvaargentina.com"
    _BBVA_SEL_USER = "#SELECTOR_TODO"  # campo usuario / DNI
    _BBVA_SEL_PASS = "#SELECTOR_TODO"  # campo clave
    _BBVA_SEL_OK = "#SELECTOR_TODO"  # botón ingresar
    _BBVA_URL_MOV = "#URL_TODO"  # URL de la sección movimientos
    _BBVA_SEL_DESDE = "#SELECTOR_TODO"  # input fecha desde
    _BBVA_SEL_HASTA = "#SELECTOR_TODO"  # input fecha hasta
    _BBVA_SEL_DL = "#SELECTOR_TODO"  # botón / link descargar Excel

    # === Santander Argentina — ajustar selectores con F12 ===
    _SANT_URL_LOGIN = "https://www.santander.com.ar"
    _SANT_SEL_USER = "#SELECTOR_TODO"
    _SANT_SEL_PASS = "#SELECTOR_TODO"
    _SANT_SEL_OK = "#SELECTOR_TODO"
    _SANT_URL_MOV = "#URL_TODO"
    _SANT_SEL_DESDE = "#SELECTOR_TODO"
    _SANT_SEL_HASTA = "#SELECTOR_TODO"
    _SANT_SEL_DL = "#SELECTOR_TODO"

    def download_bbva(self, desde: date, destino: str, prefijo: str) -> str | None:
        sesion = BDsystem.get_sesion_by_vehiculo("BBVA.ARS")
        usuario = sesion["userapi"]
        clave = sesion["userpass"]
        hasta = date.today()
        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=False)
                ctx = browser.new_context(accept_downloads=True)
                page = ctx.new_page()

                page.goto(self._BBVA_URL_LOGIN, timeout=_TIMEOUT)
                page.fill(self._BBVA_SEL_USER, usuario)
                page.fill(self._BBVA_SEL_PASS, clave)
                page.click(self._BBVA_SEL_OK)
                page.wait_for_load_state("networkidle", timeout=_TIMEOUT)

                page.goto(self._BBVA_URL_MOV, timeout=_TIMEOUT)
                page.wait_for_load_state("networkidle", timeout=_TIMEOUT)

                page.fill(self._BBVA_SEL_DESDE, desde.strftime("%d/%m/%Y"))
                page.fill(self._BBVA_SEL_HASTA, hasta.strftime("%d/%m/%Y"))

                nombre = f"{prefijo}{date.today().strftime('%Y%m%d')}.xls"
                ruta = os.path.join(destino, nombre)
                with page.expect_download(timeout=_TIMEOUT) as dl_info:
                    page.click(self._BBVA_SEL_DL)
                dl_info.value.save_as(ruta)
                browser.close()

                _logger.warning(f"download_bbva: {ruta}")
                return ruta

        except PlaywrightTimeout as e:
            _logger.error(f"download_bbva timeout: {e}")
        except Exception as e:
            _logger.error(f"download_bbva: {e}")
        return None

    def download_santander(self, desde: date, destino: str, prefijo: str) -> str | None:
        sesion = BDsystem.get_sesion_by_vehiculo("SANT.ARS")
        usuario = sesion["userapi"]
        clave = sesion["userpass"]
        hasta = date.today()
        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=False)
                ctx = browser.new_context(accept_downloads=True)
                page = ctx.new_page()

                page.goto(self._SANT_URL_LOGIN, timeout=_TIMEOUT)
                page.fill(self._SANT_SEL_USER, usuario)
                page.fill(self._SANT_SEL_PASS, clave)
                page.click(self._SANT_SEL_OK)
                page.wait_for_load_state("networkidle", timeout=_TIMEOUT)

                page.goto(self._SANT_URL_MOV, timeout=_TIMEOUT)
                page.wait_for_load_state("networkidle", timeout=_TIMEOUT)

                page.fill(self._SANT_SEL_DESDE, desde.strftime("%d/%m/%Y"))
                page.fill(self._SANT_SEL_HASTA, hasta.strftime("%d/%m/%Y"))

                nombre = f"{prefijo}{date.today().strftime('%Y%m%d')}.xlsx"
                ruta = os.path.join(destino, nombre)
                with page.expect_download(timeout=_TIMEOUT) as dl_info:
                    page.click(self._SANT_SEL_DL)
                dl_info.value.save_as(ruta)
                browser.close()

                _logger.warning(f"download_santander: {ruta}")
                return ruta

        except PlaywrightTimeout as e:
            _logger.error(f"download_santander timeout: {e}")
        except Exception as e:
            _logger.error(f"download_santander: {e}")
        return None
