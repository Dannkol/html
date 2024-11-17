// Instalar las librerias necesarias desde Arduino IDE
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <WebSocketsClient.h>
#include <DHT.h>
#include <Stepper.h>

// Configuración WiFi
const char* ssid = "ACCESO_DENEGADO";
const char* password = "2018toyota";

// Configuración del servidor
const char* serverUrl = "http://192.168.1.62:8000";  // Ajustar el puerto según la configuración del backend
const char* wsUrl = "192.168.1.62";                  // IP backend
const int wsPort = 8000;                            // Puerto de backend

// Configuración DHT11
#define DHTPIN 4
#define DHTTYPE DHT11

DHT dht(DHTPIN, DHTTYPE);

// Configuración del motor paso a paso
#define IN1 19
#define IN2 18
#define IN3 5
#define IN4 17
const int stepsPerRevolution = 2048;  // Ajusta según tu motor
Stepper myStepper(stepsPerRevolution, IN1, IN3, IN2, IN4); // Pines del motor

// Variables globales
String ChipId;
bool isRegistered = false;
bool motorStartRequest = false;
bool motorStopRequest = false;
bool motorActive = false;
WebSocketsClient webSocket;

// Variables globales adicionales
volatile bool emergencyStop = false;
volatile int currentPosition = 0;  // Posición actual del motor
volatile int targetPosition = 0;   // Posición objetivo
volatile int lastSavedPosition = 0; // Última posición guardada antes de detener
const int FULL_REVOLUTION_STEPS = stepsPerRevolution * 3; // 3 revoluciones completas
const int MOTOR_SPEED = 4; // Reducido a 4 RPM para funcionamiento con 5V

// Estructura para datos del sensor
struct SensorData {
  float temperature;
  float humidity;
};

// Estructura para el estado del motor
struct MotorState {
  bool isRunning;
  int position;
  String status;
} motorState;

// Función para obtener la MAC
String getChipId() {
  uint64_t chipid = ESP.getEfuseMac(); // El ID único de fábrica
  char chipString[15];
  snprintf(chipString, sizeof(chipString), "%04X%08X", 
           (uint16_t)(chipid >> 32), (uint32_t)chipid);
  return String(chipString);
}


// Función para mover el motor de manera más suave
void moveMotorStep(int steps) {
  for(int i = 0; i < abs(steps); i++) {
    myStepper.step(steps > 0 ? 1 : -1);
    vTaskDelay(2); // Pequeña pausa entre pasos para estabilidad
  }
}

// Función para validar registro del ESP
bool validateEspRegistration() {
  HTTPClient http;
  String url = String(serverUrl) + "/api/esp/validate-association";
  
  StaticJsonDocument<200> doc;
  doc["identification"] = ChipId;
  
  String jsonString;
  serializeJson(doc, jsonString);
  
  http.begin(url);
  http.addHeader("Content-Type", "application/json");
  
  int httpCode = http.POST(jsonString);
  
  if (httpCode == 200) {
    String payload = http.getString();
    StaticJsonDocument<500> response;
    deserializeJson(response, payload);
    
    http.end();
    return response["is_associated"];
  }
  
  http.end();
  return false;
}

// Función para registrar el ESP
#include <HTTPClient.h>
#include <ArduinoJson.h>

bool registerEsp(int userId) {
    HTTPClient http;
    String url = String(serverUrl) + "/api/esp/register";
    
    // Crear el documento JSON
    StaticJsonDocument<500> doc;
    doc["identification"] = ChipId; // Identificador del ESP32
    doc["user"] = userId;
    
    // Configurar la estructura de "sensors_data"
    JsonObject sensors_data = doc.createNestedObject("sensors_data");
    sensors_data["humidity"] = "DTH11";
    sensors_data["pressure"] = "BPS";
    sensors_data["temperature"] = "DTH11";
    
    JsonArray actuators = sensors_data.createNestedArray("actuators");
    JsonObject actuator = actuators.createNestedObject();
    actuator["pin"] = 13;
    actuator["status"] = "off";
    actuator["type"] = "motor_step";

    // Convertir a cadena JSON
    String jsonString;
    serializeJson(doc, jsonString);

    // Configurar la petición HTTP
    http.begin(url);
    http.addHeader("Content-Type", "application/json");

    // Enviar la petición
    int httpCode = http.POST(jsonString);

    // Validar el código de respuesta HTTP
    bool success = (httpCode == 200);

    // Finalizar la conexión HTTP
    http.end();
    
    return success;
}

// Función para detener el motor de forma segura
void stopMotor() {
  motorActive = false;
  motorStopRequest = false;
  emergencyStop = false;
  lastSavedPosition = currentPosition;
  
  // Enviar confirmación de detención
  StaticJsonDocument<200> doc;
  doc["type"] = "MOTOR_STATUS";
  doc["status"] = "STOPPED";
  doc["deviceId"] = ChipId;
  doc["position"] = currentPosition;
  doc["saved_position"] = lastSavedPosition;
  String jsonString;
  serializeJson(doc, jsonString);
  webSocket.sendTXT(jsonString);
  
  Serial.println("Motor detenido en posición: " + String(lastSavedPosition));
}

// Función para enviar el estado del motor
void sendMotorStatus(const char* status) {
  StaticJsonDocument<200> doc;
  doc["type"] = "MOTOR_STATUS";
  doc["status"] = status;
  doc["deviceId"] = ChipId;
  doc["current_position"] = currentPosition;
  doc["target_position"] = targetPosition;
  String jsonString;
  serializeJson(doc, jsonString);
  webSocket.sendTXT(jsonString);
}

// Tarea para el control del motor actualizada
void controlMotor(void * parameter) {
  const int STEPS_PER_BATCH = 32; // Mover en pequeños lotes para mejor control
  
  for (;;) {
    if (motorStopRequest || emergencyStop) {
      stopMotor();
      vTaskDelay(10);
      continue;
    }

    if (motorStartRequest && !emergencyStop) {
      motorActive = true;
      Serial.println("Motor iniciando desde posición: " + String(lastSavedPosition));
      
      // Calcular pasos restantes
      currentPosition = lastSavedPosition;
      targetPosition = FULL_REVOLUTION_STEPS;
      
      // Enviar estado inicial
      StaticJsonDocument<200> doc;
      doc["type"] = "MOTOR_STATUS";
      doc["status"] = "RUNNING";
      doc["deviceId"] = ChipId;
      doc["current_position"] = currentPosition;
      String jsonString;
      serializeJson(doc, jsonString);
      webSocket.sendTXT(jsonString);

      // Mover el motor en pequeños incrementos
      while (currentPosition < targetPosition && motorActive) {
        if (motorStopRequest || emergencyStop) {
          stopMotor();
          break;
        }

        int stepsToMove = min(STEPS_PER_BATCH, targetPosition - currentPosition);
        moveMotorStep(stepsToMove);
        currentPosition += stepsToMove;

        // Actualización periódica (cada 128 pasos)
        if (currentPosition % 128 == 0) {
          StaticJsonDocument<200> updateDoc;
          updateDoc["type"] = "MOTOR_STATUS";
          updateDoc["status"] = "RUNNING";
          updateDoc["deviceId"] = ChipId;
          updateDoc["current_position"] = currentPosition;
          String updateJson;
          serializeJson(updateDoc, updateJson);
          webSocket.sendTXT(updateJson);
        }

        vTaskDelay(1);
      }

      // Si completó el movimiento
      if (motorActive && currentPosition >= targetPosition) {
        motorActive = false;
        currentPosition = 0;
        lastSavedPosition = 0;
        
        StaticJsonDocument<200> completeDoc;
        completeDoc["type"] = "MOTOR_STATUS";
        completeDoc["status"] = "COMPLETED";
        completeDoc["deviceId"] = ChipId;
        String completeJson;
        serializeJson(completeDoc, completeJson);
        webSocket.sendTXT(completeJson);
      }
      
      motorStartRequest = false;
    }
    
    vTaskDelay(10);
  }
}

// Función para leer los sensores
SensorData readSensors() {
  SensorData data;
  data.temperature = dht.readTemperature();
  data.humidity = dht.readHumidity();
  
  if (isnan(data.temperature) || isnan(data.humidity)) {
    Serial.println("Error leyendo el sensor DHT11");
    data.temperature = 0;
    data.humidity = 0;
  }
  
  return data;
}

// Actualizar el callback del WebSocket
void webSocketEvent(WStype_t type, uint8_t * payload, size_t length) {
  switch(type) {
    case WStype_TEXT:
      {
        String message = String((char*)payload);
        Serial.println("Mensaje WebSocket recibido: " + message);
        
        StaticJsonDocument<200> doc;
        DeserializationError error = deserializeJson(doc, message);
        
        if (error) {
          Serial.print("deserializeJson() falló: ");
          Serial.println(error.c_str());
          return;
        }
        
        const char* type = doc["type"] | "UNKNOWN";
        if (strcmp(type, "MOTOR_COMMAND") == 0) {
          const char* action = doc["action"] | "UNKNOWN";
          Serial.print("Acción recibida: ");
          Serial.println(action);
          
          if (strcmp(action, "START_MOTOR") == 0) {
            emergencyStop = false;
            motorStartRequest = true;
            motorStopRequest = false;
            Serial.println("Continuando desde posición: " + String(lastSavedPosition));
          } 
          else if (strcmp(action, "STOP_MOTOR") == 0) {
            emergencyStop = true;
            motorStopRequest = true;
            motorStartRequest = false;
          }
        }
      }
      break;
      
    case WStype_CONNECTED:
      {
        Serial.println("WebSocket Conectado");
        // Enviar estado inicial
        sendMotorStatus(motorActive ? "RUNNING" : "STOPPED");
      }
      break;
      
    // ... resto del código del callback ...
  }
}

// Tarea para enviar datos por WebSocket
void sendSensorData(void * parameter) {
  for(;;) {
    if(isRegistered) {
      SensorData data = readSensors();
      
      StaticJsonDocument<200> doc;
      doc["type"] = "SENSOR_DATA";
      doc["temperature"] = data.temperature;
      doc["humidity"] = data.humidity;
      doc["deviceId"] = ChipId;
      
      String jsonString;
      serializeJson(doc, jsonString);
      
      webSocket.sendTXT(jsonString);
    }
    vTaskDelay(2000); // Enviar datos cada 2 segundos
  }
}

void setup() {
  Serial.begin(115200);
  
  // Inicializar componentes
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nConectado a WiFi");
  
  ChipId = getChipId();
  Serial.println("ChipId Address: " + ChipId);
  
  dht.begin();

  // Inicializar variables de posición
  currentPosition = 0;
  lastSavedPosition = 0;

  // Configurar la tarea del motor con mayor prioridad
  myStepper.setSpeed(MOTOR_SPEED); // 4 RPM para funcionar con 5V
  xTaskCreate(
    controlMotor,
    "ControlMotor",
    10000,
    NULL,
    3,
    NULL
  );
  // Verificar registro
  isRegistered = validateEspRegistration();
  
  if (!isRegistered) {
    Serial.println("ESP no registrado. Iniciando proceso de registro...");
    // Aquí podrías implementar un método para obtener el userId
    // Por ejemplo, mediante un endpoint adicional o configuración manual
    int userId = 4; // Este valor debería venir de alguna configuración
    
    if (registerEsp(userId)) {
      isRegistered = true;
      Serial.println("ESP registrado exitosamente");
    } else {
      Serial.println("Error en el registro");
    }
  }
  
  if (isRegistered) {
    // Crear la URL dinámica con el device_id
    String wsEndpoint = String("/ws/esp/") + ChipId;

    // Configurar WebSocket
    webSocket.begin(wsUrl, wsPort, wsEndpoint.c_str());
    webSocket.onEvent(webSocketEvent);
    webSocket.setReconnectInterval(5000);
    
    // Crear tareas
    xTaskCreate(controlMotor, "ControlMotor", 10000, NULL, 1, NULL);
    xTaskCreate(sendSensorData, "SendSensorData", 10000, NULL, 1, NULL);
  }

}

void loop() {
  if (isRegistered) {
    webSocket.loop();
  }
}