# Sistema de Rebalanceo de Cartera - DataHub.manager_buysell

**Fecha:** 2025-12-29
**Autor:** Claude Code
**Propósito:** Especificación del sistema de recomendaciones de compra para balancear cartera

---

## 📋 Tabla de Contenidos

1. [Objetivo del Sistema](#objetivo-del-sistema)
2. [Estado Actual](#estado-actual)
3. [Arquitectura Propuesta](#arquitectura-propuesta)
4. [Algoritmo de Rebalanceo](#algoritmo-de-rebalanceo)
5. [Visualización con ProgressBar](#visualización-con-progressbar)
6. [Plan de Implementación](#plan-de-implementación)
7. [Ejemplos de Uso](#ejemplos-de-uso)

---

## 🎯 Objetivo del Sistema

### Función Principal

**`DataHub.manager_buysell`** es un **módulo de rebalanceo de cartera** que debe identificar qué activos **COMPRAR** para balancear el portafolio en 4 dimensiones usando una **estrategia EQUIPONDERADA** (equal weighting):

#### 1. Dividendos - Equilibrio Mensual
Recibir **la misma cantidad de dividendos todos los meses**
- **Objetivo**: Distribución uniforme del ingreso mensual (12 meses)
- **Ejemplo**: Si objetivo anual es $60,000 → $5,000 cada mes (no $10,000 en enero y $0 en febrero)
- **Gap actual**: Meses con dividendos bajos vs meses con dividendos altos
- **Meta**: Suavizar el flujo de caja mensual

#### 2. Diversificación por Sector - Mismo Peso
Cada sector debe tener **el mismo peso porcentual** en la cartera
- **Objetivo**: Distribución equitativa entre todos los sectores presentes
- **Ejemplo**: Si tienes 7 sectores → 14.29% cada uno (100% / 7)
- **Identificar**: Sectores sobreponderados (reducir) y subponderados (comprar)
- **Filosofía**: No apostar más a un sector que a otro

#### 3. Diversificación por Tipo de Activo - Distribución Equitativa
Distribución equilibrada entre tipos de activos (relacionado con **cartera permanente**)
- **Objetivo**: Balance entre clases de activos según riesgo
- **Concepto**: Permanent Portfolio adaptado (Stock, Crypto, FCI, Bonds, etc.)
- **Identificar**: Tipos con baja exposición que necesitan rebalanceo
- **Nota**: Este es el criterio "más difícil" según requerimientos

#### 4. Diversificación Geográfica - Equilibrio por País
Equilibrar **lo que tengo en cada país** con mismo peso
- **Objetivo**: Mismo porcentaje en cada región/país presente
- **Ejemplo**: Si tienes 4 países → 25% cada uno
- **Identificar**: Concentración geográfica excesiva
- **Meta**: Reducir riesgo país distribuyendo igualmente

### Filosofía del Sistema

> **"La idea es tener el riesgo distribuido en partes iguales"**

Esta estrategia busca:
- ✅ Minimizar concentración de riesgo en cualquier dimensión
- ✅ Distribución uniforme sin apuestas direccionales
- ✅ Flujo de dividendos estable y predecible
- ✅ Balance natural entre activos, sectores y geografías

### Fuera del Alcance (por ahora)

- ❌ **Valoración de acciones** (análisis fundamental - sistema separado pendiente)
- ⚠️ **Enfoque principal en COMPRAS** para rebalanceo
- ℹ️ **Decisiones de venta**: Permitidas pero secundarias (no es el foco del sistema)

---

## 📊 Estado Actual

### Datos que YA se Recopilan

```python
DataHub.manager_buysell = {
    "dividends": {
        "datos": DataFrame,      # DataFrame con columnas: ['dividendos', 'cobrados']
        "struct": {
            "dividendos": [float × 12],  # Proyección mensual (12 meses)
            "cobrados": [float × 12]     # Cobros reales (12 meses)
        },
        "media": float                    # Promedio mensual
    },
    "sector": {
        "data": DataFrame,        # Posiciones detalladas por símbolo y sector
        "summary": {              # Peso actual de cada sector
            "Technology": 35.2,
            "Financial": 28.7,
            "Healthcare": 12.0,
            ...
        },
        "media": float           # Peso promedio por sector
    },
    "activos": {
        "data": DataFrame,
        "summary": {             # Distribución actual por tipo
            "Stock": 60.0,
            "Crypto": 25.0,
            "FCI": 15.0
        },
        "media": float
    },
    "region": {
        "data": DataFrame,
        "summary": {             # Distribución geográfica actual
            "USA": 55.0,
            "Europe": 30.0,
            "Asia": 15.0
        },
        "media": float
    }
}
```

### Funciones Generadoras

**Ubicación**: `Class_DataFrame.py`

1. **`grupo_dividendo()`** (línea ~2089)
   - Calcula dividendos proyectados vs cobrados
   - Retorna: `{"datos": DataFrame, "struct": dict, "media": float}`

2. **`grupo_sector()`** (línea ~1900)
   - Obtiene sector desde FinViz API
   - Retorna: `{"data": DataFrame, "summary": dict, "media": float}`

3. **`grupo_activos()`**
   - Agrupa por tipo de activo
   - Retorna estructura similar

4. **`grupo_region()`**
   - Agrupa por región geográfica
   - Retorna estructura similar

### Actualización de Datos

**Ubicación**: `DashMainV9_ia.py:graficos_main()` (líneas 3473-3508)

```python
# Se actualiza cada 20 minutos (1,200,000 ms)
DataHub.manager_buysell["dividends"] = grupo_dividendo(fg=self.rg2, parm=parm)
DataHub.manager_buysell["sector"] = grupo_sector(fig=self.rg3, parm=parm)
DataHub.manager_buysell["activos"] = grupo_activos(fg=self.rg4, parm=parm, strategy=xestrategia)
DataHub.manager_buysell["region"] = grupo_region(fg=self.rg5, strategy=xestrategia, parm=parm)
```

---

## 🏗️ Arquitectura Propuesta

### 1. Configuración de Objetivos - Estrategia Equiponderada

**Archivo sugerido**: `config_balance.py`

**IMPORTANTE**: Los parámetros financieros se obtienen de las tablas `plan` y `variables_plan` existentes.

```python
# Objetivos de balance de cartera - ESTRATEGIA EQUIPONDERADA
OBJETIVOS_BALANCE = {
    "dividends": {
        "target_anual": None,            # Se obtiene de tabla `plan` o `variables_plan`
        "estrategia": "equiponderado",   # Distribuir igualmente entre 12 meses
        "target_mensual": None,          # Se calcula: target_anual / 12
        "desviacion_max": 0.15,          # Máximo 15% de desviación permitida por mes
        "min_dividend_yield": None,      # Se obtiene de tabla `variables_plan`
        "peso": 0.35                     # 35% de peso en el score
    },
    "sector": {
        "estrategia": "equiponderado",   # Todos los sectores con mismo peso
        "modo": "dinamico",              # Calcula peso según sectores presentes
        # Si tienes 7 sectores → 100/7 = 14.29% cada uno
        # Si tienes 10 sectores → 100/10 = 10% cada uno
        "sectores_actuales": None,       # Se detecta automáticamente desde manager_buysell
        "peso_objetivo_por_sector": None,  # Se calcula: 100 / num_sectores
        "peso": 0.30                     # 30% de peso en el score
    },
    "activos": {
        "estrategia": "equiponderado",   # Balance igual entre tipos
        "modo": "dinamico",              # Calcula según tipos presentes en portafolio
        # Tipos comunes: Stock, FCI, Bonds, Crypto, Digital Assets, Cash
        # Cartera Permanente Tradicional sería:
        #   - 25% Acciones (crecimiento)
        #   - 25% Bonos (deflación)
        #   - 25% Oro (inflación)
        #   - 25% Cash (liquidez)
        # Tu versión adaptada:
        #   - Equiponderado dinámico: 100 / num_tipos presentes
        #   - Ejemplo: 5 tipos → 20% cada uno
        "tipos_actuales": None,          # Se detecta desde manager_buysell
        "peso_objetivo_por_tipo": None,  # Se calcula: 100 / num_tipos

        # RESTRICCIÓN DE DIVIDENDOS (80% POR VALOR MONETARIO)
        "restriccion_dividendos": 0.80,  # 80% del portafolio DEBE generar ingresos
        # IMPORTANTE: Se calcula por VALOR MONETARIO, no por cantidad de posiciones
        # Ejemplo: Si portafolio vale $100,000 → mínimo $80,000 en activos que pagan dividendos
        # NO significa 80% de las posiciones, sino 80% del valor total

        "tipos_con_dividendos": ["Stock", "Bonds", "Cash"],  # Solo estos tipos generan dividendos/cupones/intereses
        # Crypto y Digital Assets NO pagan dividendos
        # FCI puede o no pagar (se valida caso por caso con dividend_yield)

        "peso": 0.20                     # 20% de peso en el score
    },
    "region": {
        "estrategia": "equiponderado",   # Mismo peso por país/región
        "modo": "dinamico",              # Calcula según regiones presentes
        # Si tienes 4 países → 25% cada uno
        # Si tienes 5 países → 20% cada uno
        "regiones_actuales": None,       # Se detecta desde manager_buysell
        "peso_objetivo_por_region": None,  # Se calcula: 100 / num_regiones
        "peso": 0.15                     # 15% de peso en el score
    }
}

# NOTA IMPORTANTE:
# Los pesos objetivo se calculan DINÁMICAMENTE según lo que existe en el portafolio:
# - No se definen valores fijos como "Technology: 25%"
# - Se calcula automáticamente: peso_target = 100 / cantidad_de_categorías
# - Ejemplo: 7 sectores presentes → cada uno debe tender a 14.29%
```

### 2. Motor de Rebalanceo

**Archivo sugerido**: `Class_Rebalanceo.py`

```python
from typing import List, Dict, Tuple
import pandas as pd
from Class_customer import DataHub
from config_balance import OBJETIVOS_BALANCE


class RebalanceoCartera:
    """
    Motor de recomendaciones de compra para rebalanceo de cartera
    """

    def __init__(self, universo_activos: pd.DataFrame = None):
        """
        Args:
            universo_activos: DataFrame con activos disponibles para comprar
                Columnas: ['symbol', 'sector', 'tipo', 'region', 'dividend_yield',
                          'price', 'nombre']
        """
        self.portafolio = DataHub.manager_buysell
        self.objetivos = OBJETIVOS_BALANCE
        self.universo = universo_activos or self._get_universo_default()

    def _get_universo_default(self) -> pd.DataFrame:
        """
        Obtiene universo de activos desde base de datos o fuente externa
        """
        # TODO: Implementar obtención de activos disponibles
        pass

    def calcular_gaps(self) -> Dict:
        """
        Identifica desbalances en las 4 dimensiones usando ESTRATEGIA EQUIPONDERADA

        Returns:
            gaps = {
                "dividends": {
                    "mensual": {
                        "Enero": {"actual": 8500, "objetivo": 5000, "gap": -3500},
                        "Febrero": {"actual": 2100, "objetivo": 5000, "gap": 2900},
                        ...
                    },
                    "desviacion_std": 2345.67,  # Desviación estándar mensual
                    "meses_bajo_objetivo": 8,    # Cuántos meses están por debajo
                    "equilibrio_score": 45.2     # 0-100 (100 = perfectamente equilibrado)
                },
                "sector": {
                    "num_sectores": 7,
                    "peso_objetivo": 14.29,      # 100 / 7 sectores
                    "sectores": {
                        "Technology": {"actual": 35.2, "objetivo": 14.29, "gap": -20.91},
                        "Healthcare": {"actual": 8.5, "objetivo": 14.29, "gap": 5.79},
                        ...
                    }
                },
                "activos": {
                    "num_tipos": 4,
                    "peso_objetivo": 25.0,       # 100 / 4 tipos (equiponderado puro)
                    "tipos": {
                        "Stock": {"actual": 60.0, "objetivo": 25.0, "gap": -35.0},
                        "Crypto": {"actual": 25.0, "objetivo": 25.0, "gap": 0.0},
                        ...
                    },
                    "pct_con_dividendos": 65.0,  # Actual 65%, objetivo 80%
                    "gap_dividendos": 15.0       # Faltan 15% para cumplir restricción
                },
                "region": {
                    "num_regiones": 4,
                    "peso_objetivo": 25.0,       # 100 / 4 regiones
                    "regiones": {
                        "USA": {"actual": 55.0, "objetivo": 25.0, "gap": -30.0},
                        "Europe": {"actual": 30.0, "objetivo": 25.0, "gap": -5.0},
                        ...
                    }
                }
            }
        """
        gaps = {}

        # 1. Gap de Dividendos - EQUILIBRIO MENSUAL
        div_data = self.portafolio["dividends"]["struct"]
        div_objetivo_mensual = self.objetivos["dividends"]["target_mensual"]

        meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                 "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

        gaps["dividends"] = {"mensual": {}}
        dividendos_proyectados = div_data.get("dividendos", [0]*12)

        desviaciones = []
        meses_bajo = 0

        for i, mes in enumerate(meses):
            actual = dividendos_proyectados[i] if i < len(dividendos_proyectados) else 0
            gap = div_objetivo_mensual - actual

            gaps["dividends"]["mensual"][mes] = {
                "actual": actual,
                "objetivo": div_objetivo_mensual,
                "gap": gap
            }

            desviaciones.append(abs(gap))
            if actual < div_objetivo_mensual:
                meses_bajo += 1

        # Calcular desviación estándar (qué tan desigual es la distribución)
        import statistics
        gaps["dividends"]["desviacion_std"] = statistics.stdev(dividendos_proyectados) if len(dividendos_proyectados) > 1 else 0
        gaps["dividends"]["meses_bajo_objetivo"] = meses_bajo

        # Score de equilibrio: 100 = perfectamente equilibrado (std=0)
        max_std = div_objetivo_mensual  # Máxima desviación posible
        gaps["dividends"]["equilibrio_score"] = max(0, 100 * (1 - gaps["dividends"]["desviacion_std"] / max_std))

        # 2. Gap de Sectores - EQUIPONDERADO DINÁMICO
        sector_actual = self.portafolio["sector"]["summary"]
        num_sectores = len(sector_actual)
        peso_objetivo_sector = 100.0 / num_sectores if num_sectores > 0 else 0

        gaps["sector"] = {
            "num_sectores": num_sectores,
            "peso_objetivo": peso_objetivo_sector,
            "sectores": {}
        }

        for sector, peso_actual in sector_actual.items():
            gaps["sector"]["sectores"][sector] = {
                "actual": peso_actual,
                "objetivo": peso_objetivo_sector,
                "gap": peso_objetivo_sector - peso_actual
            }

        # 3. Gap de Activos - EQUIPONDERADO + RESTRICCIÓN 80% DIVIDENDOS
        activos_actual = self.portafolio["activos"]["summary"]
        num_tipos = len(activos_actual)
        peso_objetivo_tipo = 100.0 / num_tipos if num_tipos > 0 else 0

        gaps["activos"] = {
            "num_tipos": num_tipos,
            "peso_objetivo": peso_objetivo_tipo,
            "tipos": {}
        }

        for tipo, peso_actual in activos_actual.items():
            gaps["activos"]["tipos"][tipo] = {
                "actual": peso_actual,
                "objetivo": peso_objetivo_tipo,
                "gap": peso_objetivo_tipo - peso_actual
            }

        # Calcular % actual que paga dividendos (POR VALOR MONETARIO)
        # TODO: implementar lógica real consultando booktrading
        # Ejemplo de cálculo:
        #   valor_total_portafolio = sum(posicion.market_value for posicion in booktrading)
        #   valor_con_dividendos = sum(posicion.market_value for posicion in booktrading
        #                               if posicion.tipo in ["Stock", "Bonds", "Cash"]
        #                               and posicion.dividend_yield > min_dividend_yield)
        #   pct_con_dividendos = (valor_con_dividendos / valor_total_portafolio) * 100

        gaps["activos"]["pct_con_dividendos"] = 0.0  # TODO: calcular desde booktrading
        gaps["activos"]["gap_dividendos"] = 80.0 - gaps["activos"]["pct_con_dividendos"]

        # 4. Gap de Región - EQUIPONDERADO DINÁMICO
        region_actual = self.portafolio["region"]["summary"]
        num_regiones = len(region_actual)
        peso_objetivo_region = 100.0 / num_regiones if num_regiones > 0 else 0

        gaps["region"] = {
            "num_regiones": num_regiones,
            "peso_objetivo": peso_objetivo_region,
            "regiones": {}
        }

        for region, peso_actual in region_actual.items():
            gaps["region"]["regiones"][region] = {
                "actual": peso_actual,
                "objetivo": peso_objetivo_region,
                "gap": peso_objetivo_region - peso_actual
            }

        return gaps

    def calcular_score_activo(self, activo: pd.Series, gaps: Dict) -> Tuple[float, Dict]:
        """
        Calcula score de un activo para rebalanceo usando ESTRATEGIA EQUIPONDERADA

        Args:
            activo: Series con datos del activo (symbol, sector, tipo, region, dividend_yield,
                    price, mes_pago_dividendo)
            gaps: Diccionario de gaps calculado por calcular_gaps()

        Returns:
            (score_total, desglose)

            score_total: Puntaje de 0-100
            desglose: {
                "dividends": float,
                "sector": float,
                "activos": float,
                "region": float,
                "razones": [str]
            }
        """
        score = 0
        desglose = {"dividends": 0, "sector": 0, "activos": 0, "region": 0, "razones": []}

        # 1. Score Dividendos - PRIORIZA MESES CON BAJO INGRESO
        dividend_yield = activo.get("dividend_yield", 0)
        mes_pago = activo.get("mes_pago_dividendo", [])  # Lista de meses que paga (ej: [0, 3, 6, 9])

        if dividend_yield > 0 and len(mes_pago) > 0:
            # Calcular cuánto ayuda este activo a balancear dividendos mensuales
            meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                     "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

            # Suma de gaps de los meses donde este activo paga dividendos
            gap_total_meses = 0
            meses_ayuda = []

            for mes_idx in mes_pago:
                if mes_idx < len(meses):
                    mes_nombre = meses[mes_idx]
                    if mes_nombre in gaps["dividends"]["mensual"]:
                        gap_mes = gaps["dividends"]["mensual"][mes_nombre]["gap"]
                        if gap_mes > 0:  # Solo meses con déficit
                            gap_total_meses += gap_mes
                            meses_ayuda.append(mes_nombre)

            if gap_total_meses > 0:
                # Score más alto si ayuda en meses con más déficit
                score_div = min(100, (gap_total_meses / len(mes_pago)) / 1000 * 100)
                score += score_div * self.objetivos["dividends"]["peso"]
                desglose["dividends"] = score_div
                desglose["razones"].append(
                    f"Ayuda equilibrar dividendos en {len(meses_ayuda)} meses: {', '.join(meses_ayuda[:3])}"
                )
            else:
                # Paga en meses que ya están sobre el objetivo
                desglose["dividends"] = 0
                desglose["razones"].append(f"⚠️ Paga en meses ya sobrecargados")
        else:
            # No paga dividendos
            if gaps["activos"]["gap_dividendos"] > 0:  # Si falta llegar al 80%
                desglose["dividends"] = 0
                desglose["razones"].append(f"⚠️ No paga dividendos (falta {gaps['activos']['gap_dividendos']:.1f}% para 80%)")

        # 2. Score Sector - EQUIPONDERADO
        sector = activo.get("sector")
        if sector and sector in gaps["sector"]["sectores"]:
            gap_sector = gaps["sector"]["sectores"][sector]["gap"]
            peso_objetivo = gaps["sector"]["peso_objetivo"]

            if gap_sector > 0:  # Sector subponderado
                # Score proporcional al gap (gap más grande = score más alto)
                score_sector = min(100, (gap_sector / peso_objetivo) * 100)
                score += score_sector * self.objetivos["sector"]["peso"]
                desglose["sector"] = score_sector
                desglose["razones"].append(
                    f"Sector {sector} subponderado {gap_sector:+.1f}% (objetivo: {peso_objetivo:.1f}%)"
                )
            elif gap_sector > -5:  # Sector cerca del equilibrio
                score_sector = 30  # Score bajo pero no penaliza
                score += score_sector * self.objetivos["sector"]["peso"]
                desglose["sector"] = score_sector
                desglose["razones"].append(f"Sector {sector} balanceado")
            else:  # Sector sobreponderado
                score_sector = 0
                desglose["sector"] = 0
                desglose["razones"].append(
                    f"⚠️ Sector {sector} sobreponderado {gap_sector:+.1f}% (objetivo: {peso_objetivo:.1f}%)"
                )

        # 3. Score Tipo Activo - EQUIPONDERADO + RESTRICCIÓN 80%
        tipo = activo.get("tipo", "Stock")
        paga_dividendos = dividend_yield > 0

        if tipo in gaps["activos"]["tipos"]:
            gap_tipo = gaps["activos"]["tipos"][tipo]["gap"]
            peso_objetivo = gaps["activos"]["peso_objetivo"]
            gap_dividendos = gaps["activos"]["gap_dividendos"]

            score_tipo = 0

            # Factor 1: Balance del tipo de activo
            if gap_tipo > 0:  # Tipo subponderado
                score_tipo += min(70, (gap_tipo / peso_objetivo) * 70)
                desglose["razones"].append(
                    f"Tipo {tipo} subponderado {gap_tipo:+.1f}% (objetivo: {peso_objetivo:.1f}%)"
                )
            elif gap_tipo < -5:  # Tipo sobreponderado
                desglose["razones"].append(
                    f"⚠️ Tipo {tipo} sobreponderado {gap_tipo:+.1f}%"
                )

            # Factor 2: Cumplir restricción 80% con dividendos
            if gap_dividendos > 0:  # Falta llegar al 80%
                if paga_dividendos:
                    score_tipo += 30  # Bonus por pagar dividendos
                    desglose["razones"].append(
                        f"✓ Ayuda a cumplir 80% con dividendos (falta {gap_dividendos:.1f}%)"
                    )
                else:
                    score_tipo = max(0, score_tipo - 20)  # Penalización si no paga

            score += score_tipo * self.objetivos["activos"]["peso"]
            desglose["activos"] = score_tipo

        # 4. Score Región - EQUIPONDERADO
        region = activo.get("region")
        if region and region in gaps["region"]["regiones"]:
            gap_region = gaps["region"]["regiones"][region]["gap"]
            peso_objetivo = gaps["region"]["peso_objetivo"]

            if gap_region > 0:  # Región subponderada
                score_region = min(100, (gap_region / peso_objetivo) * 100)
                score += score_region * self.objetivos["region"]["peso"]
                desglose["region"] = score_region
                desglose["razones"].append(
                    f"Región {region} subponderada {gap_region:+.1f}% (objetivo: {peso_objetivo:.1f}%)"
                )
            elif gap_region > -5:  # Región cerca del equilibrio
                score_region = 30
                score += score_region * self.objetivos["region"]["peso"]
                desglose["region"] = score_region
            else:  # Región sobreponderada
                desglose["region"] = 0
                desglose["razones"].append(
                    f"⚠️ Región {region} sobreponderada {gap_region:+.1f}%"
                )

        return score, desglose

    def generar_recomendaciones(self, presupuesto_max: float = None, top_n: int = 10) -> List[Dict]:
        """
        Genera lista de activos recomendados para comprar

        Args:
            presupuesto_max: Presupuesto máximo para invertir
            top_n: Número de recomendaciones a retornar

        Returns:
            recomendaciones = [
                {
                    "symbol": "MSFT",
                    "nombre": "Microsoft Corp",
                    "score": 92.5,
                    "cantidad_sugerida": 15,
                    "inversion": 5625.0,
                    "desglose_score": {...},
                    "razones": ["...", "..."],
                    "impacto": {
                        "dividends": +112.5,
                        "sector": {"Technology": -2.3},
                        "activos": {"Stock": +1.2},
                        "region": {"USA": +1.0}
                    }
                },
                ...
            ]
        """
        gaps = self.calcular_gaps()
        recomendaciones = []

        for idx, activo in self.universo.iterrows():
            score, desglose = self.calcular_score_activo(activo, gaps)

            # Calcular cantidad sugerida (ejemplo simple)
            precio = activo.get("price", 100)
            cantidad = max(1, int(1000 / precio))  # Mínimo $1000 por activo

            inversion = cantidad * precio

            # Calcular impacto
            impacto = self._calcular_impacto(activo, cantidad)

            recomendaciones.append({
                "symbol": activo.get("symbol"),
                "nombre": activo.get("nombre", activo.get("symbol")),
                "score": round(score, 2),
                "cantidad_sugerida": cantidad,
                "inversion": round(inversion, 2),
                "precio": precio,
                "desglose_score": desglose,
                "razones": desglose["razones"],
                "impacto": impacto
            })

        # Ordenar por score
        recomendaciones.sort(key=lambda x: x["score"], reverse=True)

        # Filtrar por presupuesto si se especifica
        if presupuesto_max:
            recomendaciones_filtradas = []
            presupuesto_usado = 0
            for rec in recomendaciones:
                if presupuesto_usado + rec["inversion"] <= presupuesto_max:
                    recomendaciones_filtradas.append(rec)
                    presupuesto_usado += rec["inversion"]
            recomendaciones = recomendaciones_filtradas

        return recomendaciones[:top_n]

    def _calcular_impacto(self, activo: pd.Series, cantidad: int) -> Dict:
        """
        Calcula el impacto de comprar un activo en el portafolio
        """
        # TODO: Implementar cálculo real de impacto
        # Requiere conocer valor total del portafolio
        return {
            "dividends": activo.get("dividend_yield", 0) * activo.get("price", 0) * cantidad,
            "sector": {activo.get("sector"): 0.0},  # Cambio en %
            "activos": {activo.get("tipo", "Stock"): 0.0},
            "region": {activo.get("region"): 0.0}
        }

    def simular_impacto_total(self, compras: List[Dict]) -> Dict:
        """
        Simula el impacto total de ejecutar una lista de compras

        Args:
            compras: Lista de recomendaciones a ejecutar

        Returns:
            simulacion = {
                "dividends": {
                    "antes": 3800.0,
                    "despues": 4992.0,
                    "delta": +1192.0,
                    "progreso": 99.8  # % del objetivo
                },
                "sector": {
                    "Technology": {"antes": 35.2, "despues": 28.5, "delta": -6.7},
                    ...
                },
                "inversion_total": 12450.0
            }
        """
        # TODO: Implementar simulación completa
        pass
```

---

## 📐 Algoritmo de Rebalanceo - ESTRATEGIA EQUIPONDERADA

### Flujo de Ejecución

```
1. Obtener Estado Actual
   ├─► DataHub.manager_buysell (actualizado cada 20min)
   └─► Detectar dinámicamente número de categorías en cada dimensión

2. Calcular Pesos Objetivo (EQUIPONDERADO)
   ├─► Sectores: peso_objetivo = 100 / num_sectores_presentes
   ├─► Activos: peso_objetivo = 100 / num_tipos_presentes
   ├─► Regiones: peso_objetivo = 100 / num_regiones_presentes
   └─► Dividendos: target_mensual = target_anual / 12

3. Calcular Gaps (Desbalances)
   ├─► calcular_gaps()
   ├─► Dividendos: Desviación estándar mensual (equilibrio)
   ├─► Sectores: Gap por sector vs peso equiponderado
   ├─► Activos: Gap por tipo vs peso equiponderado + restricción 80% con dividendos
   └─► Regiones: Gap por región vs peso equiponderado

4. Obtener Universo de Activos
   ├─► Solo activos del portafolio actual (booktrading)
   ├─► (Tabla market NO se integra por ahora - pospuesto)
   └─► Filtrar activos válidos (líquidos, no bloqueados)

5. Calcular Score por Activo
   ├─► Para cada activo en universo:
   │   ├─► Score Dividendos (35%): Prioriza meses con bajo ingreso
   │   ├─► Score Sector (30%): Prioriza sectores subponderados
   │   ├─► Score Tipo Activo (20%): Prioriza tipos subponderados + bonus si paga dividendos
   │   └─► Score Región (15%): Prioriza regiones subponderadas
   └─► Score Total = Suma ponderada

6. Ordenar y Filtrar
   ├─► Ordenar por score descendente
   ├─► Aplicar restricciones (presupuesto, liquidez)
   └─► Retornar Top N recomendaciones

7. Simular Impacto (Opcional)
   ├─► Calcular cómo quedaría portafolio después de compras
   ├─► Verificar mejora en equilibrio (reducción de desviación estándar)
   └─► Validar cumplimiento de restricción 80% dividendos
```

### Fórmula de Score - ESTRATEGIA EQUIPONDERADA

```python
Score_Total = (Score_Dividends × 0.35) +
              (Score_Sector × 0.30) +
              (Score_Activo × 0.20) +
              (Score_Region × 0.15)

# Donde cada Score individual está en escala 0-100

# CÁLCULO DE CADA COMPONENTE:

# 1. Score Dividendos (0-100):
#    - Suma gaps de meses donde el activo paga dividendos
#    - Score más alto si ayuda en meses con mayor déficit
#    - Penaliza si paga en meses ya sobrecargados
#    - Penaliza si no paga dividendos (cuando falta llegar al 80%)

# 2. Score Sector (0-100):
#    score_sector = (gap_sector / peso_objetivo_sector) × 100
#    - gap_sector > 0 (subponderado) → score alto
#    - gap_sector ≈ 0 (balanceado) → score neutro (30)
#    - gap_sector < -5 (sobreponderado) → score = 0

# 3. Score Tipo Activo (0-100):
#    score_tipo = (gap_tipo / peso_objetivo_tipo) × 70 + bonus_dividendos(30)
#    - Factor 1 (70 pts): Balance del tipo
#    - Factor 2 (30 pts): Bonus si paga dividendos (cuando falta llegar al 80%)

# 4. Score Región (0-100):
#    score_region = (gap_region / peso_objetivo_region) × 100
#    - Similar a Score Sector (equiponderado puro)
```

**Ejemplo 1: MSFT en portafolio desbalanceado**

```python
# Estado actual del portafolio (EQUIPONDERADO)
portafolio = {
    "sectores": 7,           # 7 sectores → objetivo: 14.29% cada uno
    "tipos_activos": 5,      # 5 tipos (Stock, FCI, Bonds, Crypto, Digital Assets) → objetivo: 20% c/u
    "regiones": 4            # 4 regiones → objetivo: 25% cada una
}

# Gaps actuales (EQUIPONDERADO)
gaps = {
    "dividends": {
        "mensual": {
            "Enero": {"gap": -3000},   # Sobrecargado (recibe mucho)
            "Febrero": {"gap": 2500},  # Déficit
            "Marzo": {"gap": 1800},    # Déficit
            # ...
        },
        "desviacion_std": 2800  # Alta desviación = desbalanceado
    },
    "sector": {
        "peso_objetivo": 14.29,  # 100 / 7 sectores
        "sectores": {
            "Technology": {"gap": -20.91},  # Tiene 35.2%, objetivo 14.29% → sobreponderado
            "Healthcare": {"gap": 5.79}     # Tiene 8.5%, objetivo 14.29% → subponderado
        }
    },
    "activos": {
        "peso_objetivo": 20.0,  # 100 / 5 tipos (Stock, FCI, Bonds, Crypto, Digital Assets)
        "tipos": {
            "Stock": {"gap": -30.0},        # Tiene 50%, objetivo 20% → sobreponderado
            "FCI": {"gap": 10.0},           # Tiene 10%, objetivo 20% → subponderado
            "Bonds": {"gap": 15.0},         # Tiene 5%, objetivo 20% → subponderado
            "Crypto": {"gap": 5.0},         # Tiene 15%, objetivo 20% → subponderado
            "Digital Assets": {"gap": 0.0}  # Tiene 20%, objetivo 20% → balanceado
        },
        "gap_dividendos": 15.0  # Falta 15% para llegar al 80%
    },
    "region": {
        "peso_objetivo": 25.0,  # 100 / 4 regiones
        "regiones": {
            "USA": {"gap": -30.0}  # Tiene 55%, objetivo 25% → sobreponderado
        }
    }
}

# Datos MSFT
msft = {
    "symbol": "MSFT",
    "dividend_yield": 0.75,  # 0.75% anual
    "price": 375,
    "sector": "Technology",
    "tipo": "Stock",
    "region": "USA",
    "mes_pago_dividendo": [0, 3, 6, 9]  # Paga en Enero (mes 0), Abril (3), Julio (6), Octubre (9)
}

# Cálculo de Score:

# 1. Score Dividendos:
#    Paga en Enero (gap: -3000, sobrecargado) → NO ayuda
#    Paga en Abril, Julio, Octubre (necesitaríamos ver gaps) → Supongamos que tampoco ayudan mucho
#    Score_Dividends = 0  (paga en meses ya sobrecargados)

# 2. Score Sector:
#    Technology tiene gap: -20.91% (sobreponderado)
#    Score_Sector = 0  (penaliza comprar más Technology)

# 3. Score Tipo Activo:
#    Stock tiene gap: -30% (sobreponderado)
#    Score_Activo = 0  (penaliza comprar más Stock)
#    Nota: Aunque paga dividendos, no compensa porque Stock ya está sobreponderado

# 4. Score Región:
#    USA tiene gap: -30% (sobreponderado)
#    Score_Region = 0  (penaliza comprar más USA)

# Score Total:
Score_Total = (0 × 0.35) + (0 × 0.30) + (0 × 0.20) + (0 × 0.15) = 0.0

# CONCLUSIÓN: MSFT NO ES RECOMENDADO
# Razones:
# - ⚠️ Sector Technology sobreponderado -20.91% (objetivo: 14.29%)
# - ⚠️ Tipo Stock sobreponderado -30.0% (objetivo: 20.0%)
# - ⚠️ Región USA sobreponderada -30.0% (objetivo: 25.0%)
# - ⚠️ Paga en meses ya sobrecargados
```

**Ejemplo 2: VYM (Vanguard High Dividend Yield ETF) - ACTIVO IDEAL**

```python
# Datos VYM
vym = {
    "symbol": "VYM",
    "dividend_yield": 3.2,  # 3.2% anual
    "price": 109.50,
    "sector": "Utilities",   # Sector subponderado
    "tipo": "FCI",           # Tipo subponderado
    "region": "USA",         # Región sobreponderada (pero compensado por otros factores)
    "mes_pago_dividendo": [2, 5, 8, 11]  # Paga en Marzo, Junio, Sept, Dic (meses diferentes a MSFT)
}

# Mismo portafolio desbalanceado del ejemplo anterior
gaps = {
    "dividends": {
        "mensual": {
            "Marzo": {"gap": 1800},   # Déficit → VYM ayuda aquí
            "Junio": {"gap": 2200},   # Déficit → VYM ayuda aquí
            "Septiembre": {"gap": 1500},  # Déficit → VYM ayuda aquí
            "Diciembre": {"gap": 1900}    # Déficit → VYM ayuda aquí
        }
    },
    "sector": {
        "peso_objetivo": 14.29,
        "sectores": {
            "Utilities": {"gap": 9.29}  # Tiene 5%, objetivo 14.29% → subponderado
        }
    },
    "activos": {
        "peso_objetivo": 20.0,  # 100 / 5 tipos
        "tipos": {
            "FCI": {"gap": 10.0}  # Tiene 10%, objetivo 20% → subponderado
        },
        "gap_dividendos": 15.0  # Falta 15% para 80%
    },
    "region": {
        "peso_objetivo": 25.0,
        "regiones": {
            "USA": {"gap": -30.0}  # Sobreponderado (factor negativo)
        }
    }
}

# Cálculo de Score:

# 1. Score Dividendos:
#    Suma gaps: 1800 + 2200 + 1500 + 1900 = 7400
#    Promedio por mes: 7400 / 4 = 1850
#    Score_Dividends = min(100, 1850 / 1000 * 100) = 100  ✓ EXCELENTE

# 2. Score Sector:
#    Utilities gap: +9.29% (subponderado)
#    Score_Sector = (9.29 / 14.29) × 100 = 65.0  ✓ MUY BUENO

# 3. Score Tipo Activo:
#    FCI gap: +10.0% (subponderado)
#    score_tipo_base = (10.0 / 20.0) × 70 = 35.0
#    Bonus dividendos: +30 (paga dividendos y falta llegar al 80%)
#    Score_Activo = 35.0 + 30 = 65.0  ✓ BUENO

# 4. Score Región:
#    USA gap: -30% (sobreponderado)
#    Score_Region = 0  ✗ (factor negativo)

# Score Total:
Score_Total = (100 × 0.35) + (65 × 0.30) + (65 × 0.20) + (0 × 0.15)
            = 35.0 + 19.5 + 13.0 + 0
            = 67.5

# CONCLUSIÓN: VYM ES ALTAMENTE RECOMENDADO (Score: 67.5/100)
# Razones:
# - ✓ Ayuda equilibrar dividendos en 4 meses: Marzo, Junio, Septiembre
# - ✓ Sector Utilities subponderado +9.29% (objetivo: 14.29%)
# - ✓ Tipo FCI subponderado +10.0% (objetivo: 20.0%)
# - ✓ Ayuda a cumplir 80% con dividendos (falta 15.0%)
# - ⚠️ Región USA sobreponderada -30.0% (único punto negativo)
```

**Ejemplo 3: ASML (empresa europea de semiconductores)**

```python
# Datos ASML
asml = {
    "symbol": "ASML",
    "dividend_yield": 1.2,
    "price": 720,
    "sector": "Technology",    # Sobreponderado (factor negativo)
    "tipo": "Stock",           # Sobreponderado (factor negativo)
    "region": "Europe",        # Subponderado (factor positivo)
    "mes_pago_dividendo": [4, 10]  # Paga en Mayo y Noviembre
}

# Gaps:
gaps = {
    "dividends": {
        "mensual": {
            "Mayo": {"gap": 1200},      # Déficit → ASML ayuda
            "Noviembre": {"gap": 1600}  # Déficit → ASML ayuda
        }
    },
    "sector": {
        "sectores": {
            "Technology": {"gap": -20.91}  # Sobreponderado
        }
    },
    "activos": {
        "peso_objetivo": 20.0,  # 100 / 5 tipos
        "tipos": {
            "Stock": {"gap": -30.0}  # Sobreponderado
        },
        "gap_dividendos": 15.0
    },
    "region": {
        "regiones": {
            "Europe": {"gap": 15.0}  # Tiene 10%, objetivo 25% → subponderado
        }
    }
}

# Cálculo:

# 1. Score Dividendos:
#    Suma gaps: 1200 + 1600 = 2800
#    Promedio: 2800 / 2 = 1400
#    Score_Dividends = min(100, 1400 / 1000 * 100) = 100  ✓

# 2. Score Sector:
#    Technology gap: -20.91% (sobreponderado)
#    Score_Sector = 0  ✗

# 3. Score Tipo Activo:
#    Stock gap: -30.0% (sobreponderado)
#    Score_Activo = 0  ✗

# 4. Score Región:
#    Europe gap: +15% (subponderado)
#    Score_Region = (15 / 25) × 100 = 60.0  ✓

# Score Total:
Score_Total = (100 × 0.35) + (0 × 0.30) + (0 × 0.20) + (60 × 0.15)
            = 35.0 + 0 + 0 + 9.0
            = 44.0

# CONCLUSIÓN: ASML ES MODERADAMENTE RECOMENDADO (Score: 44.0/100)
# Razones:
# - ✓ Ayuda equilibrar dividendos en 2 meses: Mayo, Noviembre
# - ✓ Región Europe subponderada +15.0% (objetivo: 25.0%)
# - ⚠️ Sector Technology sobreponderado -20.91%
# - ⚠️ Tipo Stock sobreponderado -30.0%
#
# Decisión: Considerar solo si no hay mejores opciones que ayuden más en Sector/Activo
```

### 🎯 Nota Importante sobre Rebalanceo

**El rebalanceo se realiza PRINCIPALMENTE mediante COMPRAS (hacia arriba):**

- **Estrategia Principal - Compras** (Método preferido):
  - Cuando un sector/activo/región está **sobreponderado** (gap negativo):
    - ✓ Se **compran** otras categorías subponderadas para equilibrar
    - Con el tiempo, al crecer las demás, el peso relativo del sobreponderado disminuye
  - **Ventajas**:
    - ✅ Evita triggers fiscales (no hay ventas → no hay impuestos)
    - ✅ Mantiene activos ganadores (deja correr las ganancias)
    - ✅ Aprovecha oportunidades (compra lo que está bajo)
    - ✅ Rebalanceo gradual y pasivo

- **Estrategia Secundaria - Ventas** (Cuando sea necesario):
  - Se **podría vender** si:
    - El desbalance es muy extremo (ej: un sector >50% del portafolio)
    - Necesitas capital inmediato para comprar oportunidades críticas
    - Un activo sobreponderado tiene fundamentales deteriorados
    - Razones fiscales lo justifican (pérdidas para compensar ganancias)
  - **Importante**: Las ventas no son el foco principal, pero están permitidas

- **Ejemplo práctico:**
  - Portafolio actual: Stock 50%, FCI 10%, Bonds 5%, Crypto 15%, Digital Assets 20%
  - Objetivo equiponderado: 20% cada uno (5 tipos)

  - **Opción A - Solo Compras (Preferida)**:
    - Comprar $30,000 en FCI, Bonds y Crypto (subponderados)
    - Nuevo total: $100,000 → Stock ahora es 50% (se rebalanceará gradualmente)

  - **Opción B - Compras + Ventas (Si es necesario)**:
    - Vender parte de Stock sobreponderado (ej: $15,000)
    - Usar ese capital + efectivo nuevo para comprar FCI/Bonds/Crypto
    - Rebalanceo más rápido pero con implicaciones fiscales

### Prioridad de Rebalanceo:

1. **1ra opción**: Comprar activos subponderados con capital nuevo
2. **2da opción**: Si el desbalance es crítico, considerar ventas parciales
3. **Objetivo**: Llegar al equilibrio equiponderado de forma eficiente

---

## 📊 Visualización con ProgressBar

### Integración con ProgressBar Mejorado

El **ProgressBar con soporte de valores negativos** es ideal para mostrar **gaps de rebalanceo**.

#### A) Mostrar Gap de Dividendos

```python
from Class_customer import ProgressBar

# Obtener datos
gaps = rebalanceo.calcular_gaps()
div_gap = gaps["dividends"]

# Crear ProgressBar
bar_dividends = ProgressBar(
    parent_frame,
    label="Dividendos Mensuales:",
    partida=0,
    avance=div_gap["actual"],        # $3,800 actual
    proyeccion=div_gap["objetivo"],  # $5,000 objetivo
    width=400,
    height=20,
    bg_color=DataHub.colors["bgcolor"]
)
bar_dividends.pack(pady=5)

# Resultado visual:
# Dividendos Mensuales: [████████████░░░░░░] $3.8K / $5.0K (76%)
#                       Color: NARANJA (entre 50-75%)
```

#### B) Mostrar Balance de Sectores

```python
# Para cada sector
gaps_sector = gaps["sector"]

for sector, data in sorted(gaps_sector.items(), key=lambda x: abs(x[1]["gap"]), reverse=True):
    actual = data["actual"]
    objetivo = data["objetivo"]
    gap = data["gap"]

    # Color automático:
    # - Rojo si sobreponderado (actual > objetivo)
    # - Verde si balanceado
    # - Naranja si subponderado

    bar = ProgressBar(
        sectores_frame,
        label=f"{sector[:15]}:",
        partida=0,
        avance=actual,
        proyeccion=objetivo,
        width=350,
        height=15,
        bg_color=DataHub.colors["bgcolor"]
    )
    bar.pack(pady=3)

# Ejemplos de salida:
# Technology:  [████████████████████] 35.2% / 25.0% (141%)  ← ROJO (sobreponderado)
# Healthcare:  [████████░░░░░░░░░░░░] 12.0% / 20.0% (60%)   ← NARANJA (subponderado)
# Financial:   [████████████████░░░░] 28.7% / 20.0% (143%)  ← ROJO (sobreponderado)
```

#### C) Visualización Completa de Recomendaciones

```python
def mostrar_recomendaciones_ui(parent):
    """
    Muestra interfaz completa de recomendaciones en manager_buysell_system()
    """
    rebalanceo = RebalanceoCartera()
    gaps = rebalanceo.calcular_gaps()
    recomendaciones = rebalanceo.generar_recomendaciones(top_n=10)

    # Frame principal con scroll
    main_frame = tk.Frame(parent, bg=DataHub.colors["bgcolor"])
    main_frame.pack(fill=tk.BOTH, expand=True)

    # Canvas con scrollbar
    canvas = tk.Canvas(main_frame, bg=DataHub.colors["bgcolor"], highlightthickness=0)
    scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
    scrollable = tk.Frame(canvas, bg=DataHub.colors["bgcolor"])

    scrollable.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )

    canvas.create_window((0, 0), window=scrollable, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    # === HEADER ===
    header = tk.Label(
        scrollable,
        text="🎯 RECOMENDACIONES DE COMPRA - Rebalanceo de Cartera",
        font=("Segoe UI", 14, "bold"),
        bg=DataHub.colors["bgcolor"],
        fg="cyan"
    )
    header.pack(pady=15, padx=10, anchor=tk.W)

    # === SECCIÓN: GAPS ACTUALES ===
    gaps_section = tk.Frame(scrollable, bg=DataHub.colors["bgcolor"])
    gaps_section.pack(fill=tk.X, padx=15, pady=10)

    tk.Label(
        gaps_section,
        text="📊 ESTADO ACTUAL DEL PORTAFOLIO",
        font=("Segoe UI", 11, "bold"),
        bg=DataHub.colors["bgcolor"],
        fg="yellow"
    ).pack(anchor=tk.W, pady=(0, 10))

    # ProgressBar para Dividendos
    ProgressBar(
        gaps_section,
        label="💰 Dividendos Mensuales:",
        partida=0,
        avance=gaps["dividends"]["actual"],
        proyeccion=gaps["dividends"]["objetivo"],
        width=400,
        height=18
    ).pack(pady=5, anchor=tk.W)

    # ProgressBars para Top 3 sectores más desbalanceados
    sectores_sorted = sorted(gaps["sector"].items(), key=lambda x: abs(x[1]["gap"]), reverse=True)

    for sector, data in sectores_sorted[:5]:
        ProgressBar(
            gaps_section,
            label=f"🏢 {sector[:18]}:",
            partida=0,
            avance=data["actual"],
            proyeccion=data["objetivo"],
            width=400,
            height=14
        ).pack(pady=3, anchor=tk.W)

    # Separador
    ttk.Separator(scrollable, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=15)

    # === SECCIÓN: RECOMENDACIONES ===
    rec_section = tk.Frame(scrollable, bg=DataHub.colors["bgcolor"])
    rec_section.pack(fill=tk.X, padx=15, pady=10)

    tk.Label(
        rec_section,
        text=f"📈 TOP {len(recomendaciones)} ACTIVOS RECOMENDADOS PARA COMPRAR",
        font=("Segoe UI", 11, "bold"),
        bg=DataHub.colors["bgcolor"],
        fg="yellow"
    ).pack(anchor=tk.W, pady=(0, 10))

    # Listar recomendaciones
    for i, rec in enumerate(recomendaciones, 1):
        # Frame para cada activo
        activo_frame = tk.Frame(rec_section, bg=DataHub.colors["cgcolor"], relief=tk.RAISED, bd=1)
        activo_frame.pack(fill=tk.X, pady=8, padx=5)

        # Header del activo
        header_frame = tk.Frame(activo_frame, bg=DataHub.colors["cgcolor"])
        header_frame.pack(fill=tk.X, padx=10, pady=5)

        # Ranking y símbolo
        stars = "⭐" * min(5, int(rec["score"] / 20))
        tk.Label(
            header_frame,
            text=f"{i}. {stars} {rec['symbol']} - {rec['nombre']}",
            font=("Segoe UI", 10, "bold"),
            bg=DataHub.colors["cgcolor"],
            fg="lightgreen",
            anchor=tk.W
        ).pack(side=tk.LEFT)

        # Score
        tk.Label(
            header_frame,
            text=f"Score: {rec['score']:.1f}/100",
            font=("Segoe UI", 9),
            bg=DataHub.colors["cgcolor"],
            fg="orange",
            anchor=tk.E
        ).pack(side=tk.RIGHT)

        # Detalles
        details_frame = tk.Frame(activo_frame, bg=DataHub.colors["cgcolor"])
        details_frame.pack(fill=tk.X, padx=20, pady=(0, 5))

        tk.Label(
            details_frame,
            text=f"Cantidad sugerida: {rec['cantidad_sugerida']} acciones  |  "
                 f"Inversión: ${rec['inversion']:,.0f}  |  "
                 f"Precio: ${rec['precio']:.2f}",
            font=("Segoe UI", 8),
            bg=DataHub.colors["cgcolor"],
            fg="lightgray"
        ).pack(anchor=tk.W)

        # Razones
        razones_frame = tk.Frame(activo_frame, bg=DataHub.colors["cgcolor"])
        razones_frame.pack(fill=tk.X, padx=20, pady=(5, 10))

        tk.Label(
            razones_frame,
            text="Razones:",
            font=("Segoe UI", 8, "bold"),
            bg=DataHub.colors["cgcolor"],
            fg="cyan"
        ).pack(anchor=tk.W)

        for razon in rec["razones"]:
            tk.Label(
                razones_frame,
                text=f"  ✓ {razon}",
                font=("Segoe UI", 8),
                bg=DataHub.colors["cgcolor"],
                fg="white"
            ).pack(anchor=tk.W)

    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
```

---

## 🚀 Plan de Implementación

### Fase 1: Configuración y Datos (Semana 1)

**Objetivo**: Preparar infraestructura básica

#### Tareas:
1. ✅ Crear `config_balance.py` con objetivos
   - Definir pesos objetivo por sector
   - Definir distribución por tipo de activo
   - Definir distribución geográfica
   - Definir objetivo de dividendos mensuales

2. ✅ Crear universo de activos
   - Opción A: Leer desde base de datos existente
   - Opción B: Crear archivo CSV con activos candidatos
   - Campos mínimos: `symbol, nombre, sector, tipo, region, dividend_yield, price`

3. ✅ Validar datos de `manager_buysell`
   - Verificar que `grupo_sector()` devuelve summary correcto
   - Verificar que `grupo_dividendo()` calcula media correctamente
   - Agregar logging para debugging

#### Entregables:
- `config_balance.py` con configuración completa
- `universo_activos.csv` o método para obtener desde DB
- Script de validación de datos

---

### Fase 2: Motor de Rebalanceo (Semana 2-3)

**Objetivo**: Implementar algoritmo de recomendaciones

#### Tareas:
1. ✅ Implementar `Class_Rebalanceo.py`
   - Método `calcular_gaps()`
   - Método `calcular_score_activo()`
   - Método `generar_recomendaciones()`
   - Tests unitarios para cada método

2. ✅ Ajustar pesos y fórmulas
   - Ejecutar con datos reales
   - Validar que recomendaciones tengan sentido
   - Ajustar pesos según preferencias

3. ✅ Implementar simulación de impacto
   - Calcular cómo cambiarían los % después de compras
   - Validar que mejora el balance

#### Entregables:
- `Class_Rebalanceo.py` funcional
- Suite de tests
- Documentación de algoritmo

---

### Fase 3: Integración con UI (Semana 4)

**Objetivo**: Visualizar recomendaciones en `manager_buysell_system()`

#### Tareas:
1. ✅ Modificar `manager_buysell_system()` en `DashMainV9_ia.py`
   - Agregar tab "Recomendaciones" en Notebook
   - Implementar `mostrar_recomendaciones_ui()`

2. ✅ Integrar ProgressBar para gaps
   - Mostrar gap de dividendos
   - Mostrar top 5 sectores desbalanceados
   - Usar colores automáticos (rojo/naranja/verde)

3. ✅ Mostrar lista de recomendaciones
   - Ordenar por score
   - Mostrar razones de cada recomendación
   - Botón para simular impacto

#### Entregables:
- UI funcional con ProgressBars
- Integración completa con manager_buysell
- Manual de usuario

---

### Fase 4: Refinamiento (Semana 5)

**Objetivo**: Mejorar precisión y usabilidad

#### Tareas:
1. ✅ Agregar restricciones adicionales
   - Liquidez mínima del activo
   - Restricción de sectores prohibidos
   - Límite de concentración por activo

2. ✅ Implementar guardado de recomendaciones
   - Guardar en BD para seguimiento
   - Comparar recomendaciones vs decisiones reales

3. ✅ Integración con Telegram (opcional)
   - Comando `/rebalancear` para ver recomendaciones
   - Alerta automática si desbalance > 20%

#### Entregables:
- Sistema completo refinado
- Documentación actualizada
- Casos de uso probados

---

## 💡 Ejemplos de Uso

### Ejemplo 1: Ejecución Básica

```python
from Class_Rebalanceo import RebalanceoCartera
from Class_customer import DataHub

# Crear instancia
rebalanceo = RebalanceoCartera()

# Calcular gaps
gaps = rebalanceo.calcular_gaps()
print("📊 Gaps actuales:")
print(f"  Dividendos: ${gaps['dividends']['gap']:,.2f} mensuales")
print(f"  Sectores desbalanceados: {len([s for s in gaps['sector'].values() if abs(s['gap']) > 5])}")

# Generar recomendaciones
recomendaciones = rebalanceo.generar_recomendaciones(presupuesto_max=50_000, top_n=5)

print(f"\n🎯 Top 5 Recomendaciones:")
for i, rec in enumerate(recomendaciones, 1):
    print(f"\n{i}. {rec['symbol']} - Score: {rec['score']:.1f}/100")
    print(f"   Inversión: ${rec['inversion']:,.0f}")
    print(f"   Razones:")
    for razon in rec['razones']:
        print(f"     ✓ {razon}")
```

**Salida esperada:**
```
📊 Gaps actuales:
  Dividendos: $1,200.00 mensuales
  Sectores desbalanceados: 3

🎯 Top 5 Recomendaciones:

1. VYM - Score: 88.5/100
   Inversión: $4,350
   Razones:
     ✓ Contribuye $145.50/mes en dividendos
     ✓ Sector Utilities bajo objetivo (+5.0%)
     ✓ ETF diversificado geográficamente

2. JNJ - Score: 82.3/100
   Inversión: $3,180
   Razones:
     ✓ Sector Healthcare muy bajo (-8.0%)
     ✓ Dividendos estables: $95.40/mes
     ✓ Región USA equilibrada

...
```

### Ejemplo 2: Simulación de Impacto

```python
# Seleccionar las 3 primeras recomendaciones
compras_propuestas = recomendaciones[:3]

# Simular impacto
simulacion = rebalanceo.simular_impacto_total(compras_propuestas)

print("📈 Simulación de Impacto:")
print(f"\nDividendos:")
print(f"  Antes:   ${simulacion['dividends']['antes']:,.0f}/mes")
print(f"  Después: ${simulacion['dividends']['despues']:,.0f}/mes (+{simulacion['dividends']['delta']:,.0f})")
print(f"  Progreso: {simulacion['dividends']['progreso']:.1f}% del objetivo")

print(f"\nSectores más impactados:")
for sector, cambio in list(simulacion['sector'].items())[:3]:
    print(f"  {sector}: {cambio['antes']:.1f}% → {cambio['despues']:.1f}% ({cambio['delta']:+.1f}%)")

print(f"\nInversión total necesaria: ${simulacion['inversion_total']:,.0f}")
```

### Ejemplo 3: Integración en UI

```python
# En DashMainV9_ia.py, dentro de manager_buysell_system()

def display_recomendaciones(parent_frame):
    """
    Muestra recomendaciones de rebalanceo con ProgressBars
    """
    rebalanceo = RebalanceoCartera()
    gaps = rebalanceo.calcular_gaps()

    # Header
    tk.Label(
        parent_frame,
        text="🎯 REBALANCEO DE CARTERA",
        font=("Segoe UI", 14, "bold"),
        bg=DataHub.colors["bgcolor"],
        fg="cyan"
    ).pack(pady=10)

    # Mostrar gap de dividendos con ProgressBar
    ProgressBar(
        parent_frame,
        label="💰 Dividendos Objetivo:",
        partida=0,
        avance=gaps["dividends"]["actual"],
        proyeccion=gaps["dividends"]["objetivo"],
        width=450,
        height=20
    ).pack(pady=10)

    # Generar y mostrar recomendaciones
    recomendaciones = rebalanceo.generar_recomendaciones(top_n=5)

    for i, rec in enumerate(recomendaciones, 1):
        # Frame para cada recomendación
        rec_frame = tk.Frame(parent_frame, bg=DataHub.colors["cgcolor"], relief=tk.RAISED, bd=2)
        rec_frame.pack(fill=tk.X, pady=5, padx=10)

        # ... (resto del código de visualización)
```

---

## 📚 Anexos

### A. Estructura de Datos del Universo de Activos

```python
# universo_activos.csv
"""
symbol,nombre,sector,tipo,region,dividend_yield,price,market_cap,volume_avg
AAPL,Apple Inc,Technology,Stock,USA,0.0051,185.50,2850000000000,50000000
MSFT,Microsoft Corp,Technology,Stock,USA,0.0075,375.00,2780000000000,25000000
JNJ,Johnson & Johnson,Healthcare,Stock,USA,0.0295,159.00,395000000000,6500000
VYM,Vanguard High Dividend Yield ETF,Utilities,Stock,USA,0.0315,109.50,45000000000,1200000
BTC-USD,Bitcoin,N/A,Crypto,Global,0.0000,43500.00,850000000000,20000000000
...
"""
```

### B. Logs de Ejemplo

```python
# Habilitar logging en Class_Rebalanceo.py
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Rebalanceo")

# En calcular_gaps()
logger.info(f"Gap Dividendos: ${gap:.2f} ({gap_pct:.1f}% del objetivo)")
logger.info(f"Sectores subponderados: {[s for s, g in gaps['sector'].items() if g['gap'] > 5]}")

# En calcular_score_activo()
logger.debug(f"{activo['symbol']}: Score={score:.2f} (div={desglose['dividends']:.1f}, sector={desglose['sector']:.1f})")
```

### C. Casos de Prueba

```python
import unittest
from Class_Rebalanceo import RebalanceoCartera

class TestRebalanceo(unittest.TestCase):

    def setUp(self):
        # Configurar datos de prueba
        DataHub.manager_buysell = {
            "dividends": {"media": 3800},
            "sector": {"summary": {"Technology": 35, "Healthcare": 12}},
            "activos": {"summary": {"Stock": 70, "Crypto": 30}},
            "region": {"summary": {"USA": 60, "Europe": 40}}
        }
        self.rebalanceo = RebalanceoCartera()

    def test_calcular_gaps_dividends(self):
        gaps = self.rebalanceo.calcular_gaps()
        self.assertEqual(gaps["dividends"]["gap"], 1200)  # 5000 - 3800

    def test_score_sector_subponderado(self):
        activo = pd.Series({"sector": "Healthcare", "dividend_yield": 0.03, "price": 150})
        gaps = self.rebalanceo.calcular_gaps()
        score, _ = self.rebalanceo.calcular_score_activo(activo, gaps)
        self.assertGreater(score, 50)  # Healthcare subponderado debe tener score alto

    def test_score_sector_sobreponderado(self):
        activo = pd.Series({"sector": "Technology", "dividend_yield": 0.01, "price": 300})
        gaps = self.rebalanceo.calcular_gaps()
        score, _ = self.rebalanceo.calcular_score_activo(activo, gaps)
        self.assertLess(score, 30)  # Technology sobreponderado debe tener score bajo

if __name__ == '__main__':
    unittest.main()
```

---

**Documento generado:** 2025-12-29
**Versión:** 3.1 (Estrategia Equiponderada - Restricción por Valor)
**Autor:** Claude Code (Sonnet 4.5)
**Estrategia:** Equiponderado Puro Dinámico (100 / num_categorías)
**Tipos de Activos:** Stock, FCI, Bonds, Crypto, Digital Assets (5 tipos → 20% c/u)
**Método de Rebalanceo:** Solo compras hacia arriba (no ventas)
**Restricción:** 80% del portafolio (POR VALOR MONETARIO) debe pagar dividendos
**Estado:** ✅ Documentación completa - Lista para revisión e implementación

---

## 📋 Puntos Pendientes para Implementación

**Resueltos:**
- ✅ **Punto 1**: Tipos de activos que generan dividendos → Stock, Bonds, Cash únicamente
- ✅ **Punto 2**: Cálculo restricción 80% → Por valor monetario (no por cantidad de posiciones)

**Por Resolver:**
- ⏸️ **Punto 3**: Integración de tabla `market` → **POSPUESTO** (ahora no se integra)
- 🔧 **Punto 4**: Obtención de meses de pago de dividendos → **EN REPLANTEO**
  - **Problema actual**: yfinance se queda con datos antiguos de activos que dejaron de pagar dividendos
  - **Solución propuesta**: Migrar a Interactive Brokers API (websocket)
  - **Ubicación**: `DashMainV9_ia.py:decodifica_message_websocket()` (línea 332)
  - **Campos disponibles en IB API**:
    - `"7286"`: Dividendo actual
    - `"7287"`: % Dividend yield
    - `"7288"`: Ex-dividend date (fecha ex-dividendo)
    - `"7672"`: TTM Dividends (últimos 12 meses)
    - `"7671"`: Next dividend amount (próximo dividendo)
- ⏳ **Punto 5**: Manejo de sectores para Crypto/Digital Assets
- ✅ **Punto 6**: Determinación de región/país → Campo `region` disponible en tabla `inversiones`
- ✅ **Punto 7**: Parámetros financieros → Disponibles en tablas `plan` y `variables_plan`

**Datos Confirmados:**
- Campo `region` está en tabla `inversiones` (no requiere implementación adicional)
- Parámetros como objetivo anual de dividendos y dividend yield mínimo están en `plan` y `variables_plan`
- Universo de activos se limita a lo que ya está en **booktrading** (portafolio actual)
