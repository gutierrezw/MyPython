import asyncio
import os
import logging

from datetime import date

from Modulos_Mysql import FinanceScreen

_logger = logging.getLogger("BrowserFCI")

_TIMEOUT = 30_000
_MODAL_WAIT = 5_000


class BrowserFCI:

    # ── BBVA Argentina ────────────────────────────────────────────────────
    _BBVA_URL_LOGIN = "https://online.bbva.com.ar/fnetcore/login/index.html"
    _BBVA_BTN_LOGIN = "Ingresar"

    # ── Santander Argentina — pendiente ───────────────────────────────────
    _SANT_URL_LOGIN = "https://www.santander.com.ar"
    _SANT_SEL_USER = "#SELECTOR_TODO"
    _SANT_SEL_PASS = "#SELECTOR_TODO"
    _SANT_SEL_OK = "#SELECTOR_TODO"
    _SANT_URL_MOV = "#URL_TODO"
    _SANT_SEL_DESDE = "#SELECTOR_TODO"
    _SANT_SEL_HASTA = "#SELECTOR_TODO"
    _SANT_SEL_DL = "#SELECTOR_TODO"

    # ── Helpers async BBVA ────────────────────────────────────────────────

    async def _wait_nav(self, page):
        await page.wait_for_load_state("domcontentloaded", timeout=_TIMEOUT)
        await page.wait_for_timeout(1_500)

    async def _bbva_login(self, page, nro_doc: str, usuario: str, clave: str):
        """Login BBVA. Maneja form completo (DNI+Usuario+Clave) o solo-Clave."""
        from playwright.async_api import TimeoutError as AsyncTimeout

        await page.goto(self._BBVA_URL_LOGIN, wait_until="domcontentloaded", timeout=_TIMEOUT)

        campo_pass = page.locator("input[name='password']")
        await campo_pass.wait_for(state="visible", timeout=_TIMEOUT)

        campo_user = page.locator("input[name='username']")
        try:
            await campo_user.wait_for(state="visible", timeout=3_000)
            if nro_doc:
                await page.evaluate(
                    """(val) => {
                        function findInput(root) {
                            for (const el of root.querySelectorAll('*')) {
                                if (el.tagName === 'INPUT' && (el.name === 'document' || el.name === 'nroDoc'
                                        || (el.placeholder || '').includes('documento'))) {
                                    el.value = val;
                                    el.dispatchEvent(new Event('input', {bubbles: true}));
                                    el.dispatchEvent(new Event('change', {bubbles: true}));
                                    return true;
                                }
                                if (el.shadowRoot && findInput(el.shadowRoot)) return true;
                            }
                            return false;
                        }
                        findInput(document);
                    }""",
                    nro_doc,
                )
            await campo_user.fill(usuario)
        except AsyncTimeout:
            pass  # form abreviado — solo pide Clave

        await campo_pass.fill(clave)
        await page.get_by_role("button", name=self._BBVA_BTN_LOGIN).click()
        await self._wait_nav(page)

        try:
            from playwright.async_api import TimeoutError as AsyncTimeout2

            btn_no = page.get_by_role("button", name="No me interesa")
            await btn_no.wait_for(state="visible", timeout=_MODAL_WAIT)
            await btn_no.click()
            await self._wait_nav(page)
            _logger.warning("_bbva_login: modal promocional descartado")
        except Exception:
            pass

    async def _bbva_navegar_movimientos(self, page):
        """Desde el dashboard navega hasta la pantalla Movimientos de FCI."""
        await page.locator("p", has_text="Total de inversiones en pesos").click()
        await self._wait_nav(page)
        await page.locator('[data-testid="moreMovements"]').get_by_role("button").first.click()
        await self._wait_nav(page)

    async def _bbva_async(
        self, profile_dir: str, nro_doc: str, usuario: str, clave: str, destino: str, prefijo: str
    ) -> str | None:
        from playwright.async_api import async_playwright, TimeoutError as AsyncTimeout

        try:
            async with async_playwright() as pw:
                ctx = await pw.chromium.launch_persistent_context(
                    profile_dir,
                    headless=False,
                    accept_downloads=True,
                    permissions=["geolocation"],
                    geolocation={"latitude": -34.6037, "longitude": -58.3816},
                )
                page = await ctx.new_page()
                await self._bbva_login(page, nro_doc, usuario, clave)
                await self._bbva_navegar_movimientos(page)
                nombre = f"{prefijo}{date.today().strftime('%Y%m%d')}.xls"
                ruta = os.path.join(destino, nombre)
                async with page.expect_download(timeout=_TIMEOUT) as dl_info:
                    await page.get_by_role("button", name="Descargar").first.click()
                download = await dl_info.value
                await download.save_as(ruta)
                await ctx.close()
                _logger.warning(f"download_bbva: guardado en {ruta}")
                return ruta
        except AsyncTimeout as e:
            _logger.error(f"download_bbva timeout: {e}")
        except Exception as e:
            _logger.error(f"download_bbva: {e}")
        return None

    # ── Métodos públicos ──────────────────────────────────────────────────

    def download_bbva(self, desde: date, destino: str, prefijo: str) -> str | None:
        """Descarga el Excel de movimientos FCI desde BBVA Argentina."""
        creds = FinanceScreen().get_bank_credentials("BBVA")
        if not creds:
            _logger.error("download_bbva: credenciales BBVA no configuradas en fin_banks")
            return None

        clave = creds["login_pass"]
        raw = creds["login_user"] or ""
        nro_doc, usuario = raw.split("|", 1) if "|" in raw else ("", raw)

        profile_dir = os.path.join(os.environ.get("APPOO_TMP", "tmp"), "bbva_profile")
        os.makedirs(profile_dir, exist_ok=True)

        return asyncio.run(self._bbva_async(profile_dir, nro_doc, usuario, clave, destino, prefijo))

    def download_santander(self, desde: date, destino: str, prefijo: str) -> str | None:
        from Modulos_python import sync_playwright, PlaywrightTimeout

        creds = FinanceScreen().get_bank_credentials("Santander")
        if not creds:
            _logger.error("download_santander: credenciales Santander no configuradas en fin_banks")
            return None

        usuario = creds["login_user"]
        clave = creds["login_pass"]
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

                _logger.warning(f"download_santander: guardado en {ruta}")
                return ruta

        except PlaywrightTimeout as e:
            _logger.error(f"download_santander timeout: {e}")
        except Exception as e:
            _logger.error(f"download_santander: {e}")
        return None
