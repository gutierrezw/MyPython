import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from ConvergIA.Scanner_Sentimiento import scan_sentimiento
from ConvergIA.Interprete_Sentimiento import interpretar_sentimiento
from ConvergIA.ThemeMapper import load_sentiment, load_analysis

ACCOUNT = "U4214563"

if __name__ == "__main__":
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("ADVERTENCIA: ANTHROPIC_API_KEY no definida")

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
    from ConvergIA.ThemeMapper import voto_tech_alignment

    for sym in sorted(sentiment):
        voto = voto_tech_alignment(sym, sentiment, analysis)
        info = analysis.get(sym, {})
        print(f"  {sym:<8} sentimiento={sentiment[sym]:+d}  patron={info.get('patron','—'):<12}  voto={voto:+d}")
