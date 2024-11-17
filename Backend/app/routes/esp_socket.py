# websocket_routes.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any
from datetime import datetime
import logging

from app.utils.WsManager import websocket_manager
from app.utils.database_dependencies import get_transactional_db
from app.utils.esp_dependencies import EspValidationExists
from app.database.modelsDB import Esp, Usuario_Esp, User
from app.models.EspData import ComandMotorsRequest
from app.utils.JWT_Auth import validate_ws_token
import json
# Configurar logger
logger = logging.getLogger("app.websocket_routes")

esp_socket = APIRouter()

async def validate_esp_connection(device_id: str, db: Session) -> bool:
    """
    Valida si el ESP está registrado y asociado a un usuario
    
    Args:
        device_id: Identificador del ESP
        db: Sesión de base de datos
        
    Returns:
        bool: True si el ESP está validado, False en caso contrario
    """
    try:
        result = EspValidationExists(device_id, db)
        return result.get("is_associated", False)
    except Exception as e:
        logger.error(f"Error validando ESP {device_id}: {str(e)}")
        return False

async def update_esp_data(db: Session, esp_id: str, sensor_data: Dict):
    """
    Actualiza los datos del ESP en la base de datos
    """
    try:
        esp = db.query(Esp).filter(Esp.identification == esp_id).first()
        if esp:
            esp.json_sensores = sensor_data
            db.commit()
            logger.info(f"Datos actualizados en BD para ESP {esp_id}")
    except Exception as e:
        logger.error(f"Error actualizando datos del ESP {esp_id}: {str(e)}")
        db.rollback()

@esp_socket.websocket("/ws/esp/{device_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    device_id: str,
    db: Session = Depends(get_transactional_db)
):
    """Endpoint principal del WebSocket para comunicación con ESPs"""
    try:
        # Validar la conexión del ESP
        if not await validate_esp_connection(device_id, db):
            logger.warning(f"ESP no validado o no asociado: {device_id}")
            await websocket.close(code=4000)
            return
            
        # Aceptar la conexión WebSocket
        await websocket_manager.connect_esp(websocket, device_id)
        logger.info(f"Nueva conexión WebSocket establecida: {device_id}")
        
        try:
            while True:
                data = await websocket.receive_json()
                
                if "type" in data and data["type"] == "SENSOR_DATA":
                    sensor_data = {
                        "temperature": data.get("temperature"),
                        "humidity": data.get("humidity"),
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    # Usar broadcast_esp_data en lugar de broadcast_to_frontends
                    await websocket_manager.broadcast_esp_data(device_id, sensor_data)
                    logger.info(f"Datos recibidos de {device_id}")
                    
        except WebSocketDisconnect:
            logger.info(f"Desconexión normal del cliente: {device_id}")
        except Exception as e:
            logger.error(f"Error procesando mensajes de {device_id}: {str(e)}")
        finally:
            websocket_manager.disconnect_esp(device_id)
            
    except Exception as e:
        logger.error(f"Error en la conexión WebSocket de {device_id}: {str(e)}")
        try:
            await websocket.close(code=1011)
        except:
            pass

@esp_socket.post("/api/esp/{device_id}/motor")
async def control_motor(device_id: str, command: ComandMotorsRequest, db: Session = Depends(get_transactional_db)):
    """
    Endpoint para controlar el motor de un ESP
    
    Args:
        device_id: Identificador del ESP
        command: Comando para el motor ("START_MOTOR" o "STOP_MOTOR")
        db: Sesión de base de datos
        
    Returns:
        dict: Resultado de la operación
    """
    try:
        if not websocket_manager.is_connected_esp(device_id):
            raise HTTPException(status_code=404, detail="ESP no conectado")
        
        command_dict = {
            "type": "MOTOR_COMMAND",
            "action": command.action  # Ya está validado
        }
            
        success = await websocket_manager.send_command_to_esp(device_id, command_dict)
        
        if not success:
            raise HTTPException(status_code=500, detail="Error al enviar comando")
            
        return {
            "status": "success",
            "message": f"Comando {command.action} enviado exitosamente",
            "device_id": device_id
        }
        
    except ValueError as e:
        logger.error(f"Error en control de motor para {device_id}: {str(e)}")
        raise HTTPException(status_code=422, detail=str(e))
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en control de motor para {device_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@esp_socket.get("/api/esp/{device_id}/state")
async def get_esp_state(device_id: str, db: Session = Depends(get_transactional_db)):
    """
    Endpoint para obtener el último estado conocido de un ESP
    
    Args:
        device_id: Identificador del ESP
        db: Sesión de base de datos
        
    Returns:
        dict: Estado actual del ESP
    """
    try:
        
        if not await validate_esp_connection(device_id, db):
            raise HTTPException(status_code=404, detail="ESP no encontrado")
        
        state = websocket_manager.get_esp_state(device_id)
        if not state:
            raise HTTPException(
                status_code=404,
                detail="No hay datos disponibles para este ESP"
            )
            
        return {
            "status": "success",
            "data": state
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo estado de {device_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")
    
@esp_socket.websocket("/ws/frontend")
async def frontend_websocket_endpoint(websocket: WebSocket, db: Session = Depends(get_transactional_db)):
    """Endpoint WebSocket para clientes frontend."""
    user = None
    try:
        # 1. Validación del token
        authorization_header = websocket.query_params.get("token")
        if not authorization_header:
            await websocket.close(code=4001, reason="Token no proporcionado")
            return

        user = await validate_ws_token(authorization_header, db)
        if not user:
            await websocket.close(code=4001, reason="Token inválido")
            return

        logger.info(f"Usuario {user.name} validado correctamente")

        # 2. Establecer conexión
        await websocket_manager.connect_frontend(websocket, user.name)
        
        # 3. Bucle principal de mensajes
        while True:
            try:
                message = await websocket.receive_json()
                logger.debug(f"Mensaje recibido de {user.name}: {message}")

                if not isinstance(message, dict) or "type" not in message:
                    continue

                if message["type"] == "SUBSCRIBE":
                    device_id = message.get("device_id")
                    if not device_id:
                        continue

                    # Verificar acceso al dispositivo
                    usuario_esp = (
                        db.query(Usuario_Esp)
                        .join(Esp)
                        .join(User)
                        .filter(
                            Esp.identification == device_id,
                            User.name == user.name
                        )
                        .first()
                    )

                    if not usuario_esp:
                        await websocket.send_json({
                            "type": "ERROR",
                            "message": "No tienes acceso a este dispositivo"
                        })
                        continue

                    # Realizar suscripción
                    websocket_manager.subscribe_to_device(user.name, device_id)
                    
                    # Enviar estado actual si existe
                    current_state = websocket_manager.get_esp_state(device_id)
                    if current_state:
                        await websocket.send_json({
                            "type": "ESP_DATA",
                            "device_id": device_id,
                            "data": current_state
                        })

            except WebSocketDisconnect:
                logger.info(f"Cliente {user.name} desconectado")
                break
            except Exception as e:
                logger.error(f"Error procesando mensaje: {str(e)}")
                continue

    except Exception as e:
        logger.error(f"Error en websocket frontend: {str(e)}")
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.close(code=1011)
    finally:
        if user and hasattr(user, 'name'):
            websocket_manager.disconnect_frontend(user.name)