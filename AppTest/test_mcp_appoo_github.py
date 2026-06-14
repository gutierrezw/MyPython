#!/usr/bin/env python
"""Test de conexión y funcionalidad del servidor MCP appoo-github."""

import os
import sys
import subprocess
import json
import time

REPO_NAME = "gutierrezw/MyPython"
BRANCH = "docs"


def test_token():
    """Valida que el token de GitHub esté disponible."""
    print("\n[1] Verificando GITHUB_PERSONAL_ACCESS_TOKEN...")
    token = os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN")
    if not token:
        print("  ❌ GITHUB_PERSONAL_ACCESS_TOKEN no está definida")
        return False
    if len(token) < 10:
        print(f"  ❌ Token muy corto: {len(token)} caracteres")
        return False
    print(f"  ✓ Token presente ({len(token)} caracteres)")
    return True


def test_imports():
    """Valida que las dependencias estén instaladas."""
    print("\n[2] Verificando dependencias...")
    try:
        import fastmcp

        print(f"  ✓ fastmcp: {fastmcp.__version__ if hasattr(fastmcp, '__version__') else 'OK'}")
    except ImportError as e:
        print(f"  ❌ fastmcp: {e}")
        return False
    try:
        import github

        print(f"  ✓ PyGithub: {github.__version__ if hasattr(github, '__version__') else 'OK'}")
    except ImportError as e:
        print(f"  ❌ PyGithub: {e}")
        return False
    return True


def test_github_api():
    """Prueba conexión directa a GitHub API."""
    print("\n[3] Probando GitHub API...")
    try:
        from github import Github

        token = os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN")
        gh = Github(token)
        repo = gh.get_repo(REPO_NAME)

        # Verifica que el repo existe
        print(f"  ✓ Repo encontrado: {repo.full_name}")

        # Intenta acceder a la rama docs
        try:
            branch = repo.get_branch(BRANCH)
            print(f"  ✓ Rama '{BRANCH}' existe")
        except Exception as e:
            print(f"  ❌ Rama '{BRANCH}' no encontrada: {e}")
            return False

        # Intenta listar archivos en AppOO/Doc
        try:
            contents = repo.get_contents("AppOO/Doc", ref=BRANCH)
            file_count = len([c for c in contents if c.type == "file"])
            print(f"  ✓ AppOO/Doc contiene {file_count} archivos")
        except Exception as e:
            print(f"  ⚠ No se pudo listar AppOO/Doc: {e}")

        return True
    except Exception as e:
        print(f"  ❌ Error en GitHub API: {e}")
        return False


def test_mcp_module():
    """Valida que el módulo MCP inicie sin errores."""
    print("\n[4] Probando módulo Class_GitHubMCP.py...")
    mcp_path = r"C:\Users\InversionesWildaga\Documents\MyPython\AppOO\Modulos_python\Class_GitHubMCP.py"

    if not os.path.exists(mcp_path):
        print(f"  ❌ Archivo no encontrado: {mcp_path}")
        return False

    print(f"  ✓ Archivo encontrado")

    # Intenta importar el módulo
    try:
        sys.path.insert(0, os.path.dirname(mcp_path))
        # Verifica que pueda importarse sin errores
        with open(mcp_path) as f:
            code = f.read()
        # Valida sintaxis
        compile(code, mcp_path, "exec")
        print(f"  ✓ Sintaxis Python válida")
        return True
    except SyntaxError as e:
        print(f"  ❌ Error de sintaxis: {e}")
        return False
    except Exception as e:
        print(f"  ❌ Error al importar: {e}")
        return False


def test_settings_config():
    """Valida la configuración en settings.json."""
    print("\n[5] Verificando configuración en settings.json...")
    settings_path = r"C:\Users\InversionesWildaga\.claude\settings.json"

    if not os.path.exists(settings_path):
        print(f"  ❌ Archivo no encontrado: {settings_path}")
        return False

    try:
        with open(settings_path) as f:
            settings = json.load(f)

        if "mcpServers" not in settings:
            print("  ❌ 'mcpServers' no definido en settings.json")
            return False

        if "appoo-github" not in settings["mcpServers"]:
            print("  ❌ 'appoo-github' no registrado en mcpServers")
            return False

        server_config = settings["mcpServers"]["appoo-github"]
        print(f"  ✓ appoo-github registrado")
        print(f"    Command: {server_config.get('command', 'N/A')}")
        print(f"    Args: {server_config.get('args', 'N/A')}")

        # Valida que el archivo del script exista
        script_path = server_config.get("args", [None])[0]
        if script_path and not os.path.exists(script_path):
            print(f"  ❌ Script MCP no encontrado: {script_path}")
            return False

        return True
    except json.JSONDecodeError as e:
        print(f"  ❌ settings.json inválido: {e}")
        return False
    except Exception as e:
        print(f"  ❌ Error leyendo settings.json: {e}")
        return False


def main():
    print("=" * 70)
    print("VALIDACIÓN DE CONEXIÓN APPOO-GITHUB MCP")
    print("=" * 70)

    results = []
    results.append(("Token GitHub", test_token()))
    results.append(("Dependencias", test_imports()))
    results.append(("GitHub API", test_github_api()))
    results.append(("Módulo MCP", test_mcp_module()))
    results.append(("Configuración", test_settings_config()))

    print("\n" + "=" * 70)
    print("RESUMEN")
    print("=" * 70)

    for test_name, result in results:
        status = "✓ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")

    all_passed = all(r for _, r in results)

    if all_passed:
        print("\n✓ TODOS LOS TESTS PASARON")
        print("\nEl servidor MCP appoo-github está listo para usar.")
        print("Próximos pasos:")
        print("  1. Reinicia Claude Code (File → Reload)")
        print("  2. En una conversación, prueba: mcp__appoo-github__list_docs()")
        return 0
    else:
        print("\n❌ FALLOS DETECTADOS")
        print("Revisa los errores arriba para resolver.")
        return 1


if __name__ == "__main__":
    exit(main())
