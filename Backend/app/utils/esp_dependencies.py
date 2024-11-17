from sqlalchemy.orm import Session
from datetime import datetime
import logging

from app.utils.database_dependencies import get_transactional_db
from app.models.EspData import EspValidationExistRequest
from app.database.modelsDB import Esp, User, Usuario_Esp

logger = logging.getLogger("app.esp_utils")

def EspValidationExists(device_id: str, db: Session):
    try:
        start_time = datetime.now()
        
        # Consulta optimizada que une las tres tablas
        result = (
            db.query(
                Esp,
                User.id.label('user_id'),
                User.name.label('user_name')
            )
            .join(Usuario_Esp, Esp.id == Usuario_Esp.id_esp)
            .join(User, Usuario_Esp.id_user == User.id)
            .filter(Esp.identification == device_id)
            .first()
        )

        response_time = (datetime.now() - start_time).total_seconds()

        if result:
            # ESP encontrado y asociado
            logger.info(f"ESP {device_id} encontrado y asociado al usuario {result.user_name}")
            return {
                "status": "success",
                "is_associated": True,
                "esp_id": result.Esp.id,
                "user_id": result.user_id,
                "user_name": result.user_name,
                "identification": result.Esp.identification,
                "response_time_seconds": response_time
            }
        else:
            # Verificar si el ESP existe pero no está asociado
            esp = db.query(Esp).filter(
                Esp.identification == device_id
            ).first()
            
            if esp:
                logger.info(f"ESP {device_id} encontrado pero no asociado a ningún usuario")
                return {
                    "status": "success",
                    "is_associated": False,
                    "esp_id": esp.id,
                    "message": "ESP existe pero no está asociado a ningún usuario",
                    "response_time_seconds": response_time
                }
            else:
                logger.info(f"ESP {device_id} no encontrado en el sistema")
                return {
                    "status": "success",
                    "is_associated": False,
                    "message": "ESP no encontrado en el sistema",
                    "response_time_seconds": response_time
                }
    except Exception as e:
        logger.error(f"Error al validar asociación del ESP {device_id}: {str(e)}", exc_info=True)
        raise f"{str(e)}"
        