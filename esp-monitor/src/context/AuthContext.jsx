import { createContext, useContext, useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [userData, setUserData] = useState(JSON.parse(localStorage.getItem('userData')));
  const navigate = useNavigate();

  const login = (tokenData, user) => {
    localStorage.setItem('token', tokenData);
    localStorage.setItem('userData', JSON.stringify(user));
    setToken(tokenData);
    setUserData(user);
    navigate('/dashboard');
  };

  const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('userData');
    setToken(null);
    setUserData(null);
    navigate('/');
  };

  return (
    <AuthContext.Provider value={{ token, userData, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);