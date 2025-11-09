# 🧭 Resumen Técnico — Configuración de IBKR Client Portal Gateway con Certificado Local y Java 21

## 📌 Objetivo
Configurar el **Client Portal Gateway de IBKR** para:
- Ejecutarse correctamente con **Java 21**.
- Usar un **certificado SSL local (autofirmado)** para acceder al Gateway desde `https://localhost:5000`.
- Mantener la conexión segura con los servidores oficiales de IBKR (`https://api.ibkr.com`).
- Eliminar el error `javax.net.ssl.SSLHandshakeException: Received fatal alert: certificate_unknown`.

---

## 🔐 1️⃣ Generación del certificado `ibkrkeystore.jks`

**Requisitos previos**
- Java 21 instalado (verificar con `java -version`).
- Ubicarse en el directorio del proyecto:
  ```powershell
  cd "C:\Users\InversionesWildaga\Documents\MyPython\ResourcesIbrks\root"
  ```

**Crear el keystore**
```powershell
keytool -genkeypair ^
-alias ibkr-cert ^
-keyalg RSA ^
-keysize 2048 ^
-keystore "ibkrkeystore.jks" ^
-validity 365 ^
-storepass gwilmer ^
-dname "CN=localhost, OU=IBKR, O=InversionsWildaga, L=NY, S=NY, C=US"
```

**Exportar el certificado público (opcional)**
```powershell
keytool -exportcert ^
-alias ibkr-cert ^
-file ibkr-cert.cer ^
-keystore "ibkrkeystore.jks" ^
-storepass gwilmer
```

---

## ⚙️ 2️⃣ Configuración de `conf.yaml`

```yaml
authDelay: 3000
ccp: false
cors:
  origin.allowed: '*'
  allowCredentials: false

ip2loc: US
ips:
  allow: [192.*, 131.216.*, 127.0.0.1]
  deny: [212.90.324.10]

listenPort: 5000
listenSsl: true

sslCert: ibkrkeystore.jks
sslPwd: gwilmer

proxyRemoteHost: "https://api.ibkr.com"
proxyRemoteSsl: true

ssoPing: 5
svcEnvironment: v1
tst: false
twsBaseURL: /tws.proxy

webApps:
  - {cache: true, index: index.html, listing: false, name: demo, proxy: ''}
```

---

## 🧰 3️⃣ Limpieza y reinicio

1. Borrar caché de Vert.x  
   ```powershell
   rmdir /S /Q "C:\Users\InversionesWildaga\Documents\MyPython\.vertx"
   ```
2. Ejecutar el Gateway con Java 21  
   ```bat
   "C:\Program Files\Eclipse Adoptium\jdk-21\bin\java.exe" -jar "C:\Users\InversionesWildaga\Documents\MyPython\ResourcesIbrks\dist\ibgroup.web.core.iblink.router.clientportal.gw.jar"
   ```
3. Verificar log de inicio sin errores SSL.

---

## 🧪 4️⃣ Prueba de conexión local

**Desde navegador:** [https://localhost:5000](https://localhost:5000)

**Desde Python:**
```python
import requests
r = requests.get("https://localhost:5000/v1/api/iserver/accounts", verify=False)
print(r.status_code, r.text)
```

---

## ✅ 5️⃣ Resultado esperado

| Prueba | Estado |
|---------|---------|
| Gateway inicia con Java 21 | ✅ |
| HTTPS local operativo (con ibkrkeystore.jks) | ✅ |
| Conexión remota a IBKR estable | ✅ |
| Error certificate_unknown eliminado | ✅ |

---

## 🧠 Notas finales

- El certificado `ibkrkeystore.jks` es solo para entorno local.
- IBKR no acepta certificados autofirmados en conexiones externas.
- Java 21 incluye certificados raíz actualizados.
- Revisar antivirus o proxies que inspeccionen HTTPS si reaparece el error.
