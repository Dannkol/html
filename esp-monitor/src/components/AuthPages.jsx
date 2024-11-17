import React, { useState } from 'react';
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { User, Key, MapPin } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { login, register } from '../services/api';

const AuthPages = () => {
  const { login: authLogin } = useAuth();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  
  // Login form state
  const [loginData, setLoginData] = useState({
    username: "",
    password: ""
  });

  // Register form state
  const [registerData, setRegisterData] = useState({
    name: "",
    password: "",
    location: "",
    latitud: "",
    longitud: ""
  });

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    
    try {
      const data = await login(loginData);
      authLogin(data.access_token, data.user_data);
      
      // Feedback táctil en dispositivos móviles
      if ('vibrate' in navigator) {
        navigator.vibrate(100);
      }
    } catch (err) {
      setError(err.message);
      if ('vibrate' in navigator) {
        navigator.vibrate([50, 100, 50]);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    
    try {
      const registerPayload = {
        ...registerData,
        latitud: registerData.latitud ? parseFloat(registerData.latitud) : null,
        longitud: registerData.longitud ? parseFloat(registerData.longitud) : null
      };
      
      await register(registerPayload);
      
      // Auto-login después del registro
      const loginResponse = await login({
        username: registerData.name,
        password: registerData.password
      });
      
      authLogin(loginResponse.access_token, loginResponse.user_data);
      
      if ('vibrate' in navigator) {
        navigator.vibrate(100);
      }
    } catch (err) {
      setError(err.message);
      if ('vibrate' in navigator) {
        navigator.vibrate([50, 100, 50]);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 p-4 flex items-center justify-center">
      <Tabs defaultValue="login" className="w-full max-w-md">
        <TabsList className="grid w-full grid-cols-2 mb-4">
          <TabsTrigger value="login" className="text-lg py-3">Iniciar Sesión</TabsTrigger>
          <TabsTrigger value="register" className="text-lg py-3">Registrarse</TabsTrigger>
        </TabsList>
        
        {/* Login Tab */}
        <TabsContent value="login">
          <Card>
            <CardHeader>
              <CardTitle>Iniciar Sesión</CardTitle>
              <CardDescription>
                Ingresa tus credenciales para acceder al sistema
              </CardDescription>
            </CardHeader>
            <form onSubmit={handleLogin}>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <div className="relative">
                    <User className="absolute left-3 top-3 h-5 w-5 text-gray-500" />
                    <Input
                      className="pl-10 py-6 text-lg"
                      placeholder="Nombre de usuario"
                      value={loginData.username}
                      onChange={(e) => setLoginData({...loginData, username: e.target.value})}
                      required
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <div className="relative">
                    <Key className="absolute left-3 top-3 h-5 w-5 text-gray-500" />
                    <Input
                      className="pl-10 py-6 text-lg"
                      type="password"
                      placeholder="Contraseña"
                      value={loginData.password}
                      onChange={(e) => setLoginData({...loginData, password: e.target.value})}
                      required
                    />
                  </div>
                </div>
              </CardContent>
              <CardFooter>
                <Button className="w-full py-6 text-lg" type="submit" disabled={loading}>
                  {loading ? "Cargando..." : "Iniciar Sesión"}
                </Button>
              </CardFooter>
            </form>
          </Card>
        </TabsContent>
        
        {/* Register Tab */}
        <TabsContent value="register">
          <Card>
            <CardHeader>
              <CardTitle>Registro</CardTitle>
              <CardDescription>
                Crea una nueva cuenta en el sistema
              </CardDescription>
            </CardHeader>
            <form onSubmit={handleRegister}>
              <CardContent className="space-y-4">
                <div className="relative">
                  <User className="absolute left-3 top-3 h-5 w-5 text-gray-500" />
                  <Input
                    className="pl-10 py-6 text-lg"
                    placeholder="Nombre de usuario"
                    value={registerData.name}
                    onChange={(e) => setRegisterData({...registerData, name: e.target.value})}
                    required
                  />
                </div>
                <div className="relative">
                  <Key className="absolute left-3 top-3 h-5 w-5 text-gray-500" />
                  <Input
                    className="pl-10 py-6 text-lg"
                    type="password"
                    placeholder="Contraseña"
                    value={registerData.password}
                    onChange={(e) => setRegisterData({...registerData, password: e.target.value})}
                    required
                  />
                </div>
                <div className="relative">
                  <MapPin className="absolute left-3 top-3 h-5 w-5 text-gray-500" />
                  <Input
                    className="pl-10 py-6 text-lg"
                    placeholder="Ubicación"
                    value={registerData.location}
                    onChange={(e) => setRegisterData({...registerData, location: e.target.value})}
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <Input
                    className="py-6 text-lg"
                    type="number"
                    step="any"
                    placeholder="Latitud"
                    value={registerData.latitud}
                    onChange={(e) => setRegisterData({...registerData, latitud: e.target.value})}
                  />
                  <Input
                    className="py-6 text-lg"
                    type="number"
                    step="any"
                    placeholder="Longitud"
                    value={registerData.longitud}
                    onChange={(e) => setRegisterData({...registerData, longitud: e.target.value})}
                  />
                </div>
              </CardContent>
              <CardFooter>
                <Button className="w-full py-6 text-lg" type="submit" disabled={loading}>
                  {loading ? "Cargando..." : "Registrarse"}
                </Button>
              </CardFooter>
            </form>
          </Card>
        </TabsContent>

        {/* Error Alert */}
        {error && (
          <Alert variant="destructive" className="mt-4">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
      </Tabs>
    </div>
  );
};

export default AuthPages;