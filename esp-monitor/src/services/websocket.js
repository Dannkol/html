export class WebSocketService {
    static instance = null;
    static connecting = false;
    static connectionPromise = null;
  
    constructor(url, token) {
      if (WebSocketService.instance) {
        return WebSocketService.instance;
      }
  
      this.url = url;
      this.token = token;
      this.socket = null;
      this.listeners = new Set();
      this.deviceId = null;
      this.retryTimeout = null;
  
      WebSocketService.instance = this;
      return this;
    }
  
    async connect() {
      // Si ya hay una conexión activa, retornarla
      if (this.socket?.readyState === WebSocket.OPEN) {
        return Promise.resolve(this.socket);
      }
  
      // Si hay una conexión en progreso, retornar la promesa existente
      if (WebSocketService.connectionPromise) {
        return WebSocketService.connectionPromise;
      }
  
      WebSocketService.connectionPromise = new Promise((resolve, reject) => {
        try {
          // Limpiar cualquier socket existente
          if (this.socket) {
            this.socket.close();
            this.socket = null;
          }
  
          this.socket = new WebSocket(`${this.url}?token=Bearer ${this.token}`);
  
          const connectionTimeout = setTimeout(() => {
            if (this.socket?.readyState !== WebSocket.OPEN) {
              this.socket?.close();
              reject(new Error('Connection timeout'));
            }
          }, 5000);
  
          this.socket.onopen = () => {
            clearTimeout(connectionTimeout);
            WebSocketService.connectionPromise = null;
            console.log('WebSocket connected successfully');
            
            if (this.deviceId) {
              this.subscribeToDevice(this.deviceId);
            }
            
            resolve(this.socket);
          };
  
          this.socket.onmessage = (event) => {
            try {
              const data = JSON.parse(event.data);
              if (data.type === 'ESP_DATA') {
                this.notifyListeners(data.data);
              }
            } catch (error) {
              console.error('Error processing message:', error);
            }
          };
  
          this.socket.onclose = (event) => {
            console.log('WebSocket connection closed:', event.code);
            WebSocketService.connectionPromise = null;
            this.socket = null;
  
            // Reconectar solo si no fue un cierre limpio
            if (!event.wasClean) {
              clearTimeout(this.retryTimeout);
              this.retryTimeout = setTimeout(() => this.connect(), 3000);
            }
          };
  
          this.socket.onerror = (error) => {
            console.error('WebSocket error:', error);
            clearTimeout(connectionTimeout);
            WebSocketService.connectionPromise = null;
            reject(error);
          };
  
        } catch (error) {
          WebSocketService.connectionPromise = null;
          reject(error);
        }
      });
  
      return WebSocketService.connectionPromise;
    }
  
    subscribeToDevice(deviceId) {
      this.deviceId = deviceId;
  
      if (this.socket?.readyState === WebSocket.OPEN) {
        this.socket.send(JSON.stringify({
          type: 'SUBSCRIBE',
          device_id: deviceId
        }));
      }
    }
  
    addListener(callback) {
      if (typeof callback !== 'function') return;
      this.listeners.add(callback);
      return () => this.removeListener(callback);
    }
  
    removeListener(callback) {
      this.listeners.delete(callback);
    }
  
    notifyListeners(data) {
      this.listeners.forEach(callback => {
        try {
          callback(data);
        } catch (error) {
          console.error('Error in listener:', error);
        }
      });
    }
  
    disconnect() {
      clearTimeout(this.retryTimeout);
      this.listeners.clear();
      
      if (this.socket) {
        this.socket.close(1000, 'Normal closure');
        this.socket = null;
      }
  
      WebSocketService.instance = null;
      WebSocketService.connectionPromise = null;
    }
  }