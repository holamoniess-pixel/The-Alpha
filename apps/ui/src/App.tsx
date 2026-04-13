import React, { useState, useEffect, createContext, useContext } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { Box, AppBar, Toolbar, Typography, IconButton, CircularProgress, Badge } from '@mui/material';
import { Security, Settings, Notifications, Refresh, Circle } from '@mui/icons-material';
import Dashboard from './pages/Dashboard';
import VaultPage from './pages/Vault';
import AuditPage from './pages/Audit';
import SettingsPage from './pages/Settings';
import LoginPage from './pages/Login';
import Navigation from './components/Navigation';

const theme = createTheme({
  palette: {
    mode: 'dark',
    primary: { main: '#00f5ff' },
    secondary: { main: '#ff00ff' },
    background: { default: '#0a0a0f', paper: '#12121a' },
    success: { main: '#00ff88' },
    warning: { main: '#ffaa00' },
    error: { main: '#ff3366' },
  },
  typography: { fontFamily: '"Orbitron", "Rajdhani", "Roboto", sans-serif' },
  components: {
    MuiCssBaseline: {
      styleOverrides: `
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;500;600;700&family=Rajdhani:wght@300;400;500;600;700&display=swap');
        
        * {
          scrollbar-width: thin;
          scrollbar-color: #00f5ff #12121a;
        }
        
        *::-webkit-scrollbar {
          width: 6px;
        }
        
        *::-webkit-scrollbar-track {
          background: #12121a;
        }
        
        *::-webkit-scrollbar-thumb {
          background: linear-gradient(180deg, #00f5ff, #ff00ff);
          border-radius: 3px;
        }
        
        @keyframes glow-pulse {
          0%, 100% { box-shadow: 0 0 5px #00f5ff, 0 0 10px #00f5ff, 0 0 15px #00f5ff; }
          50% { box-shadow: 0 0 10px #00f5ff, 0 0 20px #00f5ff, 0 0 30px #00f5ff, 0 0 40px #00f5ff; }
        }
        
        @keyframes border-flow {
          0% { background-position: 0% 50%; }
          50% { background-position: 100% 50%; }
          100% { background-position: 0% 50%; }
        }
        
        @keyframes float {
          0%, 100% { transform: translateY(0px); }
          50% { transform: translateY(-10px); }
        }
        
        @keyframes scan-line {
          0% { transform: translateY(-100%); opacity: 0; }
          10% { opacity: 0.5; }
          90% { opacity: 0.5; }
          100% { transform: translateY(100vh); opacity: 0; }
        }
        
        @keyframes flicker {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.8; }
        }
        
        @keyframes slideInLeft {
          from { transform: translateX(-100%); opacity: 0; }
          to { transform: translateX(0); opacity: 1; }
        }
        
        @keyframes slideInRight {
          from { transform: translateX(100%); opacity: 0; }
          to { transform: translateX(0); opacity: 1; }
        }
        
        @keyframes slideInUp {
          from { transform: translateY(50px); opacity: 0; }
          to { transform: translateY(0); opacity: 1; }
        }
        
        @keyframes neon-fade {
          0%, 100% { text-shadow: 0 0 10px currentColor, 0 0 20px currentColor; }
          50% { text-shadow: 0 0 20px currentColor, 0 0 30px currentColor, 0 0 40px currentColor; }
        }
        
        @keyframes border-glow {
          0%, 100% { border-color: #00f5ff; }
          50% { border-color: #ff00ff; }
        }
        
        @keyframes gradient-shift {
          0% { background-position: 0% 50%; }
          50% { background-position: 100% 50%; }
          100% { background-position: 0% 50%; }
        }
        
        @keyframes rotate-hue {
          0% { filter: hue-rotate(0deg); }
          100% { filter: hue-rotate(360deg); }
        }
        
        @keyframes typing {
          from { width: 0; }
          to { width: 100%; }
        }
        
        @keyframes blink-caret {
          50% { border-color: transparent; }
        }
        
        @keyframes pulse-ring {
          0% { transform: scale(0.8); opacity: 1; }
          100% { transform: scale(2); opacity: 0; }
        }
        
        .scan-line {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          height: 2px;
          background: linear-gradient(90deg, transparent, rgba(0, 245, 255, 0.5), transparent);
          animation: scan-line 4s linear infinite;
          pointer-events: none;
          z-index: 9999;
        }
        
        .glow-text {
          animation: neon-fade 2s ease-in-out infinite;
        }
        
        .cyber-card {
          background: linear-gradient(135deg, #12121a 0%, #1a1a2e 100%);
          border: 1px solid rgba(0, 245, 255, 0.3);
          position: relative;
          overflow: hidden;
          transition: all 0.3s ease;
        }
        
        .cyber-card::before {
          content: '';
          position: absolute;
          top: 0;
          left: -100%;
          width: 100%;
          height: 100%;
          background: linear-gradient(90deg, transparent, rgba(0, 245, 255, 0.1), transparent);
          transition: left 0.5s ease;
        }
        
        .cyber-card:hover::before {
          left: 100%;
        }
        
        .cyber-card:hover {
          border-color: #00f5ff;
          box-shadow: 0 0 20px rgba(0, 245, 255, 0.3), inset 0 0 20px rgba(0, 245, 255, 0.05);
          transform: translateY(-2px);
        }
        
        .cyber-button {
          position: relative;
          overflow: hidden;
          transition: all 0.3s ease;
        }
        
        .cyber-button::before {
          content: '';
          position: absolute;
          top: 50%;
          left: 50%;
          width: 0;
          height: 0;
          background: rgba(0, 245, 255, 0.3);
          border-radius: 50%;
          transform: translate(-50%, -50%);
          transition: all 0.5s ease;
        }
        
        .cyber-button:hover::before {
          width: 300px;
          height: 300px;
        }
        
        .cyber-input {
          background: rgba(0, 0, 0, 0.5);
          border: 1px solid rgba(0, 245, 255, 0.3);
          transition: all 0.3s ease;
        }
        
        .cyber-input:focus {
          border-color: #00f5ff;
          box-shadow: 0 0 10px rgba(0, 245, 255, 0.3), inset 0 0 10px rgba(0, 245, 255, 0.1);
        }
        
        .frame-corner {
          position: relative;
        }
        
        .frame-corner::before,
        .frame-corner::after {
          content: '';
          position: absolute;
          width: 20px;
          height: 20px;
          border-color: #00f5ff;
          border-style: solid;
        }
        
        .frame-corner::before {
          top: -1px;
          left: -1px;
          border-width: 2px 0 0 2px;
        }
        
        .frame-corner::after {
          bottom: -1px;
          right: -1px;
          border-width: 0 2px 2px 0;
        }
        
        .animate-slide-in {
          animation: slideInUp 0.5s ease-out forwards;
        }
        
        .animate-delay-1 { animation-delay: 0.1s; opacity: 0; }
        .animate-delay-2 { animation-delay: 0.2s; opacity: 0; }
        .animate-delay-3 { animation-delay: 0.3s; opacity: 0; }
        .animate-delay-4 { animation-delay: 0.4s; opacity: 0; }
        .animate-delay-5 { animation-delay: 0.5s; opacity: 0; }
      `,
    },
  },
});

interface SystemContextType {
  status: any;
  metrics: any;
  isConnected: boolean;
  sendCommand: (command: string) => Promise<any>;
  refresh: () => Promise<void>;
}

const SystemContext = createContext<SystemContextType>({
  status: null,
  metrics: null,
  isConnected: false,
  sendCommand: async () => ({}),
  refresh: async () => {},
});

export const useSystem = () => useContext(SystemContext);

const API_BASE = 'http://localhost:8000';

function AppRoutes() {
  return (
    <Routes>
      <Route path="/dashboard" element={<Dashboard />} />
      <Route path="/vault" element={<VaultPage />} />
      <Route path="/audit" element={<AuditPage />} />
      <Route path="/settings" element={<SettingsPage />} />
      <Route path="/login" element={<LoginPage onLogin={() => {}} />} />
      <Route path="/" element={<Navigate to="/dashboard" />} />
    </Routes>
  );
}

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(true);
  const [user, setUser] = useState(null);
  const [status, setStatus] = useState<any>(null);
  const [metrics, setMetrics] = useState<any>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [loading, setLoading] = useState(true);
  const [ws, setWs] = useState<WebSocket | null>(null);
  const [pulseKey, setPulseKey] = useState(0);

  const fetchStatus = async () => {
    try {
      const response = await fetch(`${API_BASE}/status`);
      if (response.ok) {
        const data = await response.json();
        setStatus(data);
        setMetrics(data.metrics);
        setIsConnected(true);
        setPulseKey(prev => prev + 1);
      }
    } catch (error) {
      setIsConnected(false);
    } finally {
      setLoading(false);
    }
  };

  const sendCommand = async (command: string) => {
    try {
      const response = await fetch(`${API_BASE}/command`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command }),
      });
      return await response.json();
    } catch (error) {
      return { success: false, message: 'Connection error' };
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 5000);
    
    const websocket = new WebSocket(`ws://localhost:8000/ws`);
    websocket.onopen = () => setIsConnected(true);
    websocket.onclose = () => setIsConnected(false);
    websocket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'status_update') {
        setMetrics(data.metrics);
        setPulseKey(prev => prev + 1);
      }
    };
    setWs(websocket);

    return () => {
      clearInterval(interval);
      websocket.close();
    };
  }, []);

  const handleLogin = (userData: any) => {
    setUser(userData);
    setIsAuthenticated(true);
  };

  const handleLogout = () => {
    setUser(null);
    setIsAuthenticated(false);
    localStorage.removeItem('token');
  };

  if (loading) {
    return (
      <Box sx={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '100vh', 
        bgcolor: '#0a0a0f',
        background: 'radial-gradient(circle at center, #12121a 0%, #0a0a0f 100%)'
      }}>
        <Box sx={{ textAlign: 'center' }}>
          <Box sx={{ position: 'relative', mb: 3 }}>
            <CircularProgress 
              size={80} 
              thickness={2}
              sx={{ 
                color: '#00f5ff',
                animation: 'glow-pulse 2s ease-in-out infinite',
              }} 
            />
            <Box sx={{
              position: 'absolute',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              animation: 'flicker 0.5s ease-in-out infinite'
            }}>
              <Security sx={{ fontSize: 30, color: '#00f5ff' }} />
            </Box>
          </Box>
          <Typography 
            sx={{ 
              mt: 2, 
              color: '#00f5ff',
              fontFamily: 'Orbitron',
              letterSpacing: 4,
              animation: 'neon-fade 1.5s ease-in-out infinite'
            }}
          >
            INITIALIZING...
          </Typography>
          <Box sx={{ mt: 2, display: 'flex', justifyContent: 'center', gap: 0.5 }}>
            {[0, 1, 2].map((i) => (
              <Box
                key={i}
                sx={{
                  width: 8,
                  height: 8,
                  borderRadius: '50%',
                  bgcolor: '#00f5ff',
                  animation: `pulse-ring 1.5s ease-out infinite`,
                  animationDelay: `${i * 0.2}s`,
                }}
              />
            ))}
          </Box>
        </Box>
      </Box>
    );
  }

  return (
    <SystemContext.Provider value={{ status, metrics, isConnected, sendCommand, refresh: fetchStatus }}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <div className="scan-line" />
        <Router>
          <Box sx={{ minHeight: '100vh', backgroundColor: '#0a0a0f', display: 'flex' }}>
            <Navigation />
            <Box sx={{ flexGrow: 1 }}>
              <AppBar 
                position="static" 
                sx={{ 
                  background: 'linear-gradient(180deg, #1a1a2e 0%, #12121a 100%)',
                  borderBottom: '1px solid rgba(0, 245, 255, 0.3)',
                  boxShadow: '0 0 20px rgba(0, 245, 255, 0.1)'
                }}
              >
                <Toolbar sx={{ position: 'relative' }}>
                  <Box sx={{ 
                    position: 'absolute',
                    left: 0,
                    top: 0,
                    bottom: 0,
                    width: 3,
                    bgcolor: '#00f5ff',
                    boxShadow: '0 0 10px #00f5ff'
                  }} />
                  <Security sx={{ mr: 2, color: '#00f5ff', filter: 'drop-shadow(0 0 5px #00f5ff)' }} />
                  <Typography 
                    variant="h6" 
                    component="div" 
                    sx={{ 
                      flexGrow: 1, 
                      fontWeight: 'bold',
                      fontFamily: 'Orbitron',
                      background: 'linear-gradient(90deg, #00f5ff, #ff00ff)',
                      WebkitBackgroundClip: 'text',
                      WebkitTextFillColor: 'transparent',
                      letterSpacing: 2
                    }}
                  >
                    ALPHA OMEGA v2.0.0
                  </Typography>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                    <Box sx={{ 
                      position: 'relative',
                      px: 2, 
                      py: 0.5, 
                      borderRadius: 1, 
                      bgcolor: 'rgba(0, 0, 0, 0.5)',
                      border: `1px solid ${isConnected ? '#00ff88' : '#ff3366'}`,
                      overflow: 'hidden',
                      '&::before': isConnected ? {
                        content: '""',
                        position: 'absolute',
                        top: 0,
                        left: '-100%',
                        width: '100%',
                        height: '100%',
                        bgcolor: 'rgba(0, 255, 136, 0.2)',
                        animation: 'slideInLeft 2s ease-in-out infinite'
                      } : {}
                    }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Circle sx={{ 
                          fontSize: 10, 
                          color: isConnected ? '#00ff88' : '#ff3366',
                          animation: isConnected ? 'glow-pulse 2s ease-in-out infinite' : 'none'
                        }} />
                        <Typography sx={{
                          fontSize: '0.7rem',
                          fontWeight: 'bold',
                          fontFamily: 'Orbitron',
                          color: isConnected ? '#00ff88' : '#ff3366',
                          letterSpacing: 1
                        }}>
                          {isConnected ? 'CONNECTED' : 'OFFLINE'}
                        </Typography>
                      </Box>
                    </Box>
                    <IconButton 
                      sx={{ 
                        color: '#00f5ff',
                        transition: 'all 0.3s ease',
                        '&:hover': { 
                          bgcolor: 'rgba(0, 245, 255, 0.1)',
                          transform: 'rotate(180deg)'
                        }
                      }} 
                      onClick={fetchStatus}
                    >
                      <Refresh />
                    </IconButton>
                    <IconButton sx={{ color: '#ff00ff' }}>
                      <Badge 
                        badgeContent={0} 
                        sx={{
                          '& .MuiBadge-badge': {
                            bgcolor: '#ff00ff',
                            animation: 'glow-pulse 2s ease-in-out infinite'
                          }
                        }}
                      >
                        <Notifications />
                      </Badge>
                    </IconButton>
                    <IconButton 
                      sx={{ 
                        color: '#00f5ff',
                        transition: 'all 0.3s ease',
                        '&:hover': { 
                          bgcolor: 'rgba(0, 245, 255, 0.1)',
                          transform: 'rotate(90deg)'
                        }
                      }} 
                      onClick={handleLogout}
                    >
                      <Settings />
                    </IconButton>
                  </Box>
                </Toolbar>
              </AppBar>
              <Box sx={{ p: 3, position: 'relative' }}>
                <AppRoutes />
              </Box>
            </Box>
          </Box>
        </Router>
      </ThemeProvider>
    </SystemContext.Provider>
  );
}

export default App;
