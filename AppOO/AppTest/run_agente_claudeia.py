import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import Modulos_python  # noqa: F401
from Modulos_Mysql import BDsystem

_profile = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "profiles", "main.json")
with open(_profile, encoding="utf-8") as _f:
    _cfg = json.load(_f)
BDsystem.configure(_cfg.get("db", {}))

from Class_DashBot import ClassAgenteIA
from Class_customer import DataHub

DataHub.modo_operacion = "SUPERVISADO"

agente = ClassAgenteIA()
agente.Agente_ClaudeIA.__wrapped__(agente)
