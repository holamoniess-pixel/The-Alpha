import React, { useState, useEffect } from 'react';
import {
  Box,
  TextField,
  Button,
  Typography,
  Alert,
} from '@mui/material';
import { Security, Lock, Shield } from '@mui/icons-material';

interface LoginProps {
  onLogin: (userData: any) => void;
}

const LoginPage: React.FC<LoginProps> = ({ onLogin }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [mounted, setMounted] = useState(false);
  const [particles, setParticles] = useState<Array<{ x: number; y: number; vx: number; vy: number }>>([]);

  useEffect(() => {
    setMounted(true);
    const newParticles = Array.from({ length: 50 }, () => ({
      x: Math.random() * 100,
      y: Math.random() * 100,
      vx: (Math.random() - 0.5) * 0.5,
      vy: (Math.random() - 0.5) * 0.5,
    }));
    setParticles(newParticles);
    
    const interval = setInterval(() => {
      setParticles(prev => prev.map(p => ({
        ...p,
        x: (p.x + p.vx + 100) % 100,
        y: (p.y + p.vy + 100) % 100,
      })));
    }, 50);
    
    return () => clearInterval(interval);
  }, []);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const response = await fetch('/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: username,
          password: password
        }),
      });

      if (response.ok) {
        const data = await response.json();
        localStorage.setItem('token', data.access_token);
        onLogin({
          id: username,
          username: username,
          role: username === 'admin' ? 'admin' : 'user'
        });
      } else {
        setError('Invalid credentials');
      }
    } catch (error) {
      setError('Network error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: '#0a0a0f',
        position: 'relative',
        overflow: 'hidden',
        '&::before': {
          content: '""',
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'radial-gradient(circle at 30% 30%, rgba(0, 245, 255, 0.1) 0%, transparent 50%), radial-gradient(circle at 70% 70%, rgba(255, 0, 255, 0.1) 0%, transparent 50%)',
        }
      }}
    >
      {particles.map((p, i) => (
        <Box
          key={i}
          sx={{
            position: 'absolute',
            left: `${p.x}%`,
            top: `${p.y}%`,
            width: 2,
            height: 2,
            borderRadius: '50%',
            bgcolor: i % 2 === 0 ? '#00f5ff' : '#ff00ff',
            boxShadow: i % 2 === 0 ? '0 0 10px #00f5ff' : '0 0 10px #ff00ff',
            opacity: 0.6,
          }}
        />
      ))}

      <Box
        component="form"
        onSubmit={handleLogin}
        sx={{
          p: 5,
          width: '100%',
          maxWidth: 420,
          background: 'linear-gradient(135deg, rgba(18, 18, 26, 0.95) 0%, rgba(10, 10, 15, 0.98) 100%)',
          borderRadius: 3,
          border: '1px solid rgba(0, 245, 255, 0.3)',
          backdropFilter: 'blur(20px)',
          position: 'relative',
          overflow: 'hidden',
          opacity: mounted ? 1 : 0,
          transform: mounted ? 'translateY(0) scale(1)' : 'translateY(30px) scale(0.95)',
          transition: 'all 0.6s cubic-bezier(0.4, 0, 0.2, 1)',
          '&::before': {
            content: '""',
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            height: 3,
            background: 'linear-gradient(90deg, #00f5ff, #ff00ff, #00f5ff)',
            backgroundSize: '200% 100%',
            animation: 'gradient-shift 3s ease infinite',
          },
          '&::after': {
            content: '""',
            position: 'absolute',
            top: -50%,
            left: -50%,
            width: '200%',
            height: '200%',
            background: 'conic-gradient(from 0deg, transparent, rgba(0, 245, 255, 0.1), transparent, rgba(255, 0, 255, 0.1), transparent)',
            animation: 'rotate-hue 10s linear infinite',
            zIndex: -1,
          }
        }}
      >
        <Box display="flex" flexDirection="column" alignItems="center" mb={4}>
          <Box
            sx={{
              width: 80,
              height: 80,
              borderRadius: 3,
              background: 'linear-gradient(135deg, rgba(0, 245, 255, 0.2) 0%, rgba(255, 0, 255, 0.2) 100%)',
              border: '2px solid rgba(0, 245, 255, 0.5)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              mb: 3,
              boxShadow: '0 0 30px rgba(0, 245, 255, 0.3)',
              animation: 'float 3s ease-in-out infinite',
              position: 'relative',
              '&::before': {
                content: '""',
                position: 'absolute',
                inset: -2,
                borderRadius: 4,
                background: 'linear-gradient(45deg, #00f5ff, #ff00ff)',
                zIndex: -1,
                animation: 'glow-pulse 2s ease-in-out infinite',
              }
            }}
          >
            <Shield sx={{ fontSize: 40, color: '#00f5ff' }} />
          </Box>
          <Typography 
            variant="h3" 
            component="h1" 
            sx={{ 
              mt: 2, 
              fontFamily: 'Orbitron',
              fontWeight: 700,
              background: 'linear-gradient(90deg, #00f5ff, #ff00ff)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              letterSpacing: 4,
              animation: 'neon-fade 2s ease-in-out infinite',
            }}
          >
            RAVER
          </Typography>
          <Typography 
            variant="h6" 
            sx={{ 
              fontFamily: 'Rajdhani',
              color: 'rgba(255,255,255,0.6)',
              letterSpacing: 3,
              mt: 1,
            }}
          >
            SENTINEL
          </Typography>
          <Typography 
            variant="body2" 
            sx={{ 
              mt: 2,
              fontFamily: 'Rajdhani',
              color: 'rgba(0, 245, 255, 0.7)',
              letterSpacing: 1,
            }}
          >
            Secure AI Assistant Platform
          </Typography>
        </Box>

        <TextField
          fullWidth
          label="Username"
          variant="outlined"
          margin="normal"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          disabled={loading}
          autoFocus
          className="cyber-input"
          sx={{
            mb: 2,
            '& .MuiInputLabel-root': {
              fontFamily: 'Rajdhani',
              color: 'rgba(0, 245, 255, 0.7)',
            },
            '& .MuiOutlinedInput-root': {
              fontFamily: 'Rajdhani',
              '& fieldset': {
                borderColor: 'rgba(0, 245, 255, 0.3)',
              },
              '&:hover fieldset': {
                borderColor: 'rgba(0, 245, 255, 0.5)',
              },
              '&.Mui-focused fieldset': {
                borderColor: '#00f5ff',
                boxShadow: '0 0 15px rgba(0, 245, 255, 0.3)',
              },
            },
          }}
        />
        
        <TextField
          fullWidth
          label="Password"
          type="password"
          variant="outlined"
          margin="normal"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          disabled={loading}
          className="cyber-input"
          sx={{
            mb: 2,
            '& .MuiInputLabel-root': {
              fontFamily: 'Rajdhani',
              color: 'rgba(0, 245, 255, 0.7)',
            },
            '& .MuiOutlinedInput-root': {
              fontFamily: 'Rajdhani',
              '& fieldset': {
                borderColor: 'rgba(0, 245, 255, 0.3)',
              },
              '&:hover fieldset': {
                borderColor: 'rgba(0, 245, 255, 0.5)',
              },
              '&.Mui-focused fieldset': {
                borderColor: '#00f5ff',
                boxShadow: '0 0 15px rgba(0, 245, 255, 0.3)',
              },
            },
          }}
        />

        {error && (
          <Alert 
            severity="error" 
            sx={{ 
              mt: 2,
              bgcolor: 'rgba(255, 51, 102, 0.1)',
              border: '1px solid rgba(255, 51, 102, 0.3)',
              '& .MuiAlert-icon': {
                color: '#ff3366'
              }
            }}
          >
            <Typography sx={{ fontFamily: 'Rajdhani' }}>{error}</Typography>
          </Alert>
        )}

        <Button
          type="submit"
          fullWidth
          variant="contained"
          size="large"
          disabled={loading || !username || !password}
          sx={{ 
            mt: 3, 
            mb: 2,
            py: 1.5,
            fontFamily: 'Orbitron',
            fontWeight: 600,
            fontSize: '1rem',
            letterSpacing: 2,
            background: 'linear-gradient(90deg, #00f5ff, #ff00ff)',
            borderRadius: 2,
            position: 'relative',
            overflow: 'hidden',
            transition: 'all 0.3s ease',
            '&::before': {
              content: '""',
              position: 'absolute',
              top: 0,
              left: '-100%',
              width: '100%',
              height: '100%',
              background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent)',
              transition: 'left 0.5s ease',
            },
            '&:hover': {
              transform: 'translateY(-2px)',
              boxShadow: '0 0 30px rgba(0, 245, 255, 0.5)',
              '&::before': {
                left: '100%',
              }
            },
            '&:disabled': {
              bgcolor: 'rgba(0, 245, 255, 0.2)',
            }
          }}
          startIcon={<Lock />}
        >
          {loading ? 'AUTHENTICATING...' : 'ACCESS SYSTEM'}
        </Button>

        <Box sx={{ 
          mt: 3, 
          p: 2, 
          bgcolor: 'rgba(0, 0, 0, 0.3)', 
          borderRadius: 2,
          border: '1px solid rgba(0, 245, 255, 0.1)',
        }}>
          <Typography 
            variant="body2" 
            sx={{ 
              fontFamily: 'Rajdhani',
              color: 'rgba(255,255,255,0.5)',
              letterSpacing: 1,
              textAlign: 'center',
              mb: 1
            }}
          >
            Demo Credentials:
          </Typography>
          <Typography 
            variant="body2" 
            component="div"
            sx={{
              fontFamily: 'monospace',
              color: 'rgba(0, 245, 255, 0.7)',
              textAlign: 'center',
              '& strong': {
                color: '#00ff88'
              }
            }}
          >
            <strong>Admin:</strong> admin / admin123<br />
            <strong>User:</strong> user / user123
          </Typography>
        </Box>
      </Box>
    </Box>
  );
};

export default LoginPage;
