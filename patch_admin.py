import sys

with open("app/main.py", "r") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if "def admin_sync_status" in line:
        insert_idx = i - 1
        break

codigo_nuevo = """
@app.post("/admin_check_drive")
async def admin_check_drive(clave: str = ""):
    \"\"\"Revisa qué archivos hay nuevos en Drive comparando con lo indexado.\"\"\"
    if not _admin_valida(clave):
        raise HTTPException(status_code=403, detail="Acceso denegado")
    
    script_path = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'gdown_sync.sh')
    env = os.environ.copy()
    env["SKIP_INGESTION"] = "1"
    env["LOG_FILE"] = "/tmp/gdown_check.log"
    
    # 1. Descargar archivos a data/ sin indexar
    proc = subprocess.run(["bash", script_path], env=env, capture_output=True, text=True)
    if proc.returncode != 0:
        return {"error": "Falló la revisión de Drive", "detalle": proc.stderr or proc.stdout}
    
    # 2. Leer qué hay en data/
    data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    archivos_fisicos = []
    for root, dirs, files in os.walk(data_dir):
        # Ignorar carpeta de staging si quedara alguna
        if ".gdown_stage" in root: continue
        for f in files:
            if f.endswith(('.pdf', '.md', '.csv')):
                ruta_relativa = os.path.relpath(os.path.join(root, f), data_dir)
                archivos_fisicos.append(ruta_relativa)
                
    # 3. Leer qué hay en ChromaDB
    from app.database import get_collection
    try:
        coll = get_collection()
        docs = coll.get(include=['metadatas'])
        archivos_indexados = set(m.get('fuente') for m in docs.get('metadatas', []) if m and 'fuente' in m)
    except Exception as e:
        archivos_indexados = set()

    # 4. Comparar
    nuevos = [f for f in archivos_fisicos if f not in archivos_indexados]
    
    return {
        "ok": True,
        "en_drive": len(archivos_fisicos),
        "ya_indexados": len(archivos_indexados),
        "nuevos_count": len(nuevos),
        "nuevos": nuevos
    }

"""

lines.insert(insert_idx, codigo_nuevo)

with open("app/main.py", "w") as f:
    f.writelines(lines)
