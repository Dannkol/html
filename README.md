# ESP32 IoT Control System

En el plano de la materia de Dispositivos programable de las UTS, se desorrolo el siguiente proyecto:

Este proyecto implementa un sistema IoT que permite controlar y monitorear un motor paso a paso utilizando un ESP32, con una API RESTful como backend y un sistema de WebSockets para comunicación en tiempo real, Tambien monitorea la temperatura y humedad del ambien basandose en un sensor DHT11 y una api de clima para dar recomendaciones.

## Contenido
- [Descripción General](#descripción-general)
- [Componentes del Sistema](#componentes-del-sistema)
- [Configuración del Hardware](#configuración-del-hardware)
- [Configuración del ESP32](#configuración-del-esp32)
- [API Backend](#api-backend)
- [Comunicación en Tiempo Real](#comunicación-en-tiempo-real)
- [Guía de Instalación](#guía-de-instalación)
- [Uso del Sistema](#uso-del-sistema)

## Descripción General

El sistema permite:
- Control remoto de un motor paso a paso
- Monitoreo de temperatura y humedad mediante sensor DHT11
- Analisis de datos de temperatura y humedad para recomendaciones
- Comunicación bidireccional en tiempo real
- Gestión de usuarios y dispositivos
- Sistema de autenticación y autorización

## Componentes del Sistema

### Hardware
- ESP32
- Motor paso a paso 28BYJ-48 con driver ULN2003
- Sensor DHT11 para temperatura y humedad
- Cables de conexión

### Software
- Backend: FastAPI
- Base de datos (integrada con SQLAlchemy)
- Sistema de WebSockets
- Firmware ESP32 (Arduino)
- Frontend: React + Tailwind CSS

## Configuración del Hardware

### Conexiones del ESP32
```
ESP32          |  Componente
----------------|-------------
GPIO4           |  DHT11 Data
GPIO19          |  Motor IN1
GPIO18          |  Motor IN2
GPIO5           |  Motor IN3
GPIO17          |  Motor IN4
5V              |  VCC (Motor y DHT11)
GND             |  GND (Motor y DHT11)
```

## Configuración del ESP32

### Requisitos de Software
```
- Arduino IDE
- Bibliotecas necesarias:
  - WiFi.h
  - HTTPClient.h
  - ArduinoJson.h
  - WebSocketsClient.h
  - DHT.h
  - Stepper.h
```

### Configuración Inicial
```cpp
const char* ssid = "NOMBRE_RED_WIFI";
const char* password = "CONTRASEÑA_WIFI";
const char* serverUrl = "http://TU_IP_SERVIDOR:8000";
const char* wsUrl = "TU_IP_SERVIDOR";
const int wsPort = 8000;
```

### Características del Firmware
- Conexión automática a WiFi
- Registro automático del dispositivo
- Control de motor paso a paso
- Lectura de sensores DHT11
- Comunicación WebSocket bidireccional
- Sistema de reintentos de conexión
- Control de posición del motor

## API Backend

### Endpoints Principales

#### Registro de ESP
```http
POST /api/esp/register
Content-Type: application/json

{
    "identification": "ESP32-ID",
    "user": 1,
    "sensors_data": {
        "humidity": "DTH11",
        "temperature": "DTH11"
    }
}
```

#### Control del Motor
```http
POST /api/esp/{device_id}/motor
Content-Type: application/json

{
    "action": "START_MOTOR" | "STOP_MOTOR"
}
```

#### Validación de Asociación
```http
POST /api/esp/validate-association
Content-Type: application/json

{
    "identification": "ESP32-ID"
}
```

### Autenticación y Usuarios

#### Login
```http
POST /login
Content-Type: application/json

{
    "username": "usuario",
    "password": "contraseña"
}
```

#### Crear Usuario
```http
POST /users/
Content-Type: application/json

{
    "name": "usuario",
    "password": "contraseña",
    "location": "ubicación",
    "longitud": 0.0,
    "latitud": 0.0
}
```

## Comunicación en Tiempo Real

### WebSocket Endpoints

#### Conexión ESP32
```
WS /ws/esp/{device_id}
```

### Mensajes WebSocket

#### Del ESP32 al Servidor
```json
{
    "type": "SENSOR_DATA",
    "temperature": 25.5,
    "humidity": 60.0,
    "deviceId": "ESP32-ID"
}
```

#### Del Servidor al ESP32
```json
{
    "type": "MOTOR_COMMAND",
    "action": "START_MOTOR"
}
```

## Guía de Instalación

1. **Configuración del Hardware**
   - Conectar el ESP32 según el diagrama de conexiones
   - Verificar las conexiones del motor y sensor

2. **Configuración del ESP32**
   ```bash
   # Instalar bibliotecas en Arduino IDE
   - Instalar ESP32 board package
   - Instalar las bibliotecas requeridas
   - Configurar las credenciales WiFi
   - Cargar el código al ESP32
   ```

3. **Configuración del Backend**
   ```bash
   # Instalar dependencias
   pip install -r requirements.txt

   # Iniciar el servidor
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```

## Uso del Sistema

1. **Registro del Dispositivo**
   - El ESP32 se registrará automáticamente al iniciar
   - Verificar el registro en los logs del servidor

2. **Control del Motor**
   - Usar el endpoint `/api/esp/{device_id}/motor` para control
   - Monitorear el estado mediante WebSocket

3. **Monitoreo**
   - Los datos de sensores se envían cada 2 segundos
   - El estado del motor se actualiza en tiempo real

## Consideraciones Importantes

- El motor funciona a 4 RPM cuando se alimenta con 5V del ESP32
- Se recomienda una fuente de alimentación externa para el motor si se requiere más torque
- La comunicación WebSocket se reconecta automáticamente en caso de desconexión
- El sistema mantiene registro de la posición del motor entre paradas

## Solución de Problemas

### Problemas Comunes

1. **Motor no responde**
   - Verificar voltaje de alimentación
   - Comprobar conexiones de pines
   - Revisar velocidad configurada (4 RPM máximo con 5V)

2. **Fallas de Conexión**
   - Verificar credenciales WiFi
   - Comprobar IP y puerto del servidor
   - Revisar los logs del ESP32

3. **Errores de Registro**
   - Validar el ID del dispositivo
   - Verificar la conexión a la base de datos
   - Comprobar que el usuario está asociado al dispositivo y realmente existe