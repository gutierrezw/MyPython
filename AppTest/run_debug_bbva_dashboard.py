"""
Debug: login BBVA → click inversiones → intenta descargar archivo FCI.
"""

import asyncio
import json
import os
import re
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
    creds = FinanceScreen().get_bank_credentials("BBVA")
    clave = creds["login_pass"]
    raw = creds["login_user"] or ""
    nro_doc, usuario = raw.split("|", 1) if "|" in raw else ("", raw)

    profile_dir = os.path.join(os.environ.get("APPOO_TMP", "tmp"), "bbva_profile")
    os.makedirs(profile_dir, exist_ok=True)

    from playwright.async_api import async_playwright

    async with async_playwright() as pw:
        ctx = await pw.chromium.launch_persistent_context(
            profile_dir,
            headless=False,
            accept_downloads=True,
            permissions=["geolocation"],
            geolocation={"latitude": -34.6037, "longitude": -58.3816},
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = await ctx.new_page()
        browser = BrowserFCI()

        print(f"[{ts()}] Login...")
        await browser._bbva_login(page, nro_doc, usuario, clave)
        print(f"[{ts()}] Login OK — URL: {page.url}")

        # Click en la card de inversiones
        print(f"[{ts()}] Buscando card 'Total de inversiones en pesos'...")
        card = page.get_by_role("button", name="Estás en la inversión 1 de 1")
        await card.wait_for(state="visible", timeout=_TIMEOUT)
        await card.click()
        await page.wait_for_load_state("domcontentloaded", timeout=_TIMEOUT)
        await page.wait_for_timeout(3_000)
        print(f"[{ts()}] Pantalla inversiones — URL: {page.url}")

        # Listar botones para identificar selector de descarga
        botones = await page.get_by_role("button").all_text_contents()
        print(f"[{ts()}] Botones visibles:")
        for b in botones:
            t = b.strip()
            if t:
                print(f"  {t!r}")

        # Click en "Mostrar movimientos" (primer botón)
        print(f"[{ts()}] Click en 'Mostrar movimientos'...")
        btn_mov = page.get_by_role("button", name="Mostrar movimientos")
        await btn_mov.nth(1).click()
        await page.wait_for_function("() => window.location.hash.includes('movements')", timeout=_TIMEOUT)
        await page.wait_for_timeout(2_000)
        print(f"[{ts()}] URL: {page.url}")

        # Intentar descarga
        print(f"[{ts()}] Intentando click en 'Descargar'...")
        btn_dl = page.locator("button", has_text=re.compile(r"^[\s]*Descargar$")).first
        try:
            await btn_dl.wait_for(state="visible", timeout=_TIMEOUT)
            ruta = os.path.join(
                os.environ.get("APPOO_TMP", "tmp"), f"bbva_fci_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xls"
            )
            async with page.expect_download(timeout=_TIMEOUT) as dl_info:
                await btn_dl.click()
            download = await dl_info.value
            await download.save_as(ruta)
            print(f"[{ts()}] Descarga OK: {ruta}")
        except Exception as e:
            print(f"[{ts()}] Descarga fallida: {e}")

        await ctx.close()


asyncio.run(_debug())
