# AppOO – Resumen de Conversación y Contexto del Proyecto
**Fecha:** 2026-03-14  
**Autor:** Wilmer Gutierrez

---

## 1. Objetivo de esta Conversación

Definir cómo compartir contexto entre claude.ai (diseño) y Claude Code en VS Code (implementación), usando el flujo:

```
Chat claude.ai (diseño)  →  .md actualizado  →  Doc\ en proyecto  →  Claude Code lee contexto
```
---

## 4. Conectores MCP Explorados

| Conector | Estado | Uso |
|----------|--------|-----|
| Daloopa | ❌ Requiere dominio institucional | Fundamentales SEC |
| Alpha Vantage | ✅ Gratuito con API key | Fundamentales + técnicos |
| Financial Datasets | ✅ Gratuito | Income statement, balance sheet |

**Alpha Vantage** — pendiente de configurar:
- API key gratuita: [alphavantage.co](https://www.alphavantage.co)
- URL connector: `https://mcp.alphavantage.co/mcp?apikey=TU_KEY`
- Settings → Connectors → Add custom connector

---

## 5. Módulo Siguiente: Class_InstitucionalScore.py

Especificación base en: `Doc\institutional_dividend_screener_design.md`

**Pendiente de diseñar en próxima sesión:**
- Manejo de errores yfinance por símbolo
- Normalización del score (escala, outliers)
- Frecuencia de actualización
- Integración con screener existente (ranking combinado)

---

## 6. Roadmap AppOO

| # | Módulo | Estado |
|---|--------|--------|
| 1 | Motor de valoración (ValuationEngine.py) | 🔧 En progreso |
| 2 | Dashboard financiero histórico | ✅ |
| 3 | Portfolio Optimizer (IO) | ⬜ |
| 4 | Retirement Simulator (Monte Carlo) | ⬜ |
| 5 | Sistema de alertas inteligentes | 🔧 |
| 6 | Class_InstitucionalScore.py | 🔧 En diseño |
