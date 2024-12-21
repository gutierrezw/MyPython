from datetime import date, datetime
import time

# Crear un objeto date
fecha = datetime.now()

# Obtener la marca de tiempo (timestamp)
#timestamp = datetime.combine(fecha, datetime.min.time()).timestamp()
# fecha = datetime(1694228400000)
fecha = time.time()
print(fecha)
timestamp = datetime(fecha).timestamp()

# Calling the fromtimestamp() function
# to get date from the current time
date_From_CurrentTime = datetime.date.fromtimestamp(Todays_time);
print(f"Fecha: {fecha}")
print(f"Timestamp: {timestamp}")
