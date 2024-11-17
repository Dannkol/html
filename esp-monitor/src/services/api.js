const API_URL = 'http://192.168.1.62:8000';

export const login = async (credentials) => {
  const response = await fetch(`${API_URL}/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(credentials)
  });
  
  if (!response.ok) {
    throw new Error('Error en login');
  }
  
  return response.json();
};

export const register = async (userData) => {
  const response = await fetch(`${API_URL}/users/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(userData)
  });
  
  if (!response.ok) {
    throw new Error('Error en registro');
  }
  
  return response.json();
};

export const controlMotor = async (deviceId, action, token) => {
  const response = await fetch(`${API_URL}/api/esp/${deviceId}/motor`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({ action })
  });
  
  if (!response.ok) {
    throw new Error('Error controlando motor');
  }
  
  return response.json();
};