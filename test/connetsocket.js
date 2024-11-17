class WebSocketService {
    constructor() {
        this.socket = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.isConnecting = false;
        this.onDataCallbacks = new Set();
        this.token = null;
        this.reconnectTimeout = null;
        this.lastMessageTimestamp = 0;
        this.messageThreshold = 100; // ms entre mensajes
    }

    async connect(token) {
        if (this.isConnecting || (this.socket?.readyState === WebSocket.OPEN)) {
            console.log('Conexión ya establecida o en proceso');
            return;
        }

        this.isConnecting = true;
        this.token = token;

        try {
            const wsUrl = `ws://192.168.1.62:8000/ws/frontend?token=Bearer ${token}`;
            this.socket = new WebSocket(wsUrl);

            this.socket.onopen = () => {
                console.log('WebSocket conectado exitosamente');
                this.isConnecting = false;
                this.reconnectAttempts = 0;
                if (this.reconnectTimeout) {
                    clearTimeout(this.reconnectTimeout);
                    this.reconnectTimeout = null;
                }
            };

            this.socket.onmessage = this.throttleMessages((event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.handleMessage(data);
                } catch (error) {
                    console.error('Error procesando mensaje:', error);
                }
            });

            this.socket.onclose = (event) => {
                this.handleClose(event);
            };

            this.socket.onerror = (error) => {
                console.error('Error en WebSocket:', error);
                this.isConnecting = false;
            };

        } catch (error) {
            console.error('Error creando conexión WebSocket:', error);
            this.isConnecting = false;
        }
    }

    // Throttle para evitar actualizaciones muy frecuentes
    throttleMessages(callback) {
        return (event) => {
            const now = Date.now();
            if (now - this.lastMessageTimestamp > this.messageThreshold) {
                this.lastMessageTimestamp = now;
                callback(event);
            }
        };
    }

    handleClose(event) {
        this.isConnecting = false;
        console.log('WebSocket desconectado:', event.code, event.reason);

        if (event.code === 4001) {
            console.error('Error de autenticación:', event.reason);
            return;
        }

        if (event.code === 1000) {
            console.log('Conexión cerrada normalmente');
            return;
        }

        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);
            console.log(`Reintentando conexión en ${delay/1000} segundos...`);
            
            this.reconnectTimeout = setTimeout(() => {
                if (!this.isConnecting) {
                    this.reconnectAttempts++;
                    this.connect(this.token);
                }
            }, delay);
        } else {
            console.error('Se alcanzó el máximo de intentos de reconexión');
        }
    }

    handleMessage(message) {
        try {
            // Evitar logging excesivo
            if (message.type !== 'ESP_DATA') {
                console.log('Mensaje recibido:', message.type);
            }
            
            switch (message.type) {
                case 'ESP_DATA':
                    // Actualizar datos sin recargar
                    requestAnimationFrame(() => {
                        this.onDataCallbacks.forEach(callback => callback(message.data));
                    });
                    break;
                    
                case 'SUBSCRIPTION_SUCCESS':
                    console.log(`Suscripción exitosa a ${message.device_id}`);
                    if (message.current_state) {
                        requestAnimationFrame(() => {
                            this.onDataCallbacks.forEach(callback => 
                                callback(message.current_state)
                            );
                        });
                    }
                    break;
                    
                case 'ERROR':
                    console.error('Error del servidor:', message.message);
                    break;
                    
                case 'INITIAL_STATE':
                    console.log('Estado inicial recibido');
                    if (message.data) {
                        requestAnimationFrame(() => {
                            this.updateInitialState(message.data);
                        });
                    }
                    break;
                    
                default:
                    console.log('Mensaje no manejado:', message);
            }
        } catch (error) {
            console.error('Error manejando mensaje:', error);
        }
    }

    updateInitialState(state) {
        try {
            this.onDataCallbacks.forEach(callback => callback(state));
        } catch (error) {
            console.error('Error actualizando estado inicial:', error);
        }
    }

    subscribeToData(callback) {
        if (typeof callback !== 'function') {
            console.error('El callback debe ser una función');
            return () => {};
        }
        
        this.onDataCallbacks.add(callback);
        return () => {
            this.onDataCallbacks.delete(callback);
        };
    }

    subscribeToDevice(deviceId) {
        if (!deviceId) {
            console.error('Device ID es requerido');
            return;
        }

        if (this.socket?.readyState === WebSocket.OPEN) {
            const message = {
                type: 'SUBSCRIBE',
                device_id: deviceId
            };
            console.log('Enviando suscripción:', message);
            this.socket.send(JSON.stringify(message));
        } else {
            console.error('WebSocket no está conectado');
        }
    }

    disconnect() {
        if (this.reconnectTimeout) {
            clearTimeout(this.reconnectTimeout);
            this.reconnectTimeout = null;
        }
        
        if (this.socket) {
            this.socket.close(1000, 'Cierre iniciado por el cliente');
            this.socket = null;
        }
        
        this.isConnecting = false;
        this.reconnectAttempts = 0;
        this.onDataCallbacks.clear();
    }
}

// Ejemplo de uso con actualización de UI
const wsService = new WebSocketService();

function updateDashboard(data) {
    requestAnimationFrame(() => {
        // Actualizar elementos del DOM de forma segura
        try {
            if (data.temperature) {
                const tempElement = document.getElementById('temperature');
                if (tempElement) tempElement.textContent = `${data.temperature}°C`;
            }
            if (data.humidity) {
                const humElement = document.getElementById('humidity');
                if (humElement) humElement.textContent = `${data.humidity}%`;
            }
            // Actualizar otros elementos según necesites
        } catch (error) {
            console.error('Error actualizando dashboard:', error);
        }
    });
}

async function initializeWebSocket(loginData) {
    if (!loginData || !loginData.access_token) {
        console.error('Token de acceso no proporcionado');
        return;
    }

    try {
        // Conectar WebSocket
        await wsService.connect(loginData.access_token);

        // Suscribirse a actualizaciones
        const unsubscribe = wsService.subscribeToData(updateDashboard);

        // Suscribirse al dispositivo específico
        setTimeout(() => {
            wsService.subscribeToDevice("480D3220691C");
        }, 1000);

        // Limpiar al cerrar la página
        window.addEventListener('beforeunload', () => {
            unsubscribe();
            wsService.disconnect();
        });

    } catch (error) {
        console.error('Error inicializando WebSocket:', error);
    }
}

// Prevenir múltiples inicializaciones
let initialized = false;

async function connectWebSocket(loginData) {
    if (initialized) {
        console.log('WebSocket ya inicializado');
        return;
    }
    
    initialized = true;
    await initializeWebSocket(loginData);
}