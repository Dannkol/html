from fastapi import APIRouter, Depends, HTTPException, status
from app.utils.JWT_Auth import get_current_user
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = get_current_user(token)
        # Aquí puedes agregar más lógica para verificar el usuario, como buscar en la base de datos
        return payload
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_protected_router(router: APIRouter) -> APIRouter:
    for route in router.routes:
        route.dependencies.append(Depends(get_current_user))
    return router