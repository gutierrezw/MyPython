import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "AppOO"))

from Modulos_Mysql import BDsystem

_appoo = os.path.join(os.path.dirname(__file__), "..", "AppOO")
_profile_path = os.environ.get(
    "APPOO_PROFILE",
    os.path.join(_appoo, "profiles", "main.json"),
)
with open(_profile_path, encoding="utf-8") as _f:
    _cfg = json.load(_f)
BDsystem.configure(_cfg.get("db", {}))
_tmp = _cfg.get("tmp_path", os.path.join(_appoo, "tmp"))
if not os.path.isabs(_tmp):
    _tmp = os.path.normpath(os.path.join(_appoo, _tmp))
os.environ.setdefault("APPOO_TMP", _tmp)

from datetime import date, timedelta
from Class_BrowserFCI import BrowserFCI

destino = os.environ.get("APPOO_TMP", os.path.join(os.path.dirname(__file__), "..", "deploy", "tmp"))
desde = date.today() - timedelta(days=90)

print(f"Perfil  : {_profile_path}")
print(f"Destino : {destino}")
print(f"Desde   : {desde}")
print("Iniciando Santander download...")

browser = BrowserFCI()
ruta = browser.download_santander(desde=desde, destino=destino, prefijo="movimientos-de-superfondos-")

if ruta:
    print(f"OK — archivo guardado: {ruta}")
else:
    print("ERROR — no se descargó el archivo")
