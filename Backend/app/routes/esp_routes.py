from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import Dict, Any
import logging
from datetime import datetime
from app.models.EspData import EspData, EspValidationExistRequest
from app.utils.database_dependencies import get_transactional_db
from app.database.modelsDB import Esp, User, Usuario_Esp
from app.utils.esp_dependencies import EspValidationExists

logger = logging.getLogger("app.esp_routes")

esp_routes = APIRouter()

@esp_routes.post(
    "/api/esp/register",
    response_model=Dict[str, Any],
    responses={
        200: {
            "description": "ESP registrado o actualizado exitosamente",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "esp_id": 1,
                        "user_id": 1,
                        "message": "ESP registrado y asociado al usuario",
                        "response_time_seconds": 0.125
                    }
                }
            }
        },
        404: {
            "description": "Usuario no encontrado",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Usuario con ID 1 no encontrado"
                    }
                }
            }
        },
        500: {
            "description": "Error interno del servidor",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Error al guardar en la base de datos"
                    }
                }
            }
        }
    }
)
async def register_esp(
    sensor_data: EspData,
    db: Session = Depends(get_transactional_db)
):
    """
    Registra o actualiza un dispositivo ESP y lo asocia con un usuario.
    
    Args:
        sensor_data: Datos del sensor y usuario
        db: Sesión de base de datos con manejo de transacciones
    
    Returns:
        Dict con la información del registro/actualización
    
    Raises:
        HTTPException: Si el usuario no existe o hay errores en la base de datos
    """
    start_time = datetime.now()
    
    try:
        # Verificar si el usuario existe en una sola consulta
        user = db.query(User).filter_by(id=sensor_data.user).first()
        if not user:
            logger.warning(f"Intento de registro con usuario inexistente ID: {sensor_data.user}")
            raise HTTPException(
                status_code=404,
                detail=f"Usuario con ID {sensor_data.user} no encontrado"
            )

        # Buscar o crear ESP en una sola operación
        esp = (
            db.query(Esp)
            .filter_by(identification=sensor_data.identification)
            .first()
        )
        
        if esp:
            # Actualizar ESP existente
            esp.json_sensores = sensor_data.sensors_data
            logger.info(f"Actualizando ESP existente: {sensor_data.identification}")
        else:
            # Crear nuevo ESP
            esp = Esp(
                identification=sensor_data.identification,
                json_sensores=sensor_data.sensors_data
            )
            db.add(esp)
            # Flush para obtener el ID del ESP pero mantener la transacción
            db.flush()
            logger.info(f"Registrando nuevo ESP: {sensor_data.identification}")

        # Verificar la relación usuario-ESP existente
        usuario_esp = (
            db.query(Usuario_Esp)
            .filter_by(id_user=sensor_data.user, id_esp=esp.id)
            .first()
        )

        if not usuario_esp:
            # Crear nueva relación
            usuario_esp = Usuario_Esp(
                id_user=sensor_data.user,
                id_esp=esp.id
            )
            db.add(usuario_esp)
            logger.info(f"Creando nueva relación Usuario-ESP: User {sensor_data.user} - ESP {esp.id}")
        
        # El commit se maneja automáticamente por get_transactional_db
        response_time = (datetime.now() - start_time).total_seconds()
        
        return {
            "status": "success",
            "esp_id": esp.id,
            "user_id": sensor_data.user,
            "message": "ESP actualizado y asociado al usuario" if esp else "ESP registrado y asociado al usuario",
            "response_time_seconds": response_time
        }
            
    except HTTPException as hr:
        # Re-lanzar excepciones HTTP sin modificar
        raise hr
    except Exception as e:
        logger.error(f"Error general en el registro de ESP: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Error interno del servidor"
        )

@esp_routes.post(
    "/api/esp/validate-association",
    response_model=Dict[str, Any],
    responses={
        200: {
            "description": "Validación de asociación ESP exitosa",
            "content": {
                "application/json": {
                    "examples": {
                        "associated": {
                            "value": {
                                "status": "success",
                                "is_associated": True,
                                "esp_id": 1,
                                "user_id": 1,
                                "user_name": "John Doe",
                                "response_time_seconds": 0.125
                            }
                        },
                        "not_associated": {
                            "value": {
                                "status": "success",
                                "is_associated": False,
                                "message": "ESP no encontrado o no asociado",
                                "response_time_seconds": 0.125
                            }
                        }
                    }
                }
            }
        },
        404: {
            "description": "ESP no encontrado",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "ESP con identificador xxx no encontrado"
                    }
                }
            }
        },
        500: {
            "description": "Error interno del servidor",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Error al consultar la base de datos"
                    }
                }
            }
        }
    }
)
async def validate_esp_association(
    validation_data: EspValidationExistRequest,
    db: Session = Depends(get_transactional_db)
):
    """
    Endpoint para validar si un ESP está asociado a un usuario usando su identificador.
    Utiliza la función de utilidad EspValidationExists para la lógica principal.
    
    Args:
        validation_data: Datos de validación del ESP
        db: Sesión de base de datos con manejo de transacciones
    
    Returns:
        Dict con la información de la asociación
    
    Raises:
        HTTPException: Si hay errores en la consulta o en la base de datos
    """
    try:
        logger.info(f"Iniciando validación de asociación para ESP: {validation_data.identification}")
        
        # Utilizar la función de utilidad para la validación
        result = EspValidationExists(validation_data.identification, db)
        
        logger.info(f"Validación completada exitosamente para ESP: {validation_data.identification}")
        return result

    except Exception as e:
        logger.error(f"Error en endpoint de validación de ESP: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Error al consultar la base de datos"
        )