import streamlit as st
import pandas as pd
from pymysql import connect, Error
from sqlalchemy import create_engine

# Configuración de la página (Ancho completo)
st.set_page_config(layout="wide", page_title="TV", initial_sidebar_state="collapsed")

# --- CSS AGRESIVO para ganar cada píxel de alto
st.markdown(
    """
    <style>
        .block-container {
            padding-top: 0rem;
            padding-bottom: 1rem;
            padding-left: 1rem;
            padding-right: 1rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- BARRA LATERAL (Filtros) ---
st.sidebar.header("My Assets")
ticker = st.sidebar.selectbox("select", ["CCI", "FMC", "TLT"])

## 3. Cálculo de altura
# '98vh' significa 98% del alto de la ventana visual (viewport height)
# Usamos un poquito menos de 100 para evitar que aparezca la barra de scroll
chart_height = 780
chart_width = 300

# Insertamos el Widget de TradingView mediante un componente HTML
st.subheader(f"symbol: {ticker}")
st.components.v1.html(
    f"""
    <div class="tradingview-widget-container" style="height:{chart_height}px; {chart_width}px;">
        <div id="tradingview_full" style="height:100%; width:100%;"></div>
        <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
        <script type="text/javascript">
        new TradingView.widget({{
            "autosize": true,
            "symbol": "{ticker}",
            "interval": "D",
            "timezone": "Etc/UTC",
            "theme": "dark",
            "style": "1",
            "locale": "es",
            "toolbar_bg": "#f1f3f6",
            "enable_publishing": true,
            "hide_side_toolbar": false,
            "hide_top_toolbar": false,
            "allow_symbol_change": true,
            "withdateranges": true,
            "hide_legend": false,
            "save_image": true,
            "details": true,
            "hotlist": true,
            // --- AGREGAR ESTO ---
            "studies": [
            "GutierrezW;kPuoGBGx", "GutierrezW;1aKxXAmg"
            ],
            "container_id": "tradingview_full"
        }});
        </script>
    </div>
""",
    height=780,
)
