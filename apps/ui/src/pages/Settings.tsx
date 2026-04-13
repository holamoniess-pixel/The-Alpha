import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Switch,
  FormControlLabel,
  TextField,
  Button,
  Alert,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Chip
} from '@mui/material';
import { Settings as SettingsIcon, Security, Notifications as BellIcon, Shield, Person } from '@mui/icons-material';

interface SettingsState {
  notifications: {
    enabled: boolean;
    approvals: boolean;
    security: boolean;
    system: boolean;
  };
  security: {
    requireApproval: boolean;
    autoLock: boolean;
    sessionTimeout: number;
  };
  user: {
    username: string;
    email: string;
    role: string;
  };
}

const SettingsPage: React.FC = () => {
  const [settings, setSettings] = useState<SettingsState>({
    notifications: {
      enabled: true,
      approvals: true,
      security: true,
      system: false
    },
    security: {
      requireApproval: true,
      autoLock: true,
      sessionTimeout: 30
    },
    user: {
      username: 'demo-user',
      email: 'demo@raver.local',
      role: 'user'
    }
  });
  
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const handleNotificationChange = (key: keyof SettingsState['notifications']) => {
    setSettings(prev => ({
      ...prev,
      notifications: {
        ...prev.notifications,
        [key]: !prev.notifications[key]
      }
    }));
  };

  const handleSecurityChange = (key: keyof SettingsState['security'], value: any) => {
    setSettings(prev => ({
      ...prev,
      security: {
        ...prev.security,
        [key]: value
      }
    }));
  };

  const handleUserChange = (key: keyof SettingsState['user'], value: string) => {
    setSettings(prev => ({
      ...prev,
      user: {
        ...prev.user,
        [key]: value
      }
    }));
  };

  const handleSaveSettings = async () => {
    try {
      localStorage.setItem('raver-settings', JSON.stringify(settings));
      setSaveMessage('Settings saved successfully');
      setTimeout(() => setSaveMessage(null), 3000);
    } catch (error) {
      setSaveMessage('Failed to save settings');
      setTimeout(() => setSaveMessage(null), 3000);
    }
  };

  const getRoleColor = (role: string) => {
    switch (role) {
      case 'admin': return '#ff3366';
      case 'user': return '#00f5ff';
      case 'guest': return '#888';
      default: return '#888';
    }
  };

  const SettingsCard = ({ icon, title, color, children, delay }: { icon: React.ReactNode, title: string, color: string, children: React.ReactNode, delay: number }) => (
    <Card 
      className="cyber-card"
      sx={{ 
        mb: 3,
        opacity: mounted ? 1 : 0,
        transform: mounted ? 'translateY(0)' : 'translateY(20px)',
        transition: `all 0.5s ease ${delay}s`
      }}
    >
      <CardContent>
        <Box display="flex" alignItems="center" mb={3}>
          <Box sx={{
            width: 40,
            height: 40,
            borderRadius: 2,
            bgcolor: `${color}20`,
            border: `1px solid ${color}`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            mr: 2,
            boxShadow: `0 0 15px ${color}40`
          }}>
            {icon}
          </Box>
          <Typography 
            variant="h6" 
            sx={{ 
              fontFamily: 'Rajdhani',
              fontWeight: 600,
              color: color,
              letterSpacing: 2
            }}
          >
            {title}
          </Typography>
        </Box>
        {children}
      </CardContent>
    </Card>
  );

  const SettingRow = ({ label, children }: { label: string; children: React.ReactNode }) => (
    <Box sx={{ 
      display: 'flex', 
      alignItems: 'center', 
      justifyContent: 'space-between',
      py: 1.5,
      borderBottom: '1px solid rgba(0, 245, 255, 0.1)',
      '&:last-child': { borderBottom: 'none' }
    }}>
      <Typography sx={{ fontFamily: 'Rajdhani', color: 'rgba(255,255,255,0.8)' }}>
        {label}
      </Typography>
      {children}
    </Box>
  );

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
            background: 'linear-gradient(90deg, #00f5ff, #00ff88)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            letterSpacing: 4
          }}
        >
          SETTINGS
        </Typography>
        <Box sx={{
          flex: 1,
          height: 2,
          background: 'linear-gradient(90deg, rgba(0, 245, 255, 0.5), transparent)'
        }} />
      </Box>

      {saveMessage && (
        <Alert 
          severity={saveMessage.includes('success') ? 'success' : 'error'} 
          sx={{ 
            mb: 2,
            bgcolor: saveMessage.includes('success') ? 'rgba(0, 255, 136, 0.1)' : 'rgba(255, 51, 102, 0.1)',
            border: `1px solid ${saveMessage.includes('success') ? '#00ff88' : '#ff3366'}`,
            animation: 'slideInUp 0.3s ease',
            '& .MuiAlert-icon': {
              color: saveMessage.includes('success') ? '#00ff88' : '#ff3366'
            }
          }}
        >
          <Typography sx={{ fontFamily: 'Rajdhani' }}>{saveMessage}</Typography>
        </Alert>
      )}

      <SettingsCard icon={<Person sx={{ color: '#00f5ff' }} />} title="USER PROFILE" color="#00f5ff" delay={0.1}>
        <Box display="flex" flexDirection="column" gap={2}>
          <TextField
            label="Username"
            value={settings.user.username}
            onChange={(e) => handleUserChange('username', e.target.value)}
            disabled
            className="cyber-input"
            sx={{
              '& .MuiInputLabel-root': { fontFamily: 'Rajdhani', color: 'rgba(0, 245, 255, 0.7)' },
              '& .MuiOutlinedInput-root': { fontFamily: 'Rajdhani' }
            }}
          />
          
          <TextField
            label="Email"
            value={settings.user.email}
            onChange={(e) => handleUserChange('email', e.target.value)}
            className="cyber-input"
            sx={{
              '& .MuiInputLabel-root': { fontFamily: 'Rajdhani', color: 'rgba(0, 245, 255, 0.7)' },
              '& .MuiOutlinedInput-root': { fontFamily: 'Rajdhani' }
            }}
          />
          
          <SettingRow label="Access Level">
            <Chip 
              label={settings.user.role.toUpperCase()} 
              size="small"
              sx={{
                fontFamily: 'Orbitron',
                fontWeight: 600,
                bgcolor: `${getRoleColor(settings.user.role)}20`,
                color: getRoleColor(settings.user.role),
                border: `1px solid ${getRoleColor(settings.user.role)}`,
                boxShadow: `0 0 10px ${getRoleColor(settings.user.role)}40`
              }}
            />
          </SettingRow>
        </Box>
      </SettingsCard>

      <SettingsCard icon={<Security sx={{ color: '#ff3366' }} />} title="SECURITY CONFIG" color="#ff3366" delay={0.2}>
        <Box display="flex" flexDirection="column" gap={1}>
          <SettingRow label="Require approval for high-risk actions">
            <Switch
              checked={settings.security.requireApproval}
              onChange={() => handleSecurityChange('requireApproval', !settings.security.requireApproval)}
              sx={{
                '& .MuiSwitch-switchBase.Mui-checked': {
                  color: '#ff3366',
                },
                '& .MuiSwitch-switchBase.Mui-checked + .MuiSwitch-track': {
                  bgcolor: '#ff3366',
                },
              }}
            />
          </SettingRow>
          
          <SettingRow label="Auto-lock vault after inactivity">
            <Switch
              checked={settings.security.autoLock}
              onChange={() => handleSecurityChange('autoLock', !settings.security.autoLock)}
              sx={{
                '& .MuiSwitch-switchBase.Mui-checked': {
                  color: '#ff3366',
                },
                '& .MuiSwitch-switchBase.Mui-checked + .MuiSwitch-track': {
                  bgcolor: '#ff3366',
                },
              }}
            />
          </SettingRow>
          
          <SettingRow label="Session Timeout">
            <FormControl size="small" sx={{ minWidth: 150 }}>
              <Select
                value={settings.security.sessionTimeout}
                onChange={(e) => handleSecurityChange('sessionTimeout', e.target.value)}
                sx={{
                  fontFamily: 'Rajdhani',
                  color: '#00f5ff',
                  '& .MuiOutlinedInput-notchedOutline': {
                    borderColor: 'rgba(0, 245, 255, 0.3)'
                  },
                  '&:hover .MuiOutlinedInput-notchedOutline': {
                    borderColor: 'rgba(0, 245, 255, 0.5)'
                  }
                }}
              >
                <MenuItem value={15} sx={{ fontFamily: 'Rajdhani' }}>15 minutes</MenuItem>
                <MenuItem value={30} sx={{ fontFamily: 'Rajdhani' }}>30 minutes</MenuItem>
                <MenuItem value={60} sx={{ fontFamily: 'Rajdhani' }}>1 hour</MenuItem>
                <MenuItem value={120} sx={{ fontFamily: 'Rajdhani' }}>2 hours</MenuItem>
              </Select>
            </FormControl>
          </SettingRow>
        </Box>
      </SettingsCard>

      <SettingsCard icon={<BellIcon sx={{ color: '#ffaa00' }} />} title="NOTIFICATIONS" color="#ffaa00" delay={0.3}>
        <Box display="flex" flexDirection="column" gap={1}>
          <SettingRow label="Enable notifications">
            <Switch
              checked={settings.notifications.enabled}
              onChange={() => handleNotificationChange('enabled')}
              sx={{
                '& .MuiSwitch-switchBase.Mui-checked': {
                  color: '#ffaa00',
                },
                '& .MuiSwitch-switchBase.Mui-checked + .MuiSwitch-track': {
                  bgcolor: '#ffaa00',
                },
              }}
            />
          </SettingRow>
          
          <SettingRow label="Approval requests">
            <Switch
              checked={settings.notifications.approvals}
              onChange={() => handleNotificationChange('approvals')}
              disabled={!settings.notifications.enabled}
              sx={{
                '& .MuiSwitch-switchBase.Mui-checked': {
                  color: '#ffaa00',
                },
                '& .MuiSwitch-switchBase.Mui-checked + .MuiSwitch-track': {
                  bgcolor: '#ffaa00',
                },
              }}
            />
          </SettingRow>
          
          <SettingRow label="Security alerts">
            <Switch
              checked={settings.notifications.security}
              onChange={() => handleNotificationChange('security')}
              disabled={!settings.notifications.enabled}
              sx={{
                '& .MuiSwitch-switchBase.Mui-checked': {
                  color: '#ffaa00',
                },
                '& .MuiSwitch-switchBase.Mui-checked + .MuiSwitch-track': {
                  bgcolor: '#ffaa00',
                },
              }}
            />
          </SettingRow>
          
          <SettingRow label="System status changes">
            <Switch
              checked={settings.notifications.system}
              onChange={() => handleNotificationChange('system')}
              disabled={!settings.notifications.enabled}
              sx={{
                '& .MuiSwitch-switchBase.Mui-checked': {
                  color: '#ffaa00',
                },
                '& .MuiSwitch-switchBase.Mui-checked + .MuiSwitch-track': {
                  bgcolor: '#ffaa00',
                },
              }}
            />
          </SettingRow>
        </Box>
      </SettingsCard>

      <SettingsCard icon={<Shield sx={{ color: '#ff00ff' }} />} title="SYSTEM CONFIG" color="#ff00ff" delay={0.4}>
        <Box display="flex" flexDirection="column" gap={2}>
          <Typography 
            variant="body2" 
            sx={{ 
              fontFamily: 'Rajdhani',
              color: 'rgba(255,255,255,0.5)',
              p: 2,
              bgcolor: 'rgba(0, 0, 0, 0.3)',
              borderRadius: 1,
              border: '1px solid rgba(255, 0, 255, 0.2)'
            }}
          >
            System-wide settings require administrator privileges.
          </Typography>
          
          <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
            <Button 
              variant="outlined" 
              disabled
              sx={{
                fontFamily: 'Rajdhani',
                borderColor: 'rgba(255, 0, 255, 0.3)',
                color: 'rgba(255, 255, 255, 0.3)'
              }}
            >
              Configure Policy Engine
            </Button>
            
            <Button 
              variant="outlined" 
              disabled
              sx={{
                fontFamily: 'Rajdhani',
                borderColor: 'rgba(255, 0, 255, 0.3)',
                color: 'rgba(255, 255, 255, 0.3)'
              }}
            >
              Manage User Roles
            </Button>
            
            <Button 
              variant="outlined" 
              disabled
              sx={{
                fontFamily: 'Rajdhani',
                borderColor: 'rgba(255, 0, 255, 0.3)',
                color: 'rgba(255, 255, 255, 0.3)'
              }}
            >
              System Diagnostics
            </Button>
          </Box>
        </Box>
      </SettingsCard>

      <Box display="flex" justifyContent="flex-end" sx={{ mt: 3 }}>
        <Button
          variant="contained"
          startIcon={<SettingsIcon />}
          onClick={handleSaveSettings}
          sx={{
            fontFamily: 'Orbitron',
            fontWeight: 600,
            fontSize: '0.9rem',
            letterSpacing: 2,
            px: 4,
            py: 1.5,
            background: 'linear-gradient(90deg, #00f5ff, #ff00ff)',
            borderRadius: 2,
            position: 'relative',
            overflow: 'hidden',
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
            }
          }}
        >
          SAVE CONFIGURATION
        </Button>
      </Box>
    </Box>
  );
};

export default SettingsPage;
