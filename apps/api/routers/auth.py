"""
Router de autenticación — POST /api/v1/auth/token
Sistema mono-usuario: el token se obtiene con la APP_PASSWORD del .env.
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from core.responses import ok
from core.security import create_access_token, verify_app_password

router = APIRouter()


class LoginRequest(BaseModel):
    password: str


@router.post("/token")
async def login(body: LoginRequest) -> dict:
    """
    Intercambia la contraseña de la app por un JWT Bearer token.
    El token expira según ACCESS_TOKEN_EXPIRE_MINUTES.
    """
    if not verify_app_password(body.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Contraseña incorrecta",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token()
    return ok(
        data={"access_token": token, "token_type": "bearer"},
        meta={"note": "Incluye el token en el header: Authorization: Bearer <token>"},
    )
