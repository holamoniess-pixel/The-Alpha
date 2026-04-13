import React from 'react';
import { Box, Button, Typography, Tooltip } from '@mui/material';
import { useNavigate, useLocation } from 'react-router-dom';
import { 
  Dashboard as DashboardIcon, 
  Storage, 
  Assessment, 
  Settings,
  Shield,
  Terminal,
  Brain
} from '@mui/icons-material';

interface NavigationItemProps {
  href: string;
  icon: React.ReactNode;
  children: React.ReactNode;
  delay?: number;
}

const NavigationItem: React.FC<NavigationItemProps> = ({ href, icon, children, delay = 0 }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const isActive = location.pathname === href;

  return (
    <Tooltip title={children as string} placement="right" arrow>
      <Button
        onClick={() => navigate(href)}
        sx={{
          justifyContent: 'flex-start',
          position: 'relative',
          color: isActive ? '#00f5ff' : 'rgba(255,255,255,0.7)',
          backgroundColor: isActive ? 'rgba(0, 245, 255, 0.1)' : 'transparent',
          borderLeft: isActive ? '3px solid #00f5ff' : '3px solid transparent',
          pl: 2,
          pr: 3,
          py: 1.5,
          mb: 0.5,
          borderRadius: '0 8px 8px 0',
          overflow: 'hidden',
          transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
          animation: `slideInLeft 0.5s ease-out ${delay}s both`,
          '&::before': {
            content: '""',
            position: 'absolute',
            top: 0,
            left: 0,
            width: '100%',
            height: '100%',
            background: isActive 
              ? 'linear-gradient(90deg, rgba(0, 245, 255, 0.1) 0%, transparent 100%)'
              : 'linear-gradient(90deg, rgba(255, 255, 255, 0.05) 0%, transparent 100%)',
            transition: 'all 0.3s ease'
          },
          '&::after': {
            content: '""',
            position: 'absolute',
            top: '50%',
            right: 15,
            transform: 'translateY(-50%)',
            width: 6,
            height: 6,
            borderRadius: '50%',
            bgcolor: '#00f5ff',
            opacity: isActive ? 1 : 0,
            boxShadow: isActive ? '0 0 10px #00f5ff, 0 0 20px #00f5ff' : 'none',
            transition: 'all 0.3s ease'
          },
          '&:hover': {
            backgroundColor: 'rgba(0, 245, 255, 0.08)',
            color: '#00f5ff',
            borderLeft: '3px solid #00f5ff',
            transform: 'translateX(5px)',
            '&::before': {
              background: 'linear-gradient(90deg, rgba(0, 245, 255, 0.15) 0%, transparent 100%)'
            },
            '& .nav-icon': {
              transform: 'scale(1.1)',
              filter: 'drop-shadow(0 0 5px #00f5ff)'
            }
          }
        }}
      >
        <Box 
          className="nav-icon"
          sx={{ 
            mr: 2, 
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            transition: 'all 0.3s ease'
          }}
        >
          {icon}
        </Box>
        <Typography 
          sx={{ 
            fontFamily: 'Rajdhani',
            fontWeight: isActive ? 600 : 400,
            letterSpacing: 1,
            fontSize: '0.95rem'
          }}
        >
          {children}
        </Typography>
      </Button>
    </Tooltip>
  );
};

const Navigation: React.FC = () => {
  return (
    <Box sx={{ 
      width: 260, 
      height: '100vh',
      position: 'fixed',
      left: 0,
      top: 0,
      background: 'linear-gradient(180deg, #12121a 0%, #0a0a0f 100%)',
      borderRight: '1px solid rgba(0, 245, 255, 0.2)',
      display: 'flex',
      flexDirection: 'column',
      zIndex: 100,
      '&::before': {
        content: '""',
        position: 'absolute',
        top: 0,
        left: 0,
        right: 0,
        height: 3,
        background: 'linear-gradient(90deg, #00f5ff, #ff00ff, #00f5ff)',
        backgroundSize: '200% 100%',
        animation: 'gradient-shift 3s ease infinite'
      }
    }}>
      <Box sx={{ p: 3, position: 'relative' }}>
        <Box sx={{ 
          display: 'flex', 
          alignItems: 'center', 
          gap: 2,
          mb: 1
        }}>
          <Box sx={{
            width: 45,
            height: 45,
            borderRadius: 2,
            background: 'linear-gradient(135deg, rgba(0, 245, 255, 0.2) 0%, rgba(255, 0, 255, 0.2) 100%)',
            border: '1px solid rgba(0, 245, 255, 0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 0 20px rgba(0, 245, 255, 0.3)',
            animation: 'float 3s ease-in-out infinite'
          }}>
            <Shield sx={{ color: '#00f5ff', fontSize: 24 }} />
          </Box>
          <Box>
            <Typography 
              variant="h6" 
              sx={{ 
                fontFamily: 'Orbitron',
                fontWeight: 700,
                fontSize: '1rem',
                background: 'linear-gradient(90deg, #00f5ff, #ff00ff)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                letterSpacing: 2,
                lineHeight: 1.2
              }}
            >
              RAVER
            </Typography>
            <Typography 
              variant="caption" 
              sx={{ 
                fontFamily: 'Rajdhani',
                color: 'rgba(255,255,255,0.5)',
                letterSpacing: 1,
                fontSize: '0.65rem'
              }}
            >
              SENTINEL SYSTEM
            </Typography>
          </Box>
        </Box>
      </Box>

      <Box sx={{ px: 2, mb: 2 }}>
        <Box sx={{
          height: 1,
          background: 'linear-gradient(90deg, transparent, rgba(0, 245, 255, 0.3), transparent)'
        }} />
      </Box>

      <Box sx={{ px: 2, mb: 1 }}>
        <Typography sx={{
          fontFamily: 'Rajdhani',
          fontSize: '0.7rem',
          color: 'rgba(0, 245, 255, 0.5)',
          letterSpacing: 2,
          fontWeight: 600,
          px: 1,
          mb: 1
        }}>
          MAIN MENU
        </Typography>
      </Box>
      
      <Box sx={{ 
        display: 'flex', 
        flexDirection: 'column', 
        gap: 0.5,
        px: 2
      }}>
        <NavigationItem 
          href="/dashboard" 
          icon={<DashboardIcon sx={{ fontSize: 20 }} />}
          delay={0.1}
        >
          Dashboard
        </NavigationItem>
        
        <NavigationItem 
          href="/vault" 
          icon={<Storage sx={{ fontSize: 20 }} />}
          delay={0.2}
        >
          Vault
        </NavigationItem>
        
        <NavigationItem 
          href="/audit" 
          icon={<Assessment sx={{ fontSize: 20 }} />}
          delay={0.3}
        >
          Audit Logs
        </NavigationItem>
        
        <NavigationItem 
          href="/settings" 
          icon={<Settings sx={{ fontSize: 20 }} />}
          delay={0.4}
        >
          Settings
        </NavigationItem>
      </Box>

      <Box sx={{ px: 2, mt: 3, mb: 1 }}>
        <Typography sx={{
          fontFamily: 'Rajdhani',
          fontSize: '0.7rem',
          color: 'rgba(0, 245, 255, 0.5)',
          letterSpacing: 2,
          fontWeight: 600,
          px: 1,
          mb: 1
        }}>
          SYSTEM STATUS
        </Typography>
      </Box>

      <Box sx={{ 
        mx: 2,
        p: 2,
        borderRadius: 2,
        bgcolor: 'rgba(0, 0, 0, 0.3)',
        border: '1px solid rgba(0, 245, 255, 0.1)',
        animation: 'slideInLeft 0.5s ease-out 0.5s both'
      }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
          <Brain sx={{ fontSize: 14, color: '#00ff88' }} />
          <Typography sx={{ fontFamily: 'Rajdhani', fontSize: '0.75rem', color: 'rgba(255,255,255,0.7)' }}>
            AI Core
          </Typography>
          <Box sx={{
            ml: 'auto',
            width: 8,
            height: 8,
            borderRadius: '50%',
            bgcolor: '#00ff88',
            boxShadow: '0 0 10px #00ff88'
          }} />
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
          <Terminal sx={{ fontSize: 14, color: '#00ff88' }} />
          <Typography sx={{ fontFamily: 'Rajdhani', fontSize: '0.75rem', color: 'rgba(255,255,255,0.7)' }}>
            CLI Active
          </Typography>
          <Box sx={{
            ml: 'auto',
            width: 8,
            height: 8,
            borderRadius: '50%',
            bgcolor: '#00ff88',
            boxShadow: '0 0 10px #00ff88'
          }} />
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Shield sx={{ fontSize: 14, color: '#ff00ff' }} />
          <Typography sx={{ fontFamily: 'Rajdhani', fontSize: '0.75rem', color: 'rgba(255,255,255,0.7)' }}>
            Security
          </Typography>
          <Box sx={{
            ml: 'auto',
            width: 8,
            height: 8,
            borderRadius: '50%',
            bgcolor: '#ff00ff',
            boxShadow: '0 0 10px #ff00ff',
            animation: 'glow-pulse 2s ease-in-out infinite'
          }} />
        </Box>
      </Box>

      <Box sx={{ mt: 'auto', p: 3 }}>
        <Box sx={{
          p: 2,
          borderRadius: 2,
          background: 'linear-gradient(135deg, rgba(0, 245, 255, 0.1) 0%, rgba(255, 0, 255, 0.1) 100%)',
          border: '1px solid rgba(0, 245, 255, 0.2)',
          textAlign: 'center'
        }}>
          <Typography sx={{
            fontFamily: 'Orbitron',
            fontSize: '0.6rem',
            color: 'rgba(255,255,255,0.5)',
            letterSpacing: 1
          }}>
            VERSION 2.0.0
          </Typography>
        </Box>
      </Box>
    </Box>
  );
};

export default Navigation;
export { NavigationItem };
