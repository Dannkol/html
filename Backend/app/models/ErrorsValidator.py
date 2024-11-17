from pydantic import BaseModel
from datetime import datetime

class ErrorResponse(BaseModel):
    detail: str
    error_code: str
    timestamp: datetime = datetime.now()

class AuthenticationError(Exception):
    """Excepción personalizada para errores de autenticación"""
    pass

class DatabaseError(Exception):
    """Excepción personalizada para errores de base de datos"""
    pass