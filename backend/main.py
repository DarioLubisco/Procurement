import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Inicializar nuestra API Principal (Synapse Backend)
app = FastAPI(title="Synapse Business Suite API", version="2.0.0")

# Permisos para que el Portal Web Frontend (Nginx) pueda llamar a nuestro Backend API
# Incluso si corren bajo diferentes dominios o puertos en la red (CORS).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from database import request_db_connections

@app.middleware("http")
async def db_cleanup_middleware(request, call_next):
    token = request_db_connections.set([])
    try:
        response = await call_next(request)
        return response
    finally:
        conns = request_db_connections.get()
        if conns is not None:
            for conn in conns:
                try:
                    conn.close()
                except Exception:
                    pass
        request_db_connections.reset(token)

@app.middleware("http")
async def log_requests(request, call_next):
    # Log incoming requests safely across environments (Windows/Linux)
    log_file = "requests_log.txt" if not os.path.exists("c:/") else "c:/source/Synapse/scratch/requests_log.txt"
    try:
        with open(log_file, "a") as f:
            f.write(f"REQ: {request.method} {request.url}\n")
    except Exception:
        pass # Ignore log fail in prod to avoid crashing API
        
    try:
        response = await call_next(request)
        try:
            with open(log_file, "a") as f:
                f.write(f"RES: {response.status_code}\n")
        except Exception:
            pass
        return response
    except Exception as e:
        import traceback
        traceback.print_exc()
        try:
            with open(log_file, "a") as f:
                f.write(f"ERR: {str(e)}\n")
        except Exception:
            pass
        raise
@app.get("/api/health")
async def health_check():
    return {"status": "ok", "message": "Synapse API running inside Docker"}

# Aquí conectaremos los Enrutadores (Routers)
from routers.auth import router as auth_router
from routers.caja import router as caja_router
from routers.cxp import router as cxp_router
from routers.pedidos import router as pedidos_router
from routers.inventario import router as inventario_router
from routers.n8n_webhook import router as n8n_webhook_router
from routers.proveedores_b2b import router as proveedores_b2b_router
from routers.rotacion_grupal import router as rotacion_grupal_router

from strawberry.fastapi import GraphQLRouter
from graphql_api.schema import schema

graphql_app = GraphQLRouter(schema)

app.include_router(auth_router)
app.include_router(caja_router)
app.include_router(cxp_router)
app.include_router(pedidos_router)
from routers.generar_sencillo import router as generar_sencillo_router
app.include_router(generar_sencillo_router)
from routers.validar_minimos import router as validar_minimos_router
app.include_router(validar_minimos_router)
from routers.guardar_borrador import router as guardar_borrador_router
app.include_router(guardar_borrador_router)
from routers.bandeja import router as bandeja_router
app.include_router(bandeja_router)
from routers.pedido_moneda import router as pedido_moneda_router
app.include_router(pedido_moneda_router)
from routers.pedido_presets import router as pedido_presets_router
app.include_router(pedido_presets_router)
app.include_router(inventario_router)
app.include_router(n8n_webhook_router)
app.include_router(proveedores_b2b_router)
app.include_router(rotacion_grupal_router)

# Mount GraphQL endpoint
app.include_router(graphql_app, prefix="/graphql")

# app.include_router(pedidos_router)

from fastapi.staticfiles import StaticFiles
import os
frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.isdir(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

@app.get("/debug/paths")
async def debug_paths():
    return {"cwd": os.getcwd(), "file": __file__, "frontend_dir": frontend_dir}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
