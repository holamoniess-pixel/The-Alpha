import React, { useState, useEffect } from 'react';
import {
  Box, Grid, Card, CardContent, Typography, Button, TextField, Paper,
  CircularProgress, Chip, List, ListItem,
  ListItemText, IconButton, Alert
} from '@mui/material';
import {
  Send, Security, Activity, Shield, Speed, Terminal,
  Settings, Mic, Storage, Brain, Eye, Lock
} from '@mui/icons-material';
import { useSystem } from '../App';

const Dashboard: React.FC = () => {
  const { status, metrics, isConnected, sendCommand, refresh } = useSystem();
  const [command, setCommand] = useState('');
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<any>(null);
  const [commandHistory, setCommandHistory] = useState<string[]>([]);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    refresh();
    const interval = setInterval(refresh, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleSendCommand = async () => {
    if (!command.trim()) return;
    
    setLoading(true);
    setCommandHistory(prev => [command, ...prev.slice(0, 9)]);
    
    const result = await sendCommand(command);
    setResponse(result);
    setCommand('');
    setLoading(false);
  };

  const handleQuickCommand = (cmd: string) => {
    setCommand(cmd);
  };

  const statsCards = [
    { title: 'Commands', value: metrics?.commands_total || 0, icon: <Terminal />, color: '#00f5ff', delay: 0 },
    { title: 'Success Rate', value: `${metrics?.success_rate?.toFixed(1) || 0}%`, icon: <Speed />, color: '#00ff88', delay: 1 },
    { title: 'Avg Response', value: `${metrics?.avg_response_ms?.toFixed(0) || 0}ms`, icon: <Activity />, color: '#ffaa00', delay: 2 },
    { title: 'Uptime', value: metrics?.uptime_formatted || '0:00:00', icon: <Shield />, color: '#ff00ff', delay: 3 },
  ];

  const componentCards = [
    { name: 'Voice', icon: <Mic />, status: status?.components?.voice?.status === 'active' },
    { name: 'Intelligence', icon: <Brain />, status: status?.components?.intelligence?.status === 'active' },
    { name: 'Automation', icon: <Settings />, status: status?.components?.automation?.status === 'active' },
    { name: 'Learning', icon: <Activity />, status: status?.components?.learning?.status === 'active' },
    { name: 'Memory', icon: <Storage />, status: status?.components?.memory?.status === 'active' },
    { name: 'Security', icon: <Security />, status: status?.components?.security?.status === 'active' },
    { name: 'Vault', icon: <Lock />, status: status?.components?.vault?.status === 'active' },
    { name: 'Vision', icon: <Eye />, status: status?.components?.vision?.status === 'active' },
  ];

  const quickCommands = [
    { label: 'Status', command: 'status' },
    { label: 'Screenshot', command: 'screenshot' },
    { label: 'System Info', command: 'system info' },
    { label: 'Open Chrome', command: 'open chrome' },
    { label: 'Volume 50%', command: 'volume 50' },
    { label: 'IP Address', command: 'ip' },
  ];

  return (
    <Box sx={{ flexGrow: 1, ml: '260px', p: 3 }}>
      <Box sx={{ 
        display: 'flex', 
        alignItems: 'center', 
        gap: 2,
        mb: 4,
        opacity: mounted ? 1 : 0,
        transform: mounted ? 'translateY(0)' : 'translateY(-20px)',
        transition: 'all 0.5s ease'
      }}>
        <Typography 
          variant="h3" 
          sx={{ 
            fontFamily: 'Orbitron',
            fontWeight: 700,
            background: 'linear-gradient(90deg, #00f5ff, #ff00ff)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            letterSpacing: 4
          }}
        >
          DASHBOARD
        </Typography>
        <Box sx={{
          flex: 1,
          height: 2,
          background: 'linear-gradient(90deg, rgba(0, 245, 255, 0.5), transparent)'
        }} />
      </Box>

      <Grid container spacing={3}>
        {statsCards.map((stat, index) => (
          <Grid item xs={12} sm={6} md={3} key={index}>
            <Card 
              className="cyber-card"
              sx={{ 
                opacity: mounted ? 1 : 0,
                transform: mounted ? 'translateY(0)' : 'translateY(30px)',
                transition: `all 0.5s ease ${stat.delay * 0.1}s`,
                position: 'relative',
                overflow: 'hidden',
                '&::before': {
                  content: '""',
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  right: 0,
                  height: 3,
                  background: `linear-gradient(90deg, ${stat.color}, transparent)`
                }
              }}
            >
              <CardContent sx={{ position: 'relative' }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <Box>
                    <Typography 
                      sx={{ 
                        fontFamily: 'Rajdhani',
                        fontSize: '0.8rem',
                        color: 'rgba(255,255,255,0.5)',
                        letterSpacing: 2,
                        fontWeight: 600
                      }}
                    >
                      {stat.title.toUpperCase()}
                    </Typography>
                    <Typography 
                      variant="h4" 
                      sx={{ 
                        mt: 1, 
                        fontFamily: 'Orbitron',
                        fontWeight: 700,
                        color: stat.color,
                        textShadow: `0 0 10px ${stat.color}`,
                        animation: 'neon-fade 2s ease-in-out infinite'
                      }}
                    >
                      {stat.value}
                    </Typography>
                  </Box>
                  <Box sx={{ 
                    color: stat.color,
                    animation: 'float 3s ease-in-out infinite',
                    animationDelay: `${index * 0.2}s`
                  }}>
                    {stat.icon}
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}

        <Grid item xs={12}>
          <Card 
            className="cyber-card"
            sx={{ 
              opacity: mounted ? 1 : 0,
              transform: mounted ? 'translateY(0)' : 'translateY(30px)',
              transition: 'all 0.5s ease 0.4s'
            }}
          >
            <CardContent>
              <Typography 
                variant="h6" 
                sx={{ 
                  mb: 2,
                  fontFamily: 'Rajdhani',
                  fontWeight: 600,
                  color: '#00f5ff',
                  letterSpacing: 2,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 1
                }}
              >
                <Box sx={{
                  width: 8,
                  height: 8,
                  borderRadius: '50%',
                  bgcolor: '#00f5ff',
                  boxShadow: '0 0 10px #00f5ff',
                  animation: 'glow-pulse 2s ease-in-out infinite'
                }} />
                SYSTEM COMPONENTS
              </Typography>
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                {componentCards.map((comp, index) => (
                  <Chip
                    key={index}
                    icon={comp.icon}
                    label={comp.name}
                    color={comp.status ? 'success' : 'error'}
                    variant="outlined"
                    sx={{ 
                      m: 0.5,
                      fontFamily: 'Rajdhani',
                      fontWeight: 600,
                      borderWidth: 2,
                      animation: mounted ? `slideInUp 0.3s ease ${0.5 + index * 0.05}s both` : 'none',
                      '& .MuiChip-icon': {
                        animation: comp.status ? 'glow-pulse 2s ease-in-out infinite' : 'none'
                      }
                    }}
                  />
                ))}
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={8}>
          <Card 
            className="cyber-card"
            sx={{ 
              opacity: mounted ? 1 : 0,
              transform: mounted ? 'translateY(0)' : 'translateY(30px)',
              transition: 'all 0.5s ease 0.5s',
              height: '100%'
            }}
          >
            <CardContent>
              <Typography 
                variant="h6" 
                sx={{ 
                  mb: 2,
                  fontFamily: 'Rajdhani',
                  fontWeight: 600,
                  color: '#ff00ff',
                  letterSpacing: 2,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 1
                }}
              >
                <Terminal sx={{ fontSize: 20 }} />
                COMMAND INTERFACE
              </Typography>
              
              <TextField
                fullWidth
                placeholder="Enter command... (e.g., 'open chrome', 'type hello', 'screenshot')"
                value={command}
                onChange={(e) => setCommand(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSendCommand()}
                disabled={!isConnected || loading}
                className="cyber-input"
                sx={{ 
                  mb: 2,
                  '& .MuiOutlinedInput-root': { 
                    bgcolor: 'rgba(0, 0, 0, 0.5)',
                    fontFamily: 'Rajdhani',
                    '& fieldset': {
                      borderColor: 'rgba(0, 245, 255, 0.3)'
                    }
                  }
                }}
                InputProps={{
                  endAdornment: (
                    <IconButton 
                      onClick={handleSendCommand} 
                      disabled={!isConnected || loading}
                      sx={{ 
                        color: '#00f5ff',
                        '&:hover': { bgcolor: 'rgba(0, 245, 255, 0.2)' }
                      }}
                    >
                      {loading ? <CircularProgress size={24} sx={{ color: '#00f5ff' }} /> : <Send />}
                    </IconButton>
                  )
                }}
              />

              <Typography 
                variant="body2" 
                sx={{ 
                  mb: 1,
                  fontFamily: 'Rajdhani',
                  color: 'rgba(255,255,255,0.5)',
                  letterSpacing: 1
                }}
              >
                Quick Commands:
              </Typography>
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 2 }}>
                {quickCommands.map((cmd, index) => (
                  <Button
                    key={index}
                    size="small"
                    variant="outlined"
                    onClick={() => handleQuickCommand(cmd.command)}
                    disabled={!isConnected}
                    sx={{
                      fontFamily: 'Rajdhani',
                      borderColor: 'rgba(0, 245, 255, 0.3)',
                      color: '#00f5ff',
                      '&:hover': {
                        borderColor: '#00f5ff',
                        bgcolor: 'rgba(0, 245, 255, 0.1)',
                        boxShadow: '0 0 15px rgba(0, 245, 255, 0.3)'
                      }
                    }}
                  >
                    {cmd.label}
                  </Button>
                ))}
              </Box>

              {response && (
                <Paper 
                  sx={{ 
                    p: 2, 
                    bgcolor: 'rgba(0, 0, 0, 0.5)',
                    mt: 2,
                    border: `1px solid ${response.success ? '#00ff88' : '#ff3366'}`,
                    animation: 'slideInUp 0.3s ease'
                  }}
                >
                  <Typography 
                    variant="body2" 
                    sx={{ 
                      fontFamily: 'Rajdhani',
                      color: response.success ? '#00ff88' : '#ff3366',
                      display: 'flex',
                      alignItems: 'center',
                      gap: 1
                    }}
                  >
                    <Box sx={{
                      width: 8,
                      height: 8,
                      borderRadius: '50%',
                      bgcolor: response.success ? '#00ff88' : '#ff3366',
                      boxShadow: `0 0 10px ${response.success ? '#00ff88' : '#ff3366'}`
                    }} />
                    {response.message}
                  </Typography>
                  {response.data && (
                    <Typography 
                      variant="body2" 
                      sx={{ 
                        mt: 1, 
                        whiteSpace: 'pre-wrap', 
                        fontFamily: 'monospace',
                        color: 'rgba(255,255,255,0.7)'
                      }}
                    >
                      {JSON.stringify(response.data, null, 2)}
                    </Typography>
                  )}
                </Paper>
              )}
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={4}>
          <Card 
            className="cyber-card"
            sx={{ 
              opacity: mounted ? 1 : 0,
              transform: mounted ? 'translateY(0)' : 'translateY(30px)',
              transition: 'all 0.5s ease 0.6s',
              height: '100%'
            }}
          >
            <CardContent>
              <Typography 
                variant="h6" 
                sx={{ 
                  mb: 2,
                  fontFamily: 'Rajdhani',
                  fontWeight: 600,
                  color: '#ffaa00',
                  letterSpacing: 2,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 1
                }}
              >
                <Activity sx={{ fontSize: 20 }} />
                RECENT COMMANDS
              </Typography>
              
              {commandHistory.length > 0 ? (
                <List dense>
                  {commandHistory.map((cmd, index) => (
                    <ListItem 
                      key={index} 
                      sx={{ 
                        px: 0,
                        animation: `slideInRight 0.3s ease ${index * 0.05}s both`
                      }}
                    >
                      <Box sx={{
                        width: 4,
                        height: 4,
                        borderRadius: '50%',
                        bgcolor: '#00f5ff',
                        mr: 1
                      }} />
                      <ListItemText
                        primary={cmd}
                        primaryTypographyProps={{ 
                          variant: 'body2', 
                          fontFamily: 'monospace',
                          color: 'rgba(255,255,255,0.8)'
                        }}
                      />
                    </ListItem>
                  ))}
                </List>
              ) : (
                <Typography 
                  variant="body2" 
                  sx={{ 
                    fontFamily: 'Rajdhani',
                    color: 'rgba(255,255,255,0.4)',
                    textAlign: 'center',
                    py: 4
                  }}
                >
                  No commands yet. Start by entering a command above.
                </Typography>
              )}
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12}>
          <Alert 
            severity="info" 
            sx={{ 
              bgcolor: 'rgba(0, 245, 255, 0.1)',
              border: '1px solid rgba(0, 245, 255, 0.3)',
              borderRadius: 2,
              animation: 'slideInUp 0.5s ease 0.7s both',
              '& .MuiAlert-icon': {
                color: '#00f5ff'
              }
            }}
          >
            <Typography sx={{ fontFamily: 'Rajdhani' }}>
              <strong style={{ color: '#00f5ff' }}>TIP:</strong> Say "{status?.wake_word || 'hey alpha'}" to activate voice control, 
              or type commands directly. The system supports 200+ automation features including 
              app control, file operations, web browsing, and more.
            </Typography>
          </Alert>
        </Grid>
      </Grid>
    </Box>
  );
};

export default Dashboard;
