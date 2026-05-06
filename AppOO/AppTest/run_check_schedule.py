"""
run_check_schedule.py
Monitorea el estado de ejecución de los agentes autónomos.
Muestra último run, próximo run y alerta si alguno está vencido (>1.5x intervalo).

Uso: python AppTest/run_check_schedule.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from Modulos_Utilitarios import read_json_tmp, AGENTES_SCHEDULE
from datetime import datetime
import time

ALERTA_FACTOR = 1.5  # vencido si lleva > 1.5x el intervalo sin correr


def _fmt_intervalo(seg):
    if seg >= 86400:
        return f"{seg // 86400}d"
    if seg >= 3600:
        return f"{seg // 3600}h"
    return f"{seg // 60}m"


def main():
    sched = read_json_tmp("agents_schedule.json")
    ahora = time.time()

    ok, pendiente, vencido = [], [], []

    print(f"\n{'Agente':<28} {'Intervalo':<10} {'Último run':<22} {'Próximo run':<22} {'Estado'}")
    print("─" * 100)

    for nombre, cfg in AGENTES_SCHEDULE.items():
        intervalo = cfg["intervalo"]
        ts = sched.get(nombre, 0)

        if not ts:
            estado = "⚠  NUNCA"
            ultimo_str = "nunca"
            proximo_str = "al arrancar"
            pendiente.append(nombre)
        else:
            ultimo = datetime.fromtimestamp(ts)
            proximo = datetime.fromtimestamp(ts + intervalo)
            ultimo_str = ultimo.strftime("%Y-%m-%d %H:%M")
            proximo_str = proximo.strftime("%Y-%m-%d %H:%M")
            transcurrido = ahora - ts

            if transcurrido >= intervalo * ALERTA_FACTOR:
                estado = "🔴 VENCIDO"
                vencido.append(nombre)
            elif transcurrido >= intervalo:
                estado = "🟡 PENDIENTE"
                pendiente.append(nombre)
            else:
                estado = "🟢 OK"
                ok.append(nombre)

        print(f"{nombre:<28} {_fmt_intervalo(intervalo):<10} {ultimo_str:<22} {proximo_str:<22} {estado}")

    print("─" * 100)
    print(f"\nResumen: 🟢 OK={len(ok)}  🟡 Pendiente={len(pendiente)}  🔴 Vencido={len(vencido)}\n")

    if vencido:
        print("⚠  Agentes VENCIDOS (llevan >1.5x su intervalo sin correr):")
        for a in vencido:
            print(f"   - {a}  ({AGENTES_SCHEDULE[a]['desc']})")
        print()


if __name__ == "__main__":
    main()
