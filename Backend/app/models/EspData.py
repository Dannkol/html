from pydantic import BaseModel, Field, field_validator
from typing import Dict

class EspData(BaseModel):
    identification: str = Field(..., min_length=1, max_length=50)
    user: int = Field(..., description="ID del usuario")
    sensors_data: Dict = Field(...)

    class Config:
        json_schema_extra = {
            "example": {
                "identification": "ESP32-ABC123",
                "user": 1,
                "sensors_data":
                    {
                        "temperature": 25.2,
                        "humidity": 86,
                        "timestamp": "2024-11-17T01:05:29.029237"
                    }
                
            }
        }

class EspValidationExistRequest(BaseModel):
    identification: str
    
class ComandMotorsRequest(BaseModel):
    action: str = Field(..., description="Accion a realizar")
    
    @field_validator("action")
    def validate_action(cls, value):
        if value not in ["START_MOTOR", "STOP_MOTOR"]:
            raise ValueError("Action must be either START_MOTOR or STOP_MOTOR")
        return value 
    
    class Config:
        json_schema_extra = {
            "example": {
                "action": "START_MOTOR"
            }
        }