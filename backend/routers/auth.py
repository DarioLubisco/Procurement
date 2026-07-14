"""
Router: /api/auth
Endpoints: POST /login, GET /me, POST /logout-log
Dep: get_current_user — inyectable en cualquier ruta protegida
"""
import os
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from jose import JWTError, jwt
import bcrypt

from database import get_db_connection

# ─── Config ───────────────────────────────────────────────────────────────────
SECRET_KEY = os.getenv("SYNAPSE_JWT_SECRET", "synapse-super-secret-key-change-in-prod-2024")
ALGORITHM = "HS256"
TOKEN_EXPIRE_DAYS = 7

bearer_scheme = HTTPBearer(auto_error=False)

router = APIRouter(prefix="/api/auth", tags=["Auth"])


# ─── Models ───────────────────────────────────────────────────────────────────
class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class UserOut(BaseModel):
    id: int
    username: str
    nombre: str
    email: Optional[str]
    permissions: dict  # {"chat": {"r": True, "w": True}, "caja": {...}, ...}


# ─── Helpers ──────────────────────────────────────────────────────────────────
def _get_user_with_permissions(username: str) -> Optional[dict]:
    """Carga usuario + permisos desde SQL Server."""
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()

            # Usuario
            cur.execute(
                "SELECT id, username, nombre, password_hash, email, activo "
                "FROM dbo.synapse_usuarios WHERE username = ?",
                username
            )
            row = cur.fetchone()
            if not row:
                return None

            user_id, uname, nombre, pw_hash, email, activo = row

            if not activo:
                return None

            # Permisos
            cur.execute(
                "SELECT modulo, puede_leer, puede_escribir "
                "FROM dbo.synapse_permisos WHERE usuario_id = ?",
                user_id
            )
            perms = {}
            for modulo, r, w in cur.fetchall():
                perms[modulo] = {"r": bool(r), "w": bool(w)}

            return {
                "id": user_id,
                "username": uname,
                "nombre": nombre,
                "password_hash": pw_hash,
                "email": email,
                "permissions": perms,
            }
    except Exception as e:
        print(f"[Auth] DB Error: {e}")
        return None


def _create_token(user: dict) -> str:
    expire = datetime.utcnow() + timedelta(days=TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": user["username"],
        "uid": user["id"],
        "nombre": user["nombre"],
        "email": user.get("email"),
        "permissions": user["permissions"],
        "exp": expire,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def _log_actividad(usuario_id: int, username: str, accion: str,
                   modulo: str = None, detalle: str = None, ip: str = None):
    """Registra en synapse_log_actividad (fire-and-forget, no falla la request)."""
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO dbo.synapse_log_actividad
                   (usuario_id, username, accion, modulo, detalle, ip)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                usuario_id, username, accion, modulo, detalle, ip
            )
            conn.commit()
    except Exception as e:
        print(f"[Auth] Log error (non-fatal): {e}")


# ─── Dependency: get_current_user ─────────────────────────────────────────────
async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)
) -> dict:
    """
    Inyectable en cualquier endpoint que requiera autenticación.
    Uso: user = Depends(get_current_user)
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        return {
            "id": payload["uid"],
            "username": payload["sub"],
            "nombre": payload["nombre"],
            "email": payload.get("email"),
            "permissions": payload.get("permissions", {}),
        }
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_permission(modulo: str, write: bool = False):
    """
    Factory de dependencia para verificar permisos granulares.
    Uso: Depends(require_permission("caja", write=True))
    """
    async def _check(user: dict = Depends(get_current_user)):
        perms = user.get("permissions", {})
        mod_perm = perms.get(modulo, {})
        if write and not mod_perm.get("w"):
            raise HTTPException(status_code=403, detail=f"Sin permiso de escritura en '{modulo}'")
        if not mod_perm.get("r"):
            raise HTTPException(status_code=403, detail=f"Sin acceso al módulo '{modulo}'")
        return user
    return _check


# ─── Endpoints ────────────────────────────────────────────────────────────────
@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, request: Request):
    user = _get_user_with_permissions(body.username)

    if not user or not bcrypt.checkpw(body.password.encode('utf-8'), user["password_hash"].encode('utf-8')):
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")

    token = _create_token(user)

    # Actualizar último login
    try:
        with get_db_connection() as conn:
            conn.cursor().execute(
                "UPDATE dbo.synapse_usuarios SET ultimo_login = GETDATE() WHERE id = ?",
                user["id"]
            )
            conn.commit()
    except Exception:
        pass

    # Log de actividad
    client_ip = request.client.host if request.client else None
    _log_actividad(user["id"], user["username"], "LOGIN", ip=client_ip)

    return TokenResponse(
        access_token=token,
        user={
            "id": user["id"],
            "username": user["username"],
            "nombre": user["nombre"],
            "email": user.get("email"),
            "permissions": user["permissions"],
        }
    )


@router.get("/me", response_model=UserOut)
async def get_me(current_user: dict = Depends(get_current_user)):
    """Retorna el perfil del usuario autenticado (desde el token, sin tocar DB)."""
    return UserOut(**current_user)


@router.post("/log-action")
async def log_action(
    body: dict,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Frontend puede registrar acciones de usuario (navegación, clicks clave)."""
    _log_actividad(
        usuario_id=current_user["id"],
        username=current_user["username"],
        accion=body.get("accion", "ACCION_DESCONOCIDA"),
        modulo=body.get("modulo"),
        detalle=body.get("detalle"),
        ip=request.client.host if request.client else None,
    )
    return {"status": "logged"}
