from fastapi import Depends
import json
from datetime import datetime
import os
from typing import Dict, List
import asyncio
import logging
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager

from app.database.modelsDB import Esp
from app.database.database import database

logger = logging.getLogger("app.data_buffer")

class DataBufferManager:
    _instance = None
    BUFFER_FILE = "sensor_data_buffer.json"
    BATCH_SIZE = 50
    FLUSH_INTERVAL = 300

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DataBufferManager, cls).__new__(cls)
            cls._instance.initialize()
        return cls._instance

    def initialize(self):
        self.buffer: List[Dict] = []
        self.last_flush = datetime.now()
        
        if os.path.exists(self.BUFFER_FILE):
            try:
                with open(self.BUFFER_FILE, 'r') as f:
                    self.buffer = json.load(f)
            except json.JSONDecodeError:
                self.buffer = []
                logger.error("Error leyendo archivo buffer, iniciando vacío")
        
        # Iniciar tarea de procesamiento periódico
        asyncio.create_task(self.periodic_flush())

    async def add_data(self, device_id: str, sensor_data: dict) -> dict:
        try:
            timestamp = datetime.now().isoformat()
            data_entry = {
                "device_id": device_id,
                "data": sensor_data,
                "timestamp": timestamp
            }
            
            self.buffer.append(data_entry)
            await self.save_to_file()
            
            if len(self.buffer) >= self.BATCH_SIZE:
                asyncio.create_task(self.process_batch())
            
            return {
                "type": "SENSOR_UPDATE",
                "device_id": device_id,
                "data": {**sensor_data, "timestamp": timestamp}
            }
            
        except Exception as e:
            logger.error(f"Error añadiendo datos al buffer: {str(e)}")
            return None

    async def save_to_file(self):
        try:
            # Usar aiofiles para operaciones de archivo asíncronas
            with open(self.BUFFER_FILE, 'w') as f:
                json.dump(self.buffer, f)
        except Exception as e:
            logger.error(f"Error guardando en archivo: {str(e)}")

    async def process_batch(self):
        """Procesa un lote de datos y los guarda en la base de datos"""
        if not self.buffer:
            return
            
        try:
            # Crear una nueva sesión
            Session = database._SessionFactory
            db = Session()
            
            try:
                # Procesar datos en lote
                processed_data = {}
                for entry in self.buffer:
                    device_id = entry["device_id"]
                    if device_id not in processed_data:
                        processed_data[device_id] = {
                            "latest_data": entry["data"],
                            "timestamp": entry["timestamp"],
                            "data_points": []
                        }
                    processed_data[device_id]["data_points"].append({
                        "data": entry["data"],
                        "timestamp": entry["timestamp"]
                    })

                # Actualizar la base de datos
                for device_id, data in processed_data.items():
                    esp = db.query(Esp).filter(Esp.identification == device_id).first()
                    if esp:
                        esp.json_sensores = {
                            "current": data["latest_data"],
                            "history": data["data_points"][-10:]
                        }

                # Commit de los cambios
                db.commit()
                logger.info(f"Procesado lote de {len(self.buffer)} registros")
                
                # Limpiar buffer
                self.buffer = []
                await self.save_to_file()

            except Exception as e:
                db.rollback()
                logger.error(f"Error procesando lote: {str(e)}")
                raise
            finally:
                db.close()

        except Exception as e:
            logger.error(f"Error en proceso de lote: {str(e)}")

    async def periodic_flush(self):
        """Procesa el buffer periódicamente"""
        while True:
            try:
                await asyncio.sleep(self.FLUSH_INTERVAL)
                if self.buffer:
                    await self.process_batch()
            except Exception as e:
                logger.error(f"Error en flush periódico: {str(e)}")

# Exportar instancia única
data_buffer = DataBufferManager()