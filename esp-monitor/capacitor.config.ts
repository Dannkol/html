import { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.espmonitor.app',
  appName: 'ESP Monitor',
  webDir: 'dist',
  server: {
    androidScheme: 'https',
    // Para desarrollo, habilita live reload
    url: 'http://192.168.1.62:5173', // Cambia esto por tu IP local
    cleartext: true
  },
  android: {
    buildOptions: {
      keystorePath: undefined,
      keystoreAlias: undefined,
      keystorePassword: undefined,
      keystoreKeyPassword: undefined,
    }
  },
  plugins: {
    SplashScreen: {
      launchShowDuration: 2000,
      backgroundColor: "#FFFFFF",
      showSpinner: true,
      spinnerColor: "#3B82F6"
    }
  }
};

export default config;