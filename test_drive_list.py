import os
import subprocess
import tempfile
import json
from app import settings

DRIVE_URL = os.getenv("DRIVE_URL", "16paTbHeCuQw9YWH-ldniMJbxzuQvjBLD")

def list_drive():
    with tempfile.TemporaryDirectory() as stage:
        # Usamos gdown para descargar, PERO sin redirigir stdout al log.
        # Espera, gdown puede descargar una carpeta vacía si sabemos la estructura?
        pass

print(DRIVE_URL)
