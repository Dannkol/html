from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.utils.auth import get_protected_router

import logging
from logging.handlers import RotatingFileHandler
import os

# Import routes
from app.routes.esp_routes import esp_routes
from app.routes.user_routes import user_routers
from app.routes.esp_socket import esp_socket

# Crear el directorio de logs si no existe
log_directory = "logs"
if not os.path.exists(log_directory):
    os.makedirs(log_directory)

# Configuración del logging
def setup_logging():
    # Configurar el formato del log
    log_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Configurar el logger raíz
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Handler para archivo con rotación
    file_handler = RotatingFileHandler(
        filename=os.path.join(log_directory, 'app.log'),
        maxBytes=10485760,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(log_format)
    
    # Handler para consola
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_format)
    
    # Agregar handlers al logger raíz
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Crear logger específico para la aplicación
    logger = logging.getLogger("app")
    logger.setLevel(logging.INFO)
    
    return logger

# Eventos de inicio y apagado
def lifespan(_):
    logger.info("Aplicación iniciada correctamente")
    yield
    logger.info("Apagando aplicación...")

app =  FastAPI(
    title="ESP Management API",
    description="API para gestionar dispositivos ESP y sus datos de sensores",
    version="1.0.0",
    lifespan=lifespan,
    host="0.0.0.0",
    port=8000,
    reload=True
)


# Configurar el logging al iniciar la aplicación
logger = setup_logging()
logger.info("Iniciando aplicación...")

# CORS middleware
origins = [
    "*"
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir rutas
app.include_router(esp_routes, tags=["ESP Management"])
app.include_router(user_routers, tags=["User Management"])
app.include_router(esp_socket, tags=["ESP Management"])

# Endpoint de health check
@app.get("/health")
async def health_check():
    return {"status": "ok"}