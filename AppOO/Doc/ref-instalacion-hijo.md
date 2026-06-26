# Instalación perfil hijo — AppOO

## Tabs habilitados
- Crypto
- BotCrypto
- ARS (Fondos de Inversión)
- Finance

---

## PASO 1 — Probar perfil localmente (tu máquina)

Antes de buildear el exe, verificar que los tabs cargan bien:

```
python DashMain.py --profile hijo
```

Debe mostrar solo 4 tabs: Crypto, Ars, BotCrypto, Finance.

---

## PASO 2 — Generar el ejecutable (tu máquina)

```
buildExe.bat hijo
```

El exe queda en:
```
AppOO\dist\hijo\AppOO_hijo\
```

---

## PASO 3 — Exportar la base de datos (tu máquina)

```
AppTest\export_hijo.bat
```

Genera en `AppTest\`:
- `hijo_estructura.sql` — tablas vacías (datos personales)
- `hijo_datos.sql` — tablas de referencia (precios, config, categorías)

---

## PASO 4 — Instalar en la máquina del hijo

### 4.1 Instalar MySQL 8.x
Descargar desde: https://dev.mysql.com/downloads/mysql/

### 4.2 Crear la base de datos
```sql
CREATE DATABASE bdinv CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 4.3 Importar estructura y datos
Abrir CMD en la carpeta donde están los .sql y ejecutar en orden:
```
mysql -u root -p bdinv < hijo_estructura.sql
mysql -u root -p bdinv < hijo_datos.sql
```

### 4.4 Copiar el ejecutable
Copiar toda la carpeta `AppOO_hijo\` a la máquina del hijo (USB o red).
No copiar solo el .exe — necesita los archivos de `_internal\`.

### 4.5 Configurar credenciales Binance
El hijo configura sus propias claves API desde la UI de la app
(tabla `sesion` queda vacía — se completa desde la pantalla de configuración).

---

## Estructura de carpetas en la máquina del hijo

```
AppOO_hijo\
├── AppOO_hijo.exe       <- doble click para arrancar
├── profiles\
│   └── hijo.json
├── logs\                <- se crea automáticamente
├── tmp\                 <- se crea automáticamente
└── _internal\           <- no tocar
```

---

## Archivos clave del proyecto

| Archivo | Propósito |
|---------|-----------|
| `profiles/hijo.json` | Define qué tabs se muestran |
| `DashMain_hijo.py` | Entry point del exe hijo |
| `buildExe.bat hijo` | Genera el exe |
| `AppTest/export_hijo.bat` | Exporta la BD |

---

## Notas

- La máquina del hijo no necesita Python instalado.
- Solo necesita MySQL local corriendo en `localhost:3306`.
- Si en el futuro se agregan tabs al perfil hijo, editar `profiles/hijo.json` y rebuildear.
