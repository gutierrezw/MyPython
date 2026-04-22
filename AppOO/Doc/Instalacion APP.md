C:\Users\54911\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Python 3.11
==================================================================================
instalacion de modulos

github:
    https://github.com/gutierrezw/MyPython

Softare y Datos:
	./MyPython
	./dumps


Software base:
	java: https://www.java.com/es/download/ie_manual.jsp
	node: https://nodejs.org/es (latest LTS for windows)
	mysql : https://dev.mysql.com/downloads/
	python install Nabager: https://www.python.org/downloads/windows/
	tsw: https://www.interactivebrokers.co.uk/es/trading/ib-api.php
	git: https://git-scm.com/downloads/win
	clientportal.gw:  https://www.interactivebrokers.com/es/trading/ib-api.php
		

Excepciones:
	clientportal.gw:  mover las carptas a resource ubicada en Mypython
	Ejecutar eventualmente TSW para que se instalen nuevos certificados o prametros globales de las API
	Copiar confg.yaml deszde backup a root -- configuracion personalziada para el puerto 5501	
	


Comandos upgrate python
===================================================================================
pip list
pip install <paquete>
pip uninstall <paquete>
cuando cambie de versi�n
Set-ExecutionPolicy -ExecutionPolicy Unrestricted -Scope CurrentUser
Get-ExecutionPolicy -List

== identifica las dependencias de APP
pip install pipreqs

== Ejecuta
pipreqs --force
pip install -r requirements.txt


Ejecución de API
resources\bin\run.bat resources\root\conf.yaml
==================================================================================
Instalación de API IBKRs  desde directorio

cd  C:\Users\54911\Documents\MyPython\TWS-API\source\pythonclient
pip install .
==================================================================================

==================================================================================
API Key
vxep6cM1R0KVPgY3J4mS2PvvgpPGzGaLVcIeMxeqHc82y6QuATBYlcBrRvBhivKs
Secret Key
yvXIfJGvdVJ8iSQN2qZKfUxUQfY9tcLMrlkJZeVmlUdH0CBVJ4igM7yg8CqH4N8J
==================================================================================
Binance-conector

pip install binance-connector

