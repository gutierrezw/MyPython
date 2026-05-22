import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from Modulos_Mysql import BDsystem
from ConvergIA.Scanner_Sentimiento import scan_sentimiento
from ConvergIA.Interprete_Sentimiento import interpretar_sentimiento
from ConvergIA.ThemeMapper import load_sentiment, load_analysis, voto_tech_alignment

ACCOUNT = "U4214563"

if __name__ == "__main__":
    sesion = BDsystem.get_sesion_by_vehiculo("ClaudeAPI")
    api_key = sesion["userapi"].decode("utf-8") if sesion else ""
    if not api_key:
        print("ADVERTENCIA: ClaudeAPI no configurada en tabla sesion")

    print("=== Scanner ===")
    result = scan_sentimiento(account=ACCOUNT, api_key=api_key)
    print(f"Símbolos en cartera : {result['symbols']}")
    print(f"Con noticias        : {result['with_news']}")
    print(f"Clasificados        : {result['classified']}")

    print("\n=== Interprete ===")
    analisis = interpretar_sentimiento(account=ACCOUNT, api_key=api_key)
    for sym, patron in analisis.items():
        print(f"  {sym:<8} {patron}")

    print("\n=== Votos resultantes ===")
    sentiment = load_sentiment(ACCOUNT)
    analysis = load_analysis(ACCOUNT)
    for sym in sorted(sentiment):
        voto = voto_tech_alignment(sym, sentiment, analysis)
        info = analysis.get(sym, {})
        print(f"  {sym:<8} sentimiento={sentiment[sym]:+d}  patron={info.get('patron','—'):<12}  voto={voto:+d}")
