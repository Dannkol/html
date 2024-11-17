from pydantic import BaseModel, field_validator
from typing import Optional

class UserCreate(BaseModel):
    name: str
    password: str
    location: Optional[str] = None
    longitud: Optional[float] = None
    latitud: Optional[float] = None

    @field_validator('name')
    def name_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError('El nombre no puede estar vacío')
        if len(v) > 50:
            raise ValueError('El nombre no puede tener más de 50 caracteres')
        return v.strip()

    @field_validator('password')
    def password_must_be_strong(cls, v):
        if len(v) < 8:
            raise ValueError('La contraseña debe tener al menos 8 caracteres')
        return v

    @field_validator('latitud')
    def validate_latitud(cls, v):
        if v is not None and (v < -90 or v > 90):
            raise ValueError('La latitud debe estar entre -90 y 90 grados')
        return v

    @field_validator('longitud')
    def validate_longitud(cls, v):
        if v is not None and (v < -180 or v > 180):
            raise ValueError('La longitud debe estar entre -180 y 180 grados')
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Dannkol",
                "password": "contraseña1234",
                "location": "Ciudad de México",
                "longitud": -99.133208,
                "latitud": 19.432608
            }
        }

class LoginData(BaseModel):
    username: str
    password: str    

class Token(BaseModel):
    access_token: str
    token_type: str
    user_data: dict