from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from sqlalchemy.orm import Session
import os
from dotenv import load_dotenv
import logging

from app.database.modelsDB import User
from app.utils.database_dependencies import get_db

load_dotenv()
logger = logging.getLogger("app.auth")

# Configuración de JWT
SECRET_KEY = os.getenv("SECRET_KEY", "tu_clave_secreta_por_defecto")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Crea un token JWT usando PyJWT.
    
    Args:
        data: Datos a codificar en el token
        expires_delta: Tiempo de expiración opcional
        
    Returns:
        str: Token JWT codificado
    """
    try:
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

        # Usar timestamp para la expiración
        to_encode.update({"exp": expire})
        
        encoded_jwt = jwt.encode(
            to_encode,
            SECRET_KEY,
            algorithm=ALGORITHM
        )
        
        logger.debug(f"Token creado con expiración: {expire}")
        return encoded_jwt
        
    except Exception as e:
        logger.error(f"Error creando token: {str(e)}")
        raise

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """
    Valida el token JWT y retorna el usuario actual.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decodificar el token con PyJWT
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"verify_exp": True}  # Verificar expiración automáticamente
        )
        
        username: str = payload.get("sub")
        if username is None:
            logger.warning("Token no contiene campo 'sub'")
            raise credentials_exception
            
    except jwt.ExpiredSignatureError:
        logger.error("Token expirado")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expirado"
        )
    except jwt.InvalidTokenError as e:
        logger.error(f"Token inválido: {str(e)}")
        raise credentials_exception
    except Exception as e:
        logger.error(f"Error inesperado validando token: {str(e)}")
        raise credentials_exception

    # Buscar usuario en la base de datos
    user = db.query(User).filter(User.name == username).first()
    if user is None:
        logger.warning(f"Usuario no encontrado: {username}")
        raise credentials_exception
        
    return user

async def validate_ws_token(token: str, db: Session) -> Optional[User]:
    """
    Valida un token para conexiones WebSocket.
    """
    try:
        # Eliminar el prefijo "Bearer" si existe
        if token.startswith("Bearer "):
            token = token.split(" ")[1]
            
        # Decodificar el token
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"verify_exp": True}
        )
        
        username: str = payload.get("sub")
        if not username:
            return None
            
        # Verificar usuario en la base de datos
        user = db.query(User).filter(User.name == username).first()
        return user
        
    except jwt.ExpiredSignatureError:
        logger.error("Token WS expirado")
        return None
    except jwt.InvalidTokenError as e:
        logger.error(f"Token WS inválido: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Error validando token WebSocket: {str(e)}")
        return None