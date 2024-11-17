from fastapi import WebSocket, WebSocketDisconnect, HTTPException
from datetime import datetime
import logging

# Se pretende manejar el buffer de datos
# este guardaria los datos que se envian a los clientes
# en un archivo .log para su posterior análisis o backup en db

# from app.utils.BufferManager import data_buffer 

logger = logging.getLogger("app.connection_manager")

class ConnectionManager:
    def __new__(cls):
        if not hasattr(cls, '_instance'):
            cls._instance = super(ConnectionManager, cls).__new__(cls)
            cls._instance.esp_connections = {}
            cls._instance.frontend_connections = {}
            cls._instance.esp_states = {}
            cls._instance.user_devices = {}
            cls._instance.device_subscribers = {}
        return cls._instance

    def is_connected_esp(self, device_id: str) -> bool:
        """Verifica si un ESP está conectado"""
        return device_id in self.esp_connections and self.esp_connections[device_id] is not None

    async def connect_esp(self, websocket: WebSocket, device_id: str):
        """Conecta un ESP"""
        await websocket.accept()
        self.esp_connections[device_id] = websocket
        logger.info(f"ESP conectado: {device_id}")

    def disconnect_esp(self, device_id: str):
        """Desconecta un ESP"""
        if device_id in self.esp_connections:
            del self.esp_connections[device_id]
        logger.info(f"ESP desconectado: {device_id}")

    async def connect_frontend(self, websocket: WebSocket, user_id: str):
        """Conecta un cliente frontend"""
        await websocket.accept()
        self.frontend_connections[user_id] = websocket
        if user_id not in self.user_devices:
            self.user_devices[user_id] = set()
        logger.info(f"Nueva conexión frontend para usuario: {user_id}")

    def disconnect_frontend(self, user_id: str):
        """Desconecta un cliente frontend"""
        if user_id in self.frontend_connections:
            del self.frontend_connections[user_id]
        logger.info(f"Cliente frontend desconectado: {user_id}")

    def subscribe_to_device(self, user_id: str, device_id: str) -> bool:
        """Suscribe un usuario a un dispositivo"""
        try:
            if device_id not in self.device_subscribers:
                self.device_subscribers[device_id] = set()
            
            self.device_subscribers[device_id].add(user_id)
            
            if user_id not in self.user_devices:
                self.user_devices[user_id] = set()
            self.user_devices[user_id].add(device_id)
            
            logger.info(f"Usuario {user_id} suscrito al dispositivo {device_id}")
            return True
        except Exception as e:
            logger.error(f"Error en suscripción: {str(e)}")
            return False

    async def send_command_to_esp(self, device_id: str, command: dict) -> bool:
        """
        Envía un comando a un ESP específico
        
        Args:
            device_id: Identificador del ESP
            command: Diccionario con el comando a enviar
            
        Returns:
            bool: True si el comando se envió exitosamente
            
        Raises:
            HTTPException: Si el ESP no está conectado o hay un error al enviar el comando
        """
        try:
            if not self.is_connected_esp(device_id):
                raise HTTPException(
                    status_code=404,
                    detail=f"ESP {device_id} no está conectado"
                )

            websocket = self.esp_connections[device_id]
            
            logger.info(f"Enviando comando a {device_id}: {command}")
            
            # Enviar el comando como JSON
            await websocket.send_json(command)
            
            # Actualizar el estado del motor en esp_states
            if command.get("action"):
                current_state = self.esp_states.get(device_id, {})
                current_state["motor_status"] = "running" if command["action"] == "START_MOTOR" else "stopped"
                current_state["last_update"] = datetime.now().isoformat()
                self.esp_states[device_id] = current_state
                
                # Notificar a los suscriptores del cambio de estado
                await self.broadcast_esp_data(device_id, current_state)
            
            logger.info(f"Comando enviado exitosamente a {device_id}: {command}")
            return True
            
        except WebSocketDisconnect:
            self.disconnect_esp(device_id)
            raise HTTPException(
                status_code=404,
                detail=f"ESP {device_id} se desconectó durante el envío del comando"
            )
        except Exception as e:
            logger.error(f"Error enviando comando a {device_id}: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error enviando comando al ESP: {str(e)}"
            )

    async def broadcast_esp_data(self, device_id: str, data: dict):
        """Transmite datos del ESP a sus suscriptores"""
        try:
            # Actualizar estado del ESP
            self.esp_states[device_id] = {
                **data,
                "last_update": datetime.now().isoformat()
            }
            state = self.esp_states[device_id]

            # Obtener suscriptores para este dispositivo
            subscribers = self.device_subscribers.get(device_id, set()).copy()
            
            # Preparar mensaje
            message = {
                "type": "ESP_DATA",
                "device_id": device_id,
                "data": state
            }

            # Enviar a cada suscriptor
            for user_id in subscribers:
                if user_id in self.frontend_connections:
                    try:
                        websocket = self.frontend_connections[user_id]
                        await websocket.send_json(message)
                        logger.debug(f"Datos enviados a usuario {user_id}")
                    except WebSocketDisconnect:
                        logger.info(f"Cliente {user_id} desconectado durante broadcast")
                        self.disconnect_frontend(user_id)
                    except Exception as e:
                        logger.error(f"Error enviando datos a {user_id}: {str(e)}")
                        # No desconectar por otros tipos de errores

        except Exception as e:
            logger.error(f"Error en broadcast_esp_data: {str(e)}")

    def get_esp_state(self, device_id: str):
        """Obtiene el último estado conocido de un ESP"""
        return self.esp_states.get(device_id)

# Instancia única
websocket_manager = ConnectionManager()