"""
Debug: login Santander → navega a FCI → intenta descargar movimientos.
"""

import asyncio
import json
import os
import sys
from datetime import datetime

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

from Modulos_Mysql import FinanceScreen
from Class_BrowserFCI import BrowserFCI, _TIMEOUT


def ts():
    return datetime.now().strftime("%H:%M:%S")


async def _debug():
    creds = FinanceScreen().get_bank_credentials("Santander")
    usuario = creds["login_user"]
    clave = creds["login_pass"]

    profile_dir = os.path.join(os.environ.get("APPOO_TMP", "tmp"), "santander_profile")
    os.makedirs(profile_dir, exist_ok=True)

    from playwright.async_api import async_playwright

    async with async_playwright() as pw:
        ctx = await pw.chromium.launch_persistent_context(
            profile_dir,
            headless=False,
            accept_downloads=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = await ctx.new_page()
        browser = BrowserFCI()

        print(f"[{ts()}] Login...")
        await browser._sant_login(page, usuario, clave)
        print(f"[{ts()}] Login OK — URL: {page.url}")

        # Capturar estado del dashboard
        await page.wait_for_timeout(3_000)
        print(f"[{ts()}] URL dashboard: {page.url}")

        botones = await page.get_by_role("button").all_text_contents()
        print(f"[{ts()}] Botones visibles:")
        for b in botones:
            t = b.strip()
            if t:
                print(f"  {t!r}")

        links = await page.get_by_role("link").all_text_contents()
        print(f"[{ts()}] Links visibles:")
        for lnk in links:
            t = lnk.strip()
            if t:
                print(f"  {t!r}")

        # Intentar navegar a Superfondos
        print(f"[{ts()}] Navegando a Superfondos...")
        try:
            await browser._sant_navegar_descarga(page)
            print(f"[{ts()}] URL Superfondos: {page.url}")

            botones2 = await page.get_by_role("button").all_text_contents()
            print(f"[{ts()}] Botones en Superfondos:")
            for b in botones2:
                t = b.strip()
                if t:
                    print(f"  {t!r}")

            # Intentar descarga
            print(f"[{ts()}] Intentando descargar...")
            ruta = os.path.join(
                os.environ.get("APPOO_TMP", "tmp"), f"santander_fci_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            )
            async with page.expect_download(timeout=_TIMEOUT) as dl_info:
                await page.locator('[data-testid="downloadLink"]').click()
            download = await dl_info.value
            nombre = download.suggested_filename or f"santander_fci_{datetime.now().strftime('%Y%m%d')}.xlsx"
            ruta = os.path.join(os.environ.get("APPOO_TMP", "tmp"), nombre)
            await download.save_as(ruta)
            print(f"[{ts()}] Descarga OK: {ruta}")
        except Exception as e:
            print(f"[{ts()}] Error en navegación/descarga: {e}")
            print(f"[{ts()}] URL actual: {page.url}")
            botones3 = await page.get_by_role("button").all_text_contents()
            print(f"[{ts()}] Botones en pantalla actual:")
            for b in botones3:
                t = b.strip()
                if t:
                    print(f"  {t!r}")

        await ctx.close()


asyncio.run(_debug())
