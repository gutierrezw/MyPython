import os
import logging
from fastmcp import FastMCP
from github import Github, GithubException

logging.basicConfig(level=logging.WARNING)
_logger = logging.getLogger("GitHubMCP")

REPO_NAME = "gutierrezw/MyPython"
BRANCH = "docs"
DOC_PATH = "AppOO/Doc"
MEMORY_PATH = "AppOO/Doc/memory"
BACKLOG_PATH = "AppOO/BACKLOG.md"
ALLOWED_EXT = {".md", ".txt", ".json"}

_gh = None
_repo = None


def _get_repo():
    global _gh, _repo
    if _repo is not None:
        return _repo
    token = os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_PERSONAL_ACCESS_TOKEN no definida en variables de entorno")
    _gh = Github(token)
    _repo = _gh.get_repo(REPO_NAME)
    return _repo


def _upsert_file(path: str, content: str, message: str) -> dict:
    repo = _get_repo()
    try:
        existing = repo.get_contents(path, ref=BRANCH)
        result = repo.update_file(path, message, content, existing.sha, branch=BRANCH)
        return {"ok": True, "sha": result["commit"].sha, "url": result["commit"].html_url}
    except GithubException as e:
        if e.status == 404:
            result = repo.create_file(path, message, content, branch=BRANCH)
            return {"ok": True, "sha": result["commit"].sha, "url": result["commit"].html_url}
        raise


mcp = FastMCP("appoo-github")


@mcp.tool()
def push_doc(filename: str, content: str, message: str = "") -> dict:
    """Crea o actualiza un archivo en AppOO/Doc/ de la rama docs."""
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXT:
        return {"ok": False, "error": f"extensión no permitida: {ext}"}
    path = f"{DOC_PATH}/{filename}"
    msg = message or f"docs: update {filename}"
    try:
        return _upsert_file(path, content, msg)
    except Exception as e:
        _logger.error(f"push_doc({filename}): {e}")
        return {"ok": False, "error": str(e)}


@mcp.tool()
def push_memory(filename: str, content: str, message: str = "") -> dict:
    """Crea o actualiza un archivo en AppOO/Doc/memory/ de la rama docs."""
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXT:
        return {"ok": False, "error": f"extensión no permitida: {ext}"}
    path = f"{MEMORY_PATH}/{filename}"
    msg = message or f"docs: update memory/{filename}"
    try:
        return _upsert_file(path, content, msg)
    except Exception as e:
        _logger.error(f"push_memory({filename}): {e}")
        return {"ok": False, "error": str(e)}


@mcp.tool()
def read_doc(filename: str) -> dict:
    """Lee el contenido de un archivo en AppOO/Doc/."""
    path = f"{DOC_PATH}/{filename}"
    try:
        repo = _get_repo()
        file = repo.get_contents(path, ref=BRANCH)
        return {"ok": True, "content": file.decoded_content.decode("utf-8"), "sha": file.sha}
    except GithubException as e:
        if e.status == 404:
            return {"ok": False, "error": "archivo no encontrado"}
        _logger.error(f"read_doc({filename}): {e}")
        return {"ok": False, "error": str(e)}
    except Exception as e:
        _logger.error(f"read_doc({filename}): {e}")
        return {"ok": False, "error": str(e)}


@mcp.tool()
def list_docs(subdir: str = "") -> dict:
    """Lista archivos en AppOO/Doc/ o en un subdirectorio (ej: 'memory')."""
    path = f"{DOC_PATH}/{subdir}".rstrip("/") if subdir else DOC_PATH
    try:
        repo = _get_repo()
        contents = repo.get_contents(path, ref=BRANCH)
        files = [c.name for c in contents if c.type == "file"]
        return {"ok": True, "files": files}
    except GithubException as e:
        if e.status == 404:
            return {"ok": False, "error": f"directorio no encontrado: {path}"}
        _logger.error(f"list_docs({subdir}): {e}")
        return {"ok": False, "error": str(e)}
    except Exception as e:
        _logger.error(f"list_docs({subdir}): {e}")
        return {"ok": False, "error": str(e)}


@mcp.tool()
def update_backlog(content: str, message: str = "") -> dict:
    """Reemplaza el contenido completo de AppOO/BACKLOG.md en rama docs."""
    msg = message or "docs: update BACKLOG.md"
    try:
        return _upsert_file(BACKLOG_PATH, content, msg)
    except Exception as e:
        _logger.error(f"update_backlog: {e}")
        return {"ok": False, "error": str(e)}


if __name__ == "__main__":
    mcp.run()
