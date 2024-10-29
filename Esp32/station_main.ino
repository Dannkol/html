// Instalar las librerias necesarias desde Arduino IDE

#include <WiFi.h>
#include <WebSocketsServer.h>
#include <DHT.h>
#include <Stepper.h>

// Configuración del sensor DHT11
#define DHTPIN 4  // Pin donde está conectado el DHT11
#define DHTTYPE DHT11  // Tipo de sensor DHT
DHT dht(DHTPIN, DHTTYPE);

// Configuración del motor paso a paso
const int stepsPerRevolution = 2048;  // Cambiar según las revoluciones del motor
#define IN1 19
#define IN2 18
#define IN3 5
#define IN4 17

Stepper myStepper(stepsPerRevolution, IN1, IN3, IN2, IN4);

// Nombre de la red Wi-Fi y contraseña
const char* ssid = "****";
const char* password = "******";  // Coloca la contraseña si la red la tiene

// Crear servidor WebSocket en el puerto 81
WebSocketsServer webSocket = WebSocketsServer(81);

// Variables de control
bool motorActive = false;
bool manualControl = false;
bool motorStartRequest = false;
bool motorStopRequest = false;

// Tarea para controlar el motor paso a paso sin bloquear
void controlMotor(void * parameter) {
  for (;;) {
    if (motorStartRequest) {
      motorActive = true;
      Serial.println("Iniciando el motor");
      for (int i = 0; i < 3; i++) {
        myStepper.step(stepsPerRevolution);  // Girar una vuelta completa
        delay(100);  // Pausa entre giros
      }
      motorStartRequest = false;  // Resetear la petición de inicio
    }

    if (motorStopRequest) {
      motorActive = false;
      Serial.println("Motor detenido");
      motorStopRequest = false;  // Resetear la petición de parada
    }
    vTaskDelay(10);  // Esperar un poco antes de verificar de nuevo
  }
}

// Función para enviar los datos del sensor a través del WebSocket
void sendSensorData() {
  float temperature = dht.readTemperature();
  float humidity = dht.readHumidity();

  if (isnan(temperature) || isnan(humidity)) {
    Serial.println("Error leyendo los datos del sensor DHT11");
    return;
  }

  // Si la humedad supera el 80% y no estamos en control manual, activar el motor
  if (humidity > 80 && !manualControl && !motorActive) {
    Serial.println("Humedad mayor a 80%. Girando el motor 3 veces.");
    motorStartRequest = true;  // Solicitar que se inicie el motor
    manualControl = true;
  }
  if (humidity < 70 && manualControl) {
    Serial.println("Humedad menor al 70%. Deteniendo el motor.");
    motorStopRequest = true;  // Solicitar que se detenga el motor
    manualControl = false;
  }

  // Crear el mensaje en formato JSON
  String jsonData = "{\"temperature\":" + String(temperature) + ",\"humidity\":" + String(humidity) + ",\"motorActive\":" + String(motorActive ? "true" : "false") + "}";
  
  // Enviar el mensaje a todos los clientes conectados
  webSocket.broadcastTXT(jsonData);
}

// Función para manejar las conexiones WebSocket
void webSocketEvent(uint8_t num, WStype_t type, uint8_t * payload, size_t length) {
  switch (type) {
    case WStype_DISCONNECTED:
      Serial.printf("[%u] Desconectado\n", num);
      break;
    case WStype_CONNECTED: {
      IPAddress ip = webSocket.remoteIP(num);
      Serial.printf("[%u] Conectado desde %d.%d.%d.%d\n", num, ip[0], ip[1], ip[2], ip[3]);
      break;
    }
    case WStype_TEXT:
      // Si recibimos un mensaje desde el cliente para iniciar o detener el motor
      if (strcmp((char*)payload, "START_MOTOR") == 0) {
        manualControl = true;
        motorStartRequest = true;  // Solicitar inicio del motor
      } else if (strcmp((char*)payload, "STOP_MOTOR") == 0) {
        motorStopRequest = true;  // Solicitar parada del motor
        manualControl = false;
      }
      break;
  }
}

void setup() {
  // Inicializar el sensor DHT11
  dht.begin();

  // Inicializar el puerto serial
  Serial.begin(115200);

  // Configuración del motor paso a paso
  myStepper.setSpeed(5);  // Configurar la velocidad del motor (RPM)

  // Conectar a la red Wi-Fi
  Serial.println();
  Serial.println("Conectando a la red Wi-Fi...");
  WiFi.begin(ssid, password);
  
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.print(".");
  }

  Serial.println();
  Serial.println("Conectado a la red Wi-Fi");
  Serial.print("Dirección IP: ");
  Serial.println(WiFi.localIP());

  // Iniciar WebSocket
  webSocket.begin();
  webSocket.onEvent(webSocketEvent);

  Serial.println("WebSocket iniciado en el puerto 81");

  // Crear la tarea de control del motor
  xTaskCreate(controlMotor, "ControlMotorTask", 10000, NULL, 1, NULL);
}

void loop() {
  // Manejar las conexiones WebSocket
  webSocket.loop();

  // Enviar los datos del sensor periódicamente (cada 2 segundos)
  sendSensorData();
  delay(2000);
}
