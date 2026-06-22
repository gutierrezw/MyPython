#!/usr/bin/env python3
"""
Análisis de performance acumulado — 5 superfondos + 2 fondos comparación
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from Modulos_Mysql import BDsystem

# Configurar BD
BDsystem.configure({"user": "root", "password": "Password123", "host": "localhost", "database": "bdinv"})

# Usar SQLAlchemy engine
from sqlalchemy import create_engine

engine = create_engine("mysql+pymysql://root:Daga2004@localhost/bdinv")

# Fondos a analizar
FONDOS = {
    689: "Superfondo Acciones Brasil - Clase A",
    1346: "Superfondo Renta Fija Dólares - Clase A",
    1325: "Superfondo Estrategico - Clase A",
    1565: "Superfondo Renta Fija Dólares II - Clase A",
    5334: "Superfondo Ahorro en Dólares - Clase A",
    730: "Supergestión MIX VI (SANT0001)",
    350: "FBA HORIZONTE (BBVA0001)",
}

# Extraer datos
query = """
    SELECT
        codCAFCI,
        fondo,
        fecha,
        valorActual,
        moneda
    FROM diaria_cnv
    WHERE codCAFCI IN (689, 1346, 1325, 1565, 5334, 730, 350)
    ORDER BY codCAFCI, fecha
"""

try:
    df = pd.read_sql(query, engine)
    print(f"\n✓ Datos extraídos: {len(df)} registros\n")
except Exception as e:
    print(f"✗ Error: {e}")
    sys.exit(1)

# Resumen por fondo
print("=" * 80)
print("RESUMEN — Registros por Fondo")
print("=" * 80)

for cod, nombre in FONDOS.items():
    subset = df[df["codCAFCI"] == cod]
    if len(subset) == 0:
        print(f"  {cod:5} | {nombre:45} | SIN DATOS")
        continue

    print(f"  {cod:5} | {nombre:45} | {len(subset):3d} registros")
    print(f"          Período: {subset['fecha'].min()} a {subset['fecha'].max()}")
    print(f"          Valor: ${subset['valorActual'].min():.4f} → ${subset['valorActual'].max():.4f}")
    print()

# Calcular performance acumulado
print("=" * 80)
print("PERFORMANCE ACUMULADO (USD)")
print("=" * 80)

resultados = []

for cod, nombre in FONDOS.items():
    subset = df[df["codCAFCI"] == cod].sort_values("fecha")

    if len(subset) < 2:
        print(f"  {cod:5} | {nombre:40} | SIN SUFICIENTES DATOS")
        continue

    valor_inicial = subset["valorActual"].iloc[0]
    valor_final = subset["valorActual"].iloc[-1]
    pct_cambio = ((valor_final - valor_inicial) / valor_inicial) * 100

    print(f"  {cod:5} | {nombre:40}")
    print(f"          Inicial:  ${valor_inicial:10.4f}  ({subset['fecha'].iloc[0]})")
    print(f"          Final:    ${valor_final:10.4f}  ({subset['fecha'].iloc[-1]})")
    print(f"          Cambio:   {pct_cambio:+7.2f}%")
    print()

    resultados.append(
        {
            "codCAFCI": cod,
            "Fondo": nombre.replace("Superfondo ", ""),
            "Fecha_Inicio": subset["fecha"].iloc[0],
            "Fecha_Fin": subset["fecha"].iloc[-1],
            "Valor_Inicial": valor_inicial,
            "Valor_Final": valor_final,
            "Cambio_%": pct_cambio,
            "Registros": len(subset),
        }
    )

# Tabla comparativa
print("=" * 80)
print("TABLA COMPARATIVA")
print("=" * 80)

df_resultados = pd.DataFrame(resultados)
df_resultados = df_resultados.sort_values("Cambio_%", ascending=False)

print("\n" + df_resultados.to_string(index=False))

# Análisis de comparación
print("\n" + "=" * 80)
print("COMPARACIÓN: 5 Superfondos vs 2 Fondos Base")
print("=" * 80)

superfondos = df_resultados[df_resultados["codCAFCI"].isin([689, 1346, 1325, 1565, 5334])]
fondos_base = df_resultados[df_resultados["codCAFCI"].isin([730, 350])]

print(f"\n5 Superfondos (USD):")
print(f"  Promedio performance: {superfondos['Cambio_%'].mean():+.2f}%")
print(f"  Mín/Máx: {superfondos['Cambio_%'].min():+.2f}% / {superfondos['Cambio_%'].max():+.2f}%")

print(f"\n2 Fondos Base (comparación):")
print(f"  Promedio performance: {fondos_base['Cambio_%'].mean():+.2f}%")
print(f"  Mín/Máx: {fondos_base['Cambio_%'].min():+.2f}% / {fondos_base['Cambio_%'].max():+.2f}%")

diferencia = superfondos["Cambio_%"].mean() - fondos_base["Cambio_%"].mean()
print(f"\n➜ Diferencia (Superfondos vs Base): {diferencia:+.2f}pp")

engine.dispose()
print("\n✓ Análisis completado\n")
