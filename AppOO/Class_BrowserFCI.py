import asyncio
import os
import logging

from datetime import date, datetime

from Modulos_Mysql import FinanceScreen
from Modulos_Utilitarios import read_json_tmp, write_json_tmp

_logger = logging.getLogger("BrowserFCI")

_TIMEOUT = 30_000
_MODAL_WAIT = 5_000
_BLOCKED_FILE = "browser_fci_blocked.json"


class BrowserFCI:

    def _check_blocked(self) -> bool:
        data = read_json_tmp(_BLOCKED_FILE)
        if data.get("blocked"):
            _logger.error(
                f"BrowserFCI bloqueado desde {data.get('timestamp')} — razón: {data.get('reason')}. "
                "Ejecutá BrowserFCI().reset_blocked() para liberar."
            )
            return True
        return False

    def _set_blocked(self, reason: str):
        write_json_tmp(
            _BLOCKED_FILE,
            {
                "blocked": True,
                "reason": reason,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            },
        )
        _logger.error(f"BrowserFCI — BLOQUEADO: {reason}")

    def reset_blocked(self):
        write_json_tmp(_BLOCKED_FILE, {"blocked": False})
        _logger.warning("BrowserFCI — bloqueo liberado manualmente")

    # ── BBVA Argentina ────────────────────────────────────────────────────
    _BBVA_URL_LOGIN = "https://online.bbva.com.ar/fnetcore/login/index.html"
    _BBVA_BTN_LOGIN = "Ingresar"

    # ── Santander Argentina ───────────────────────────────────────────────
    _SANT_URL_LOGIN = "https://www2.personas.santander.com.ar/obp-webapp/angular/#!/login"
    _SANT_SEL_USER = "#datosusuario"
    _SANT_SEL_PASS = "#clave"
    _SANT_BTN_LOGIN = "Ingresar"
    # Navegación FCI → pendiente inspección post-login
    _SANT_SEL_DL = "#SELECTOR_TODO"

    # ── Helpers async BBVA ────────────────────────────────────────────────

    async def _wait_nav(self, page):
        await page.wait_for_load_state("domcontentloaded", timeout=_TIMEOUT)
        await page.wait_for_timeout(1_500)

    async def _bbva_login(self, page, nro_doc: str, usuario: str, clave: str):
        """Login BBVA usando perfil persistente Chrome — autofill llena las credenciales."""
        await page.goto(self._BBVA_URL_LOGIN, wait_until="domcontentloaded", timeout=_TIMEOUT)

        # Esperar que el form cargue y Chrome autofill complete los campos
        campo_pass = page.locator("input[name='password']")
        await campo_pass.wait_for(state="visible", timeout=_TIMEOUT)
        await page.wait_for_timeout(3_000)

        # Hacer click en el botón — autofill nativo ya disparó los eventos correctos
        btn_login = page.get_by_role("button", name=self._BBVA_BTN_LOGIN)
        try:
            await btn_login.wait_for(state="enabled", timeout=10_000)
        except Exception:
            pass  # si no se habilitó solo, forzar click igual
        await btn_login.click(force=True)
        await self._wait_nav(page)

        try:
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
            self._set_blocked(f"BBVA timeout: {e}")
        except Exception as e:
            self._set_blocked(f"BBVA: {e}")
        return None

    # ── Métodos públicos ──────────────────────────────────────────────────

    def download_bbva(self, desde: date, destino: str, prefijo: str) -> str | None:
        """Descarga el Excel de movimientos FCI desde BBVA Argentina."""
        if self._check_blocked():
            return None
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

    async def _sant_login(self, page, usuario: str, clave: str):
        """Login Santander usando perfil persistente Chrome — autofill llena las credenciales."""
        await page.goto(self._SANT_URL_LOGIN, wait_until="domcontentloaded", timeout=_TIMEOUT)

        # Esperar que el form cargue y Chrome autofill complete los campos
        await page.locator(self._SANT_SEL_PASS).wait_for(state="visible", timeout=_TIMEOUT)
        await page.wait_for_timeout(3_000)

        await page.locator("button.button-login").click()
        await self._wait_nav(page)

    async def _sant_navegar_descarga(self, page):
        """Dashboard → Superfondos → tab Operaciones → espera botón Descargar."""
        await page.locator("#plazos-fijos").wait_for(state="visible", timeout=_TIMEOUT)
        await page.locator("#plazos-fijos").click()
        await self._wait_nav(page)

        await page.locator("#tab-3").wait_for(state="visible", timeout=_TIMEOUT)
        await page.locator("#tab-3").click()
        await self._wait_nav(page)

        await page.locator('[data-testid="downloadLink"]').wait_for(state="visible", timeout=_TIMEOUT)

    async def _sant_async(
        self, profile_dir: str, usuario: str, clave: str, desde: date, destino: str, prefijo: str
    ) -> str | None:
        from playwright.async_api import async_playwright, TimeoutError as AsyncTimeout

        try:
            async with async_playwright() as pw:
                ctx = await pw.chromium.launch_persistent_context(
                    profile_dir,
                    headless=False,
                    accept_downloads=True,
                )
                page = await ctx.new_page()
                await self._sant_login(page, usuario, clave)
                await self._sant_navegar_descarga(page)
                nombre = f"{prefijo}{date.today().strftime('%Y%m%d')}.xlsx"
                ruta = os.path.join(destino, nombre)
                async with page.expect_download(timeout=_TIMEOUT) as dl_info:
                    await page.locator('[data-testid="downloadLink"]').click()
                download = await dl_info.value
                # Conservar nombre original de Santander (movimientos-de-superfondos-*.xlsx)
                nombre = download.suggested_filename or f"{prefijo}{date.today().strftime('%Y-%m-%d')}.xlsx"
                ruta = os.path.join(destino, nombre)
                await download.save_as(ruta)
                await ctx.close()
                _logger.warning(f"download_santander: guardado en {ruta}")
                return ruta
        except AsyncTimeout as e:
            self._set_blocked(f"Santander timeout: {e}")
        except Exception as e:
            self._set_blocked(f"Santander: {e}")
        return None

    def download_santander(self, desde: date, destino: str, prefijo: str) -> str | None:
        """Descarga el Excel de movimientos FCI desde Santander Argentina."""
        if self._check_blocked():
            return None
        creds = FinanceScreen().get_bank_credentials("Santander")
        if not creds:
            _logger.error("download_santander: credenciales Santander no configuradas en fin_banks")
            return None

        usuario = creds["login_user"]
        clave = creds["login_pass"]

        profile_dir = os.path.join(os.environ.get("APPOO_TMP", "tmp"), "santander_profile")
        os.makedirs(profile_dir, exist_ok=True)

        return asyncio.run(self._sant_async(profile_dir, usuario, clave, desde, destino, prefijo))
