import os
import sys

# En PyInstaller: fija el cwd al directorio del exe para que tmp/ resuelva siempre igual
if getattr(sys, "frozen", False):
    os.chdir(os.path.dirname(sys.executable))

# Crea tmp/ si no existe (primera ejecución en máquina nueva)
os.makedirs("tmp", exist_ok=True)

sys.argv = [sys.argv[0], "--profile", "hijo"]

from DashMainV9_ia import DashMain

if __name__ == "__main__":
    app = DashMain()
    app.run()
