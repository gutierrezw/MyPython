#!/usr/bin/env python3
"""
Gráfico comparativo — banda fondos base (MIX VI + FBA HORIZONTE) vs 5 superfondos
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from sqlalchemy import create_engine

# BD
engine = create_engine("mysql+pymysql://root:Daga2004@localhost/bdinv")

# Extraer datos
query = """
    SELECT
        codCAFCI,
        fondo,
        fecha,
        valorActual
    FROM diaria_cnv
    WHERE codCAFCI IN (689, 1346, 1325, 1565, 5334, 730, 350)
    ORDER BY codCAFCI, fecha
"""

df = pd.read_sql(query, engine)
print(f"✓ Datos extraídos: {len(df)} registros\n")

# Fondos
FONDOS = {
    689: ("Acciones Brasil", "C0", "-", 2),
    1346: ("Renta Fija $", "C1", "-", 2),
    1325: ("Estrategico", "C2", "-", 2),
    1565: ("Renta Fija Dólares II", "C3", "-", 2),
    5334: ("Ahorro en Dólares", "C4", "-", 2),
    730: ("MIX VI (SANT)", "darkgreen", "--", 2.5),
    350: ("FBA HORIZONTE (BBVA)", "darkred", "--", 2.5),
}

# Normalizar valores (100 = valor inicial de cada fondo)
df_norm = df.copy()
for cod in df["codCAFCI"].unique():
    mask = df_norm["codCAFCI"] == cod
    valor_inicial = df_norm.loc[mask, "valorActual"].iloc[0]
    df_norm.loc[mask, "valorActual"] = (df_norm.loc[mask, "valorActual"] / valor_inicial) * 100

# Crear figura
fig, ax = plt.subplots(figsize=(16, 9))

# Normalizar a 6 meses (desde 2025-12-21)
fecha_inicio = pd.to_datetime("2025-12-21").date()
df_norm["fecha"] = pd.to_datetime(df_norm["fecha"])
df_norm = df_norm[df_norm["fecha"].dt.date >= fecha_inicio].copy()

# Renormalizar valores a partir de la nueva fecha de inicio
for cod in df_norm["codCAFCI"].unique():
    mask = df_norm["codCAFCI"] == cod
    valor_inicial = df_norm.loc[mask, "valorActual"].iloc[0]
    df_norm.loc[mask, "valorActual"] = (df_norm.loc[mask, "valorActual"] / valor_inicial) * 100

# Datos por fondo
datos_por_fondo = {}
for cod in df_norm["codCAFCI"].unique():
    subset = df_norm[df_norm["codCAFCI"] == cod].sort_values("fecha")
    datos_por_fondo[cod] = subset

# Dibujar banda (MIX VI y FBA HORIZONTE)
df_mix = datos_por_fondo[730].sort_values("fecha")
df_fba = datos_por_fondo[350].sort_values("fecha")

# Alinear fechas para la banda
todas_fechas = pd.concat([df_mix["fecha"], df_fba["fecha"]]).unique()
todas_fechas = sorted(todas_fechas)

# Interpolar para tener valores en todas las fechas
df_mix_interp = df_mix.set_index("fecha")[["valorActual"]].reindex(todas_fechas, method="ffill").reset_index()
df_fba_interp = df_fba.set_index("fecha")[["valorActual"]].reindex(todas_fechas, method="ffill").reset_index()
df_mix_interp.columns = ["fecha", "valorActual"]
df_fba_interp.columns = ["fecha", "valorActual"]

# Banda sombreada
ax.fill_between(
    df_mix_interp["fecha"],
    df_mix_interp["valorActual"],
    df_fba_interp["valorActual"],
    alpha=0.2,
    color="gray",
    label="Banda: MIX VI - FBA HORIZONTE",
)

# Líneas de fondos base (bordes de banda)
ax.plot(
    df_mix["fecha"],
    df_mix["valorActual"],
    color="darkgreen",
    linewidth=2.5,
    linestyle="--",
    label="MIX VI (límite inferior)",
)
ax.plot(
    df_fba["fecha"],
    df_fba["valorActual"],
    color="darkred",
    linewidth=2.5,
    linestyle="--",
    label="FBA HORIZONTE (límite superior)",
)

# Líneas de superfondos
for cod in [689, 1346, 1325, 1565, 5334]:
    subset = datos_por_fondo[cod].sort_values("fecha")
    nombre, color, estilo, ancho = FONDOS[cod]
    ax.plot(
        subset["fecha"], subset["valorActual"], label=nombre, color=color, linewidth=ancho, linestyle=estilo, alpha=0.8
    )

# Estilo
ax.set_xlabel("Fecha", fontsize=12, fontweight="bold")
ax.set_ylabel("Valor Normalizado (Base 100)", fontsize=12, fontweight="bold")
ax.set_title(
    "Comparación de Performance (últimos 6 meses) — 5 Superfondos vs Banda MIX VI / FBA HORIZONTE",
    fontsize=14,
    fontweight="bold",
    pad=20,
)
ax.legend(loc="upper left", fontsize=10, framealpha=0.95)
ax.grid(True, alpha=0.3, linestyle=":")
ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
plt.xticks(rotation=45, ha="right")

# Annotations
ax.axhline(y=100, color="black", linewidth=0.8, linestyle=":", alpha=0.5)
ax.text(df["fecha"].min(), 101, "Base (100)", fontsize=9, alpha=0.7)

# Layout
plt.tight_layout()
plt.savefig(
    "C:/Users/InversionesWildaga/Documents/MyPython/AppOO/AppTest/grafico_comparativo.png", dpi=300, bbox_inches="tight"
)
print(f"✓ Gráfico guardado: AppTest/grafico_comparativo.png")

plt.show()
engine.dispose()
