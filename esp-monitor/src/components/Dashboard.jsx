import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Thermometer, Droplets, Menu, LogOut } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { WebSocketService } from '../services/websocket';
import { controlMotor } from '../services/api';

const DEVICE_ID = "480D3220691C";

const Dashboard = () => {
    const { token, logout } = useAuth();
    const [sensorData, setSensorData] = useState({
        temperature: '--',
        humidity: '--',
        lastUpdate: '--'
    });
    const [isMotorOn, setIsMotorOn] = useState(false);
    const [loading, setLoading] = useState(false);
    const [isMenuOpen, setIsMenuOpen] = useState(false);

    const setupWebSocket = useCallback(async () => {
        try {
            const ws = new WebSocketService('ws://192.168.1.62:8000/ws/frontend', token);

            const cleanup = ws.addListener((data) => {
                setSensorData({
                    temperature: data.temperature?.toFixed(1) || '--',
                    humidity: data.humidity?.toFixed(1) || '--',
                    lastUpdate: new Date().toLocaleTimeString()
                });
            });

            await ws.connect();
            ws.subscribeToDevice(DEVICE_ID);

            return () => {
                cleanup();
                ws.disconnect();
            };
        } catch (error) {
            console.error('Error setting up WebSocket:', error);
        }
    }, [token]);

    useEffect(() => {
        let cleanupFn;

        // Usar setTimeout para evitar la conexión inmediata
        const initTimeout = setTimeout(async () => {
            cleanupFn = await setupWebSocket();
        }, 100);

        return () => {
            clearTimeout(initTimeout);
            if (cleanupFn) cleanupFn();
        };
    }, [setupWebSocket]);

    const handleMotorToggle = async () => {
        setLoading(true);
        try {
            await controlMotor(
                DEVICE_ID, isMotorOn ? 'STOP_MOTOR' : 'START_MOTOR',
                token
            );
            setIsMotorOn(!isMotorOn);
        } catch (error) {
            console.error('Error controlando motor:', error);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-gray-100">
            {/* Header fijo */}
            <div className="fixed top-0 left-0 right-0 bg-white shadow-sm z-50">
                <div className="flex items-center justify-between p-4">
                    <h1 className="text-xl font-bold">ESP Monitor</h1>
                    <button
                        onClick={() => setIsMenuOpen(!isMenuOpen)}
                        className="p-2 rounded-full hover:bg-gray-100"
                    >
                        <Menu className="h-6 w-6" />
                    </button>
                </div>

                {/* Menú desplegable */}
                {isMenuOpen && (
                    <div className="absolute top-full right-0 w-48 bg-white shadow-lg rounded-lg py-2 mt-1">
                        <button
                            onClick={logout}
                            className="w-full px-4 py-2 text-left flex items-center space-x-2 hover:bg-gray-100"
                        >
                            <LogOut className="h-4 w-4" />
                            <span>Cerrar Sesión</span>
                        </button>
                    </div>
                )}
            </div>

            {/* Contenido principal con padding superior para el header */}
            <div className="pt-20 px-4 pb-4 space-y-4">
                {/* Tarjetas de sensores */}
                <div className="grid grid-cols-1 gap-4 mb-6">
                    {/* Temperature Card */}
                    <Card className="touch-pan-x">
                        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                            <CardTitle className="text-sm font-medium">Temperatura</CardTitle>
                            <Thermometer className="h-4 w-4 text-gray-500" />
                        </CardHeader>
                        <CardContent>
                            <div className="text-4xl font-bold text-center py-4">
                                {sensorData.temperature}°C
                            </div>
                            <p className="text-xs text-gray-500 text-center">
                                Última actualización: {sensorData.lastUpdate}
                            </p>
                        </CardContent>
                    </Card>

                    {/* Humidity Card */}
                    <Card className="touch-pan-x">
                        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                            <CardTitle className="text-sm font-medium">Humedad</CardTitle>
                            <Droplets className="h-4 w-4 text-gray-500" />
                        </CardHeader>
                        <CardContent>
                            <div className="text-4xl font-bold text-center py-4">
                                {sensorData.humidity}%
                            </div>
                            <p className="text-xs text-gray-500 text-center">
                                Última actualización: {sensorData.lastUpdate}
                            </p>
                        </CardContent>
                    </Card>
                </div>

                {/* Control de Motor */}
                <Card className="touch-pan-x">
                    <CardHeader>
                        <CardTitle>Control de Motor</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-6">
                            <div className="flex items-center justify-between">
                                <span className="text-sm font-medium">Estado del Motor</span>
                                <Switch
                                    checked={isMotorOn}
                                    onCheckedChange={handleMotorToggle}
                                    disabled={loading}
                                    className="scale-125"
                                />
                            </div>

                            <Button
                                className="w-full py-6 text-lg"
                                variant={isMotorOn ? "destructive" : "default"}
                                onClick={handleMotorToggle}
                                disabled={loading}
                            >
                                {loading ? "Procesando..." : isMotorOn ? "Detener Motor" : "Iniciar Motor"}
                            </Button>
                        </div>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
};

export default Dashboard;