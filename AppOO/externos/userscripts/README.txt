================================================================================
  SETUP TRADINGVIEW + INDICADORES
================================================================================


1. CREAR CUENTA TRADINGVIEW
----------------------------
Registrarse en: https://www.tradingview.com
El plan gratuito es suficiente para usar los indicadores.


2. AGREGAR LOS INDICADORES
---------------------------
En TradingView, abrir un grafico y hacer click en "Indicators" (arriba).

Buscar por autor: GutierrezW

Agregar los dos indicadores:
  - EMA/MACD cross {dual 4 EMA (V2.0)}   <- medias moviles en el grafico
  - RSI Cross + VIX + Volume (v5.1)       <- panel debajo del grafico

Hacer click en la estrella para agregarlos a Favoritos.


3. INSTALAR EL PANEL DE LA APP (tv_panel.js)
---------------------------------------------
El panel conecta TradingView con la app AppOO para ver datos
de la cartera directamente en el grafico.

Paso 1 - Instalar Tampermonkey (extension del browser):
  Chrome: https://chrome.google.com/webstore/detail/tampermonkey
  Firefox: https://addons.mozilla.org/firefox/addon/tampermonkey
  Instalar y activar la extension.

Paso 2 - Instalar el script:
  - Abrir Tampermonkey -> Dashboard
  - Click en el icono "+" (nuevo script)
  - Borrar todo el contenido que aparece por defecto
  - Pegar el contenido del archivo tv_panel.js (de la carpeta setup_hijo)
  - Guardar (Ctrl+S)

Paso 3 - Verificar:
  - Abrir TradingView en el browser
  - Debe aparecer un panel flotante en el grafico con datos de la cartera
  - Si no aparece: verificar que Tampermonkey este activado


4. COMO FUNCIONA EL PANEL
--------------------------
  - El panel se conecta a la app AppOO que debe estar corriendo
  - Muestra datos de posicion: precio promedio, zona objetivo, etc.
  - Se puede arrastrar y minimizar


5. REQUISITO — APP CORRIENDO
------------------------------
Para que el panel de TradingView funcione, la app AppOO debe estar
abierta y corriendo en la misma maquina. El panel se comunica con
la app a traves del puerto 5050 (localhost).

================================================================================
