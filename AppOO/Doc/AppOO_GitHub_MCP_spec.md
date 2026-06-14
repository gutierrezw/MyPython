# AppOO GitHub MCP — Especificación Técnica
**AppOO · 2026-06**

---

## 1. Propósito

Servidor MCP local que permite a Claude Code interactuar con el repositorio
`gutierrezw/MyPython` (rama `docs`) sin especificar repo/rama en cada comando.
Encapsula las convenciones de AppOO: rutas, rama, y estructura de directorios.

---

## 2. Contexto y decisiones de diseño

### 2.1 Por qué un MCP propio y no el oficial `@github/mcp-server`

| Aspecto | Oficial | AppOO MCP |
|---|---|---|
| Requiere repo/rama en cada llamada | Sí | No — hardcodeado en config |
| Conoce estructura AppOO/Doc/ | No | Sí |
| `push_doc` → siempre rama `docs` | No | Sí |
| `push_memory` → siempre `Doc/memory/` | No | Sí |
| Lógica de convenciones AppOO | No | Sí |

### 2.2 Relación con Class_BrowserBridge.py

AppOO ya tiene un servidor HTTP local en puerto 5050 (`Class_BrowserBridge.py`).
El MCP de GitHub sigue el **mismo patrón arquitectónico** pero corre como
proceso separado para:
- No mezclar protocolos (HTTP simple vs MCP stdio)
- Aislamiento de fallos
- Control independiente (start/stop/restart)

### 2.3 Transporte

**stdio** — el más simple para uso local con Claude Code.
Claude Code lanza el proceso como hijo y se comunica por stdin/stdout.
No requiere puerto, no requiere firewall, no requiere servidor HTTP.

---

## 3. Stack técnico

| Componente | Tecnología |
|---|---|
| Lenguaje | Python 3.11+ |
| Framework MCP | `fastmcp` |
| Cliente GitHub | `PyGithub` |
| Autenticación | `GITHUB_PERSONAL_ACCESS_TOKEN` (variable de entorno Windows — herencia de proceso) |
| Transporte | stdio |
| Registro en Claude Code | `settings.json` → bloque `mcpServers` |

---

## 4. Configuración

### 4.1 Constantes hardcodeadas (convenciones AppOO)

```python
REPO_NAME   = "gutierrezw/MyPython"
BRANCH      = "docs"
DOC_PATH    = "AppOO/Doc"
MEMORY_PATH = "AppOO/Doc/memory"
BACKLOG_PATH = "AppOO/BACKLOG.md"
```

### 4.2 Registro en settings.json de Claude Code

```jsonc
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@github/mcp-server"]
    },
    "appoo-github": {
      "command": "python",
      "args": ["C:\\Users\\InversionesWildaga\\Documents\\MyPython\\AppOO\\Modulos_python\\Class_GitHubMCP.py"]
    }
  }
}
```

El token llega por herencia de proceso desde las variables de entorno de Windows.
No se especifica en el config (mismo patrón que el servidor oficial).

---

## 5. Herramientas expuestas (Tools)

### 5.1 `push_doc`

Crea o actualiza un archivo en `AppOO/Doc/`.

```
Parámetros:
  filename  : str   — nombre del archivo (ej: "EcoScanner_Roadmap_v1.md")
  content   : str   — contenido completo del archivo
  message   : str   — mensaje de commit (opcional, default: "docs: update {filename}")

Retorna:
  { "ok": true, "sha": "...", "url": "..." }
```

**Restricción:** solo permite extensiones `.md`, `.txt`, `.json`. Para `.docx` o `.pdf`
usar `push_binary` (fase 2).

---

### 5.2 `push_memory`

Crea o actualiza un archivo en `AppOO/Doc/memory/`.

```
Parámetros:
  filename  : str   — nombre del archivo (ej: "project_ecoscanner.md")
  content   : str   — contenido completo
  message   : str   — mensaje de commit (opcional)

Retorna:
  { "ok": true, "sha": "...", "url": "..." }
```

---

### 5.3 `read_doc`

Lee el contenido de un archivo en `AppOO/Doc/`.

```
Parámetros:
  filename  : str   — nombre del archivo

Retorna:
  { "ok": true, "content": "...", "sha": "..." }
```

---

### 5.4 `list_docs`

Lista archivos en `AppOO/Doc/` o en un subdirectorio.

```
Parámetros:
  subdir    : str   — subdirectorio opcional (ej: "memory", default: "")

Retorna:
  { "ok": true, "files": ["archivo1.md", "archivo2.md", ...] }
```

---

### 5.5 `update_backlog`

Reemplaza el contenido completo de `AppOO/BACKLOG.md`.

```
Parámetros:
  content   : str   — nuevo contenido del backlog
  message   : str   — mensaje de commit (opcional)

Retorna:
  { "ok": true, "sha": "...", "url": "..." }
```

---

## 6. Arquitectura del módulo

```
AppOO/
└── Modulos_python/
    └── Class_GitHubMCP.py      ← servidor MCP (este módulo)
```

### 6.1 Estructura interna de Class_GitHubMCP.py

```python
# ── Imports ──────────────────────────────────────────────
from fastmcp import FastMCP
from github import Github, GithubException
import os, base64, logging

# ── Constantes AppOO ─────────────────────────────────────
REPO_NAME    = "gutierrezw/MyPython"
BRANCH       = "docs"
DOC_PATH     = "AppOO/Doc"
MEMORY_PATH  = "AppOO/Doc/memory"
BACKLOG_PATH = "AppOO/BACKLOG.md"
ALLOWED_EXT  = {".md", ".txt", ".json"}

# ── Cliente GitHub ────────────────────────────────────────
_gh   = None   # Github instance
_repo = None   # Repository instance

def _get_repo():
    """Inicializa cliente GitHub con lazy init."""
    ...

# ── Servidor MCP ─────────────────────────────────────────
mcp = FastMCP("appoo-github")

@mcp.tool()
def push_doc(filename: str, content: str, message: str = "") -> dict:
    ...

@mcp.tool()
def push_memory(filename: str, content: str, message: str = "") -> dict:
    ...

@mcp.tool()
def read_doc(filename: str) -> dict:
    ...

@mcp.tool()
def list_docs(subdir: str = "") -> dict:
    ...

@mcp.tool()
def update_backlog(content: str, message: str = "") -> dict:
    ...

# ── Entry point ───────────────────────────────────────────
if __name__ == "__main__":
    mcp.run()   # stdio transport por defecto
```

---

## 7. Control del proceso (patrón BrowserBridge)

A diferencia de `Class_BrowserBridge.py`, este módulo **no necesita**
`start_/stop_/is_running()` porque Claude Code gestiona el ciclo de vida
del proceso hijo automáticamente vía stdio.

Claude Code lanza el proceso al conectarse y lo mata al desconectarse.
No corre como daemon permanente de AppOO.

---

## 8. Manejo de errores

| Caso | Comportamiento |
|---|---|
| Token no encontrado | Error claro: "GITHUB_PERSONAL_ACCESS_TOKEN no definida" |
| Archivo no existe en `read_doc` | `{ "ok": false, "error": "archivo no encontrado" }` |
| Extensión no permitida en `push_doc` | `{ "ok": false, "error": "extensión no permitida: .docx" }` |
| Error de red / GitHub API | Log + `{ "ok": false, "error": "..." }` |
| Repo o rama no existe | Error descriptivo con nombre de repo y rama |

---

## 9. Dependencias

```
fastmcp>=0.1.0
PyGithub>=2.1.1
```

Instalación:
```bash
pip install fastmcp PyGithub --break-system-packages
```

---

## 10. Roadmap

| Prioridad | Tarea |
|---|---|
| 1 — Inmediato | Implementar las 5 herramientas core |
| 2 — Siguiente | `push_binary` para `.docx` y `.pdf` (base64) |
| 3 — Futuro | `search_docs` — búsqueda por contenido en `AppOO/Doc/` |
| 4 — Futuro | Integración con `AppOO/Doc/memory/project_proxima_sesion.md` como contexto automático |

---

## 11. Instrucciones para Claude Code

Al implementar este módulo, Claude Code debe:

1. Leer esta spec completa antes de escribir código
2. Leer `AppOO/Doc/memory/MEMORY.md` para contexto del proyecto
3. Instalar dependencias: `pip install fastmcp PyGithub --break-system-packages`
4. Crear `AppOO/Modulos_python/Class_GitHubMCP.py`
5. Probar con: `python Class_GitHubMCP.py` — debe iniciar sin errores
6. Registrar en `settings.json` de Claude Code
7. Hacer commit de la spec y del módulo a rama `docs`

**Convención de commits:**
```
feat: agregar Class_GitHubMCP.py — servidor MCP para GitHub AppOO
docs: agregar AppOO_GitHub_MCP_spec.md
```
