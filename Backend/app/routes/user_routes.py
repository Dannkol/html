import logging
import os 
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.utils.crypt_dependencies import crypt_password, crypt_verify_password
from app.database.modelsDB import User
from app.utils.database_dependencies import get_transactional_db, get_db
from app.models.UserValidator import UserCreate, LoginData, Token
from app.utils.JWT_Auth import create_access_token, get_current_user
from app.models.ErrorsValidator import DatabaseError

logger = logging.getLogger("app.esp_routes")

user_routers = APIRouter()

@user_routers.post("/users/", 
                   response_model=dict,
                   responses={
                       200: {
                           "description": "Usuario creado exitosamente",
                            "content": {
                                "application/json": {
                                    "status": "success",
                                    "message": "Usuario creado exitosamente",
                                    "user_id": 2
                                }
                            }
                        },
                       500: {
                           "description": "Error interno en el servidor",
                            "content": {
                                "application/json": {
                                    "status": "error",
                                    "message": "Error interno en el servidor"
                                }
                            }
                        }
                   })
async def create_user(user: UserCreate, db: Session = Depends(get_transactional_db)):
    """
    Registrar Nuevo Usuario.
    
    Args:
        user: UserCreate,
        db: Session, la sesión de la base de datos
    
    Returns:
        Dict con la información del registro
    
    Raises:
        HTTPException: Si la peticion tiene error o hay errores en la base de datos
    """
    try:
        logger.info(f"Inicio de solicitud de crear nuevo usuario, name: {user.name}, location: {user.location}, longitude: {user.longitud}, latitude: {user.latitud}")
        # Verificar si el usuario ya existe
        try:
            existing_user = db.query(User).filter(User.name == user.name).first()
        except SQLAlchemyError as db_error:
            raise DatabaseError("Error al buscar el usuario: %s" % db_error)
        
        if existing_user:
            logger.warning(f"Intento de registro de un usuario existente name: {user.name}")
            raise HTTPException(
                status_code=400,
                detail="El nombre de usuario ya está registrado"
            )

        # Crear el nuevo usuario
        hashed_password = crypt_password(user.password)
        logger.info(f"Hasheando clave para: {user.name}")
        
        try:
        
            db_user = User(
                name=user.name,
                password=hashed_password,
                location=user.location,
                longitud=user.longitud,
                latitud=user.latitud
            )

            # Guardar en la base de datos
            db.add(db_user)
            db.commit()
            db.refresh(db_user)
            logger.info(f"Nuevo usuario creado exitosamente: {user.name}")
        except SQLAlchemyError as db_error:
             # Extraer información relevante de `db_user`
            user_info = f"id={db_user.id}, name={db_user.name}" if db_user else "N/A"
            # Lanzar una excepción personalizada
            raise DatabaseError(
                f"Error al guardar el usuario ({user_info}). Detalles del error:\n{db_error}"
            ) from db_error
                
        return {
            "message": "Usuario creado exitosamente",
            "user_id": db_user.id
        }

    except DatabaseError as db_error:
        logger.error(f"Error al crear nuevo usuario: {str(db_error)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "detail": "Error al acceder a la base de datos",
                "error_code": "DATABASE_ERROR"
            }
        )
        
    except ValueError as e:
        logger.warning(f"Error en el registro de nuevo usuario: {str(e)}")
        raise HTTPException(
            status_code=422,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error general en el registro de nuevo usuario: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error al crear el usuario: {str(e)}"
        )
        
@user_routers.post("/login", response_model=Token)
async def login(login_data: LoginData, db: Session = Depends(get_db)):
    try:
        logger.info(f"User trying to login: {login_data.username}")
        # Buscar usuario en la base de datos
        user = db.query(User).filter(User.name == login_data.username).first()
        
        # Verificar si el usuario existe y la contraseña es correcta
        if not user or not crypt_verify_password(login_data.password, user.password):
            logger.warning(f"Intento de inicio de sesión fallido, Nombre de usuario o contraseña incorrectos: {login_data.username}")
            raise HTTPException(
                status_code=401,
                detail="Nombre de usuario o contraseña incorrectos"
            )
        
        # Crear el token con un tiempo de expiración
        access_token = create_access_token(
            data={"sub": user.name}
        )
        
        # Preparar datos del usuario para la respuesta
        user_data = {
            "id": user.id,
            "name": user.name,
            "location": user.location,
            "longitud": user.longitud,
            "latitud": user.latitud
        }
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user_data": user_data
        }
    
    except Exception as e:
        logger.error(f"Error general en el inicio de sesión: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error al iniciar sesión: {str(e)}"
        )
        
@user_routers.get("/users/me")
async def read_users_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "name": current_user.name,
        "location": current_user.location,
        "longitud": current_user.longitud,
        "latitud": current_user.latitud
    }