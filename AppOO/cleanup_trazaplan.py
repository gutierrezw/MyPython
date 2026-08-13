import pymysql
from config import MYSQL_CONFIG

conn = pymysql.connect(**MYSQL_CONFIG)
cursor = conn.cursor(pymysql.cursors.DictCursor)

# Obtener todos los registros de trazaplan para la cuenta U4214563
cursor.execute("SELECT id, meta, status FROM trazaplan WHERE idcuenta='U4214563' ORDER BY meta, id")
registros = cursor.fetchall()

print(f"Total de registros: {len(registros)}\n")

# Agrupar por año (meta)
años = {}
for reg in registros:
    año = reg['meta']
    if año not in años:
        años[año] = []
    años[año].append(reg)

# Identificar duplicados
ids_a_eliminar = []
for año, regs in sorted(años.items()):
    if len(regs) > 1:
        print(f"Año {año}: {len(regs)} registros")
        # Mantener el primero, eliminar el resto
        for reg in regs[1:]:
            print(f"  - Eliminar ID {reg['id']} (status: {reg['status']})")
            ids_a_eliminar.append(reg['id'])

if ids_a_eliminar:
    print(f"\nTotal de registros a eliminar: {len(ids_a_eliminar)}")
    print("¿Deseas continuar? (S/n)")
    respuesta = input().strip().lower()
    
    if respuesta in ('s', ''):
        # Eliminar registros
        for id_reg in ids_a_eliminar:
            cursor.execute("DELETE FROM trazaplan WHERE id=%s", (id_reg,))
        conn.commit()
        print(f"Eliminados {len(ids_a_eliminar)} registros")
else:
    print("No hay duplicados que eliminar")

cursor.close()
conn.close()
